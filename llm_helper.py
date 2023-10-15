import json
import logging
import time
import requests
from langchain.llms import Clarifai

from global_config import GlobalConfig


logging.basicConfig(
    level=GlobalConfig.LOG_LEVEL,
    format='%(asctime)s - %(message)s',
)

llm = None


def get_llm(use_gpt: bool) -> Clarifai:
    """
    Get a large language model.

    :param use_gpt: True if GPT-3.5 is required; False is Llama 2 is required
    """

    if use_gpt:
        _ = Clarifai(
            pat=GlobalConfig.CLARIFAI_PAT,
            user_id=GlobalConfig.CLARIFAI_USER_ID_GPT,
            app_id=GlobalConfig.CLARIFAI_APP_ID_GPT,
            model_id=GlobalConfig.CLARIFAI_MODEL_ID_GPT,
            verbose=True,
            # temperature=0.1,
        )
    else:
        _ = Clarifai(
            pat=GlobalConfig.CLARIFAI_PAT,
            user_id=GlobalConfig.CLARIFAI_USER_ID,
            app_id=GlobalConfig.CLARIFAI_APP_ID,
            model_id=GlobalConfig.CLARIFAI_MODEL_ID,
            verbose=True,
            # temperature=0.1,
        )
    # print(llm)

    return _


def generate_slides_content(topic: str) -> str:
    """
    Generate the outline/contents of slides for a presentation on a given topic.

    :param topic: Topic/subject matter/idea on which slides are to be generated
    :return: The content in JSON format
    """

    # global prompt
    global llm

    with open(GlobalConfig.SLIDES_TEMPLATE_FILE, 'r') as in_file:
        template_txt = in_file.read().strip()
        template_txt = template_txt.replace('<REPLACE_PLACEHOLDER>', topic)

    if llm is None:
        llm = get_llm(use_gpt=True)
        print(llm)

    slides_content = llm(template_txt, verbose=True)

    return slides_content


def get_ai_image(text: str) -> str:
    """
    Get a Stable Diffusion-generated image based on a given text.

    :param text: The input text
    :return: The Base 64-encoded image
    """

    url = f'''https://api.clarifai.com/v2/users/{GlobalConfig.CLARIFAI_USER_ID_SD}/apps/{GlobalConfig.CLARIFAI_APP_ID_SD}/models/{GlobalConfig.CLARIFAI_MODEL_ID_SD}/versions/{GlobalConfig.CLARIFAI_MODEL_VERSION_ID_SD}/outputs'''
    headers = {
        "Content-Type": "application/json",
        "Authorization": f'Key {GlobalConfig.CLARIFAI_PAT}'
    }
    data = {
        "inputs": [
            {
                "data": {
                    "text": {
                        "raw": text
                    }
                }
            }
        ]
    }

    # print('*** AI image generator...')
    # print(url)

    start = time.time()
    response = requests.post(
        url=url,
        headers=headers,
        data=json.dumps(data)
    )
    stop = time.time()

    # print('Response:', response, response.status_code)
    logging.debug('Image generation took', stop - start, 'seconds')
    img_data = ''

    if response.ok:
        # print('*** Clarifai SDXL request: Response OK')
        json_data = json.loads(response.text)
        img_data = json_data['outputs'][0]['data']['image']['base64']
    else:
        logging.error('*** Image generation failed:', response.text)

    return img_data


if __name__ == '__main__':
    # results = get_related_websites('5G AI WiFi 6')
    #
    # for a_result in results.results:
    #     print(a_result.title, a_result.url, a_result.extract)

    # get_ai_image('A talk on AI, covering pros and cons')
    pass
