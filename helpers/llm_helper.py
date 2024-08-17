import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from langchain_community.llms.huggingface_endpoint import HuggingFaceEndpoint
from langchain_core.language_models import LLM

from global_config import GlobalConfig


HF_API_URL = f"https://api-inference.huggingface.co/models/{GlobalConfig.HF_LLM_MODEL_NAME}"
HF_API_HEADERS = {"Authorization": f"Bearer {GlobalConfig.HUGGINGFACEHUB_API_TOKEN}"}
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


def get_hf_endpoint() -> LLM:
    """
    Get an LLM via the HuggingFaceEndpoint of LangChain.

    :return: The LLM.
    """

    logger.debug('Getting LLM via HF endpoint')

    return HuggingFaceEndpoint(
        repo_id=GlobalConfig.HF_LLM_MODEL_NAME,
        max_new_tokens=GlobalConfig.LLM_MODEL_MAX_OUTPUT_LENGTH,
        top_k=40,
        top_p=0.95,
        temperature=GlobalConfig.LLM_MODEL_TEMPERATURE,
        repetition_penalty=1.03,
        streaming=True,
        huggingfacehub_api_token=GlobalConfig.HUGGINGFACEHUB_API_TOKEN,
        return_full_text=False,
        stop_sequences=['</s>'],
    )


def hf_api_query(payload: dict) -> dict:
    """
    Invoke HF inference end-point API.

    :param payload: The prompt for the LLM and related parameters.
    :return: The output from the LLM.
    """

    try:
        response = http_session.post(
            HF_API_URL,
            headers=HF_API_HEADERS,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        result = response.json()
    except requests.exceptions.Timeout as te:
        logger.error('*** Error: hf_api_query timeout! %s', str(te))
        result = []

    return result


def generate_slides_content(topic: str) -> str:
    """
    Generate the outline/contents of slides for a presentation on a given topic.

    :param topic: Topic on which slides are to be generated.
    :return: The content in JSON format.
    """

    with open(GlobalConfig.SLIDES_TEMPLATE_FILE, 'r', encoding='utf-8') as in_file:
        template_txt = in_file.read().strip()
        template_txt = template_txt.replace('<REPLACE_PLACEHOLDER>', topic)

    output = hf_api_query({
        'inputs': template_txt,
        'parameters': {
            'temperature': GlobalConfig.LLM_MODEL_TEMPERATURE,
            'min_length': GlobalConfig.LLM_MODEL_MIN_OUTPUT_LENGTH,
            'max_length': GlobalConfig.LLM_MODEL_MAX_OUTPUT_LENGTH,
            'max_new_tokens': GlobalConfig.LLM_MODEL_MAX_OUTPUT_LENGTH,
            'num_return_sequences': 1,
            'return_full_text': False,
            # "repetition_penalty": 0.0001
        },
        'options': {
            'wait_for_model': True,
            'use_cache': True
        }
    })

    output = output[0]['generated_text'].strip()
    # output = output[len(template_txt):]

    json_end_idx = output.rfind('```')
    if json_end_idx != -1:
        # logging.debug(f'{json_end_idx=}')
        output = output[:json_end_idx]

    logger.debug('generate_slides_content: output: %s', output)

    return output


if __name__ == '__main__':
    # results = get_related_websites('5G AI WiFi 6')
    #
    # for a_result in results.results:
    #     print(a_result.title, a_result.url, a_result.extract)

    # get_ai_image('A talk on AI, covering pros and cons')
    pass
