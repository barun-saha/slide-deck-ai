import logging
import re
from typing import Tuple, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from langchain_community.llms.huggingface_endpoint import HuggingFaceEndpoint
from langchain_core.language_models import LLM

from global_config import GlobalConfig


LLM_PROVIDER_MODEL_REGEX = re.compile(r'\[(.*?)\](.*)')
HF_API_HEADERS = {'Authorization': f'Bearer {GlobalConfig.HUGGINGFACEHUB_API_TOKEN}'}
REQUEST_TIMEOUT = 35

logger = logging.getLogger(__name__)

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


def get_provider_model(provider_model: str) -> Tuple[str, str]:
    """
    Parse and get LLM provider and model name from strings like `[provider]model/name-version`.

    :param provider_model: The provider, model name string from `GlobalConfig`.
    :return: The provider and the model name.
    """

    match = LLM_PROVIDER_MODEL_REGEX.match(provider_model)

    if match:
        inside_brackets = match.group(1)
        outside_brackets = match.group(2)
        return inside_brackets, outside_brackets

    return '', ''


def get_hf_endpoint(repo_id: str, max_new_tokens: int, api_key: str = '') -> LLM:
    """
    Get an LLM via the HuggingFaceEndpoint of LangChain.

    :param repo_id: The model name.
    :param max_new_tokens: The max new tokens to generate.
    :param api_key: [Optional] Hugging Face access token.
    :return: The HF LLM inference endpoint.
    """

    logger.debug('Getting LLM via HF endpoint: %s', repo_id)

    return HuggingFaceEndpoint(
        repo_id=repo_id,
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


def get_langchain_llm(
        provider: str,
        model: str,
        max_new_tokens: int,
        api_key: str = ''
) -> Union[LLM, None]:
    """
    Get an LLM based on the provider and model specified.

    :param provider: The LLM provider. Valid values are `hf` for Hugging Face.
    :param model:
    :param max_new_tokens:
    :param api_key:
    :return:
    """
    if not provider or not model or provider not in GlobalConfig.VALID_PROVIDERS:
        return None

    if provider == 'hf':
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

    return None


if __name__ == '__main__':
    inputs = [
        '[hf]mistralai/Mistral-7B-Instruct-v0.2',
        '[gg]gemini-1.5-flash-002'
    ]

    for text in inputs:
        print(get_provider_model(text))
