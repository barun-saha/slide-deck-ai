"""
Helper functions to access LLMs.
"""
import logging
import re
import sys
from typing import Tuple, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from langchain_core.language_models import BaseLLM

sys.path.append('..')

from global_config import GlobalConfig


LLM_PROVIDER_MODEL_REGEX = re.compile(r'\[(.*?)\](.*)')
OLLAMA_MODEL_REGEX = re.compile(r'[a-zA-Z0-9._:-]+$')
# 6-64 characters long, only containing alphanumeric characters, hyphens, and underscores
API_KEY_REGEX = re.compile(r'^[a-zA-Z0-9_-]{6,64}$')
HF_API_HEADERS = {'Authorization': f'Bearer {GlobalConfig.HUGGINGFACEHUB_API_TOKEN}'}
REQUEST_TIMEOUT = 35

logger = logging.getLogger(__name__)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

retries = Retry(
    total=5,
    backoff_factor=0.25,
    backoff_jitter=0.3,
    status_forcelist=[502, 503, 504],
    allowed_methods={'POST'},
)
adapter = HTTPAdapter(max_retries=retries)
http_session = requests.Session()
http_session.mount('https://', adapter)
http_session.mount('http://', adapter)


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
            return inside_brackets, outside_brackets

    return '', ''


def is_valid_llm_provider_model(provider: str, model: str, api_key: str) -> bool:
    """
    Verify whether LLM settings are proper.
    This function does not verify whether `api_key` is correct. It only confirms that the key has
    at least five characters. Key verification is done when the LLM is created.

    :param provider: Name of the LLM provider.
    :param model: Name of the model.
    :param api_key: The API key or access token.
    :return: `True` if the settings "look" OK; `False` otherwise.
    """

    if not provider or not model or provider not in GlobalConfig.VALID_PROVIDERS:
        return False

    if provider in [
        GlobalConfig.PROVIDER_GOOGLE_GEMINI,
        GlobalConfig.PROVIDER_COHERE,
        GlobalConfig.PROVIDER_TOGETHER_AI,
    ] and not api_key:
        return False

    if api_key:
        return API_KEY_REGEX.match(api_key) is not None

    return True


def get_langchain_llm(
        provider: str,
        model: str,
        max_new_tokens: int,
        api_key: str = ''
) -> Union[BaseLLM, None]:
    """
    Get an LLM based on the provider and model specified.

    :param provider: The LLM provider. Valid values are `hf` for Hugging Face.
    :param model: The name of the LLM.
    :param max_new_tokens: The maximum number of tokens to generate.
    :param api_key: API key or access token to use.
    :return: An instance of the LLM or `None` in case of any error.
    """

    if provider == GlobalConfig.PROVIDER_HUGGING_FACE:
        from langchain_community.llms.huggingface_endpoint import HuggingFaceEndpoint

        logger.debug('Getting LLM via HF endpoint: %s', model)
        return HuggingFaceEndpoint(
            repo_id=model,
            max_new_tokens=max_new_tokens,
            top_k=40,
            top_p=0.95,
            temperature=GlobalConfig.LLM_MODEL_TEMPERATURE,
            repetition_penalty=1.03,
            streaming=True,
            huggingfacehub_api_token=api_key or GlobalConfig.HUGGINGFACEHUB_API_TOKEN,
            return_full_text=False,
            stop_sequences=['</s>'],
        )

    if provider == GlobalConfig.PROVIDER_GOOGLE_GEMINI:
        from google.generativeai.types.safety_types import HarmBlockThreshold, HarmCategory
        from langchain_google_genai import GoogleGenerativeAI

        logger.debug('Getting LLM via Google Gemini: %s', model)
        return GoogleGenerativeAI(
            model=model,
            temperature=GlobalConfig.LLM_MODEL_TEMPERATURE,
            max_tokens=max_new_tokens,
            timeout=None,
            max_retries=2,
            google_api_key=api_key,
            safety_settings={
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT:
                    HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT:
                    HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
            }
        )

    if provider == GlobalConfig.PROVIDER_COHERE:
        from langchain_cohere.llms import Cohere

        logger.debug('Getting LLM via Cohere: %s', model)
        return Cohere(
            temperature=GlobalConfig.LLM_MODEL_TEMPERATURE,
            max_tokens=max_new_tokens,
            timeout_seconds=None,
            max_retries=2,
            cohere_api_key=api_key,
            streaming=True,
        )

    if provider == GlobalConfig.PROVIDER_TOGETHER_AI:
        from langchain_together import Together

        logger.debug('Getting LLM via Together AI: %s', model)
        return Together(
            model=model,
            temperature=GlobalConfig.LLM_MODEL_TEMPERATURE,
            together_api_key=api_key,
            max_tokens=max_new_tokens,
            top_k=40,
            top_p=0.90,
        )

    if provider == GlobalConfig.PROVIDER_OLLAMA:
        from langchain_ollama.llms import OllamaLLM

        logger.debug('Getting LLM via Ollama: %s', model)
        return OllamaLLM(
            model=model,
            temperature=GlobalConfig.LLM_MODEL_TEMPERATURE,
            num_predict=max_new_tokens,
            format='json',
            streaming=True,
        )

    return None


if __name__ == '__main__':
    inputs = [
        '[co]Cohere',
        '[hf]mistralai/Mistral-7B-Instruct-v0.2',
        '[gg]gemini-1.5-flash-002'
    ]

    for text in inputs:
        print(get_provider_model(text, use_ollama=False))
