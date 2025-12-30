"""
Helper functions to access LLMs using LiteLLM.
"""
import logging
import re
import urllib3
from typing import Tuple, Union, Iterator, Optional


from ..global_config import GlobalConfig

try:
    import litellm
    from litellm import completion

    litellm.drop_params = True

    # Ask LiteLLM to suppress debug information if possible
    try:
        litellm.suppress_debug_info = True
    except AttributeError:
        # Attribute not available in this version of LiteLLM
        pass

except ImportError:
    litellm = None
    completion = None


LLM_PROVIDER_MODEL_REGEX = re.compile(r'\[(.*?)\](.*)')
OLLAMA_MODEL_REGEX = re.compile(r'[a-zA-Z0-9._:-]+$')
# 200 characters long, only containing alphanumeric characters, hyphens, and underscores
API_KEY_REGEX = re.compile(r'^[a-zA-Z0-9_-]{6,200}$')


logger = logging.getLogger(__name__)


def get_provider_model(provider_model: str, use_ollama: bool) -> Tuple[str, str]:
    """
    Parse and get LLM provider and model name from strings like `[provider]model/name-version`.

    :param provider_model: The provider, model name string from `GlobalConfig`.
    :param use_ollama: Whether Ollama is used (i.e., running in offline mode).
    :return: The provider and the model name; empty strings in case no matching pattern found.
    """
    provider_model = provider_model.strip()

    if use_ollama:
        match = OLLAMA_MODEL_REGEX.match(provider_model)
        if match:
            return GlobalConfig.PROVIDER_OLLAMA, match.group(0)
    else:
        match = LLM_PROVIDER_MODEL_REGEX.match(provider_model)

        if match:
            inside_brackets = match.group(1)
            outside_brackets = match.group(2)
            
            # Validate that the provider is in the valid providers list
            if inside_brackets not in GlobalConfig.VALID_PROVIDERS:
                logger.warning(
                    "Provider '%s' not in VALID_PROVIDERS: %s",
                    inside_brackets, GlobalConfig.VALID_PROVIDERS
                )
                return '', ''
            
            # Validate that the model name is not empty
            if not outside_brackets.strip():
                logger.warning("Empty model name for provider '%s'", inside_brackets)
                return '', ''
            
            return inside_brackets, outside_brackets

    logger.warning(
        "Could not parse provider_model: '%s' (use_ollama=%s)",
        provider_model, use_ollama
    )
    return '', ''


def is_valid_llm_provider_model(
        provider: str,
        model: str,
        api_key: str,
        azure_endpoint_url: str = '',
        azure_deployment_name: str = '',
        azure_api_version: str = '',
) -> bool:
    """
    Verify whether LLM settings are proper.
    This function does not verify whether `api_key` is correct. It only confirms that the key has
    at least five characters. Key verification is done when the LLM is created.

    :param provider: Name of the LLM provider.
    :param model: Name of the model.
    :param api_key: The API key or access token.
    :param azure_endpoint_url: Azure OpenAI endpoint URL.
    :param azure_deployment_name: Azure OpenAI deployment name.
    :param azure_api_version: Azure OpenAI API version.
    :return: `True` if the settings "look" OK; `False` otherwise.
    """
    if not provider or not model or provider not in GlobalConfig.VALID_PROVIDERS:
        return False

    if provider != GlobalConfig.PROVIDER_OLLAMA:
        # No API key is required for offline Ollama models
        if not api_key:
            return False

        if api_key and API_KEY_REGEX.match(api_key) is None:
            return False

    if provider == GlobalConfig.PROVIDER_AZURE_OPENAI:
        valid_url = urllib3.util.parse_url(azure_endpoint_url)
        all_status = all(
            [azure_api_version, azure_deployment_name, str(valid_url)]
        )
        return all_status

    return True


def get_litellm_model_name(provider: str, model: str) -> Optional[str]:
    """
    Convert provider and model to LiteLLM model name format.
    
    Note: Azure OpenAI models are handled separately in stream_litellm_completion()
    and should not be passed to this function.
    
    :param provider: The LLM provider.
    :param model: The model name.
    :return: LiteLLM-compatible model name, or None if provider is not supported.
    """
    prefix = GlobalConfig.LITELLM_PROVIDER_MAPPING.get(provider)
    if prefix:
        return f'{prefix}/{model}'
    # LiteLLM always expects a prefix for model names; if not found, return None
    return None


def stream_litellm_completion(
        provider: str,
        model: str,
        messages: list,
        max_tokens: int,
        api_key: str = '',
        azure_endpoint_url: str = '',
        azure_deployment_name: str = '',
        azure_api_version: str = '',
) -> Iterator[str]:
    """
    Stream completion from LiteLLM.

    :param provider: The LLM provider.
    :param model: The name of the LLM.
    :param messages: List of messages for the chat completion.
    :param max_tokens: The maximum number of tokens to generate.
    :param api_key: API key or access token to use.
    :param azure_endpoint_url: Azure OpenAI endpoint URL.
    :param azure_deployment_name: Azure OpenAI deployment name.
    :param azure_api_version: Azure OpenAI API version.
    :return: Iterator of response chunks.
    """
    if litellm is None:
        raise ImportError("LiteLLM is not installed. Please install it with: pip install litellm")
    
    # Convert to LiteLLM model name
    if provider == GlobalConfig.PROVIDER_AZURE_OPENAI:
        # For Azure OpenAI, use the deployment name as the model
        # This is consistent with Azure OpenAI's requirement to use deployment names
        if not azure_deployment_name:
            raise ValueError("Azure deployment name is required for Azure OpenAI provider")
        litellm_model = f'azure/{azure_deployment_name}'
    else:
        litellm_model = get_litellm_model_name(provider, model)
        if not litellm_model:
            raise ValueError(f"Invalid model name: {model} for provider: {provider}")
    
    # Prepare the request parameters
    request_params = {
        'model': litellm_model,
        'messages': messages,
        'max_tokens': max_tokens,
        'temperature': GlobalConfig.LLM_MODEL_TEMPERATURE,
        'stream': True,
    }
    
    # Set API key and any provider-specific params
    if provider != GlobalConfig.PROVIDER_OLLAMA:
        # For OpenRouter, pass API key as parameter
        if provider == GlobalConfig.PROVIDER_OPENROUTER:
            request_params['api_key'] = api_key
        elif provider == GlobalConfig.PROVIDER_AZURE_OPENAI:
            # For Azure OpenAI, pass credentials as parameters
            request_params['api_key'] = api_key
            request_params['api_base'] = azure_endpoint_url
            request_params['api_version'] = azure_api_version
        else:
            # For other providers, pass API key as parameter
            request_params['api_key'] = api_key
    
    logger.debug('Streaming completion via LiteLLM: %s', litellm_model)
    
    try:
        response = litellm.completion(**request_params)
        
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices:
                choice = chunk.choices[0]
                if hasattr(choice, 'delta') and hasattr(choice.delta, 'content'):
                    if choice.delta.content:
                        yield choice.delta.content
                elif hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    if choice.message.content:
                        yield choice.message.content
                        
    except Exception as e:
        raise


def get_litellm_llm(
        provider: str,
        model: str,
        max_new_tokens: int,
        api_key: str = '',
        azure_endpoint_url: str = '',
        azure_deployment_name: str = '',
        azure_api_version: str = '',
) -> Union[object, None]:
    """
    Get a LiteLLM-compatible object for streaming.

    :param provider: The LLM provider.
    :param model: The name of the LLM.
    :param max_new_tokens: The maximum number of tokens to generate.
    :param api_key: API key or access token to use.
    :param azure_endpoint_url: Azure OpenAI endpoint URL.
    :param azure_deployment_name: Azure OpenAI deployment name.
    :param azure_api_version: Azure OpenAI API version.
    :return: A LiteLLM-compatible object for streaming; `None` in case of any error.
    """
    if litellm is None:
        raise ImportError("LiteLLM is not installed. Please install it with: pip install litellm")
    
    # Create a simple wrapper object that mimics the LangChain streaming interface
    class LiteLLMWrapper:
        def __init__(
                self, provider, model, max_tokens, api_key, azure_endpoint_url,
                azure_deployment_name, azure_api_version
        ):
            self.provider = provider
            self.model = model
            self.max_tokens = max_tokens
            self.api_key = api_key
            self.azure_endpoint_url = azure_endpoint_url
            self.azure_deployment_name = azure_deployment_name
            self.azure_api_version = azure_api_version
        
        def stream(self, prompt: str):
            messages = [{'role': 'user', 'content': prompt}]
            return stream_litellm_completion(
                provider=self.provider,
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                api_key=self.api_key,
                azure_endpoint_url=self.azure_endpoint_url,
                azure_deployment_name=self.azure_deployment_name,
                azure_api_version=self.azure_api_version,
            )
    
    logger.debug('Creating LiteLLM wrapper for: %s', model)
    return LiteLLMWrapper(
        provider=provider,
        model=model,
        max_tokens=max_new_tokens,
        api_key=api_key,
        azure_endpoint_url=azure_endpoint_url,
        azure_deployment_name=azure_deployment_name,
        azure_api_version=azure_api_version,
    )


# Keep the old function name for backward compatibility
get_langchain_llm = get_litellm_llm


if __name__ == '__main__':
    inputs = [
        '[co]Cohere',
        '[hf]mistralai/Mistral-7B-Instruct-v0.2',
        '[gg]gemini-1.5-flash-002'
    ]

    for text in inputs:
        print(get_provider_model(text, use_ollama=False))
