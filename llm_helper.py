import json
import time
import metaphor_python as metaphor
import requests
from langchain import PromptTemplate
from langchain.llms import Clarifai

from global_config import GlobalConfig


prompt = None
llm_contents = None
llm_json = None
metaphor_client = None


def get_llm(use_gpt: bool) -> Clarifai:
    """
    Get a large language model.

    :param use_gpt: True if GPT-3.5 is required; False is Llama 2 is required
    """

    if use_gpt:
        llm = Clarifai(
            pat=GlobalConfig.CLARIFAI_PAT,
            user_id=GlobalConfig.CLARIFAI_USER_ID_GPT,
            app_id=GlobalConfig.CLARIFAI_APP_ID_GPT,
            model_id=GlobalConfig.CLARIFAI_MODEL_ID_GPT,
            verbose=True,
            # temperature=0.1,
        )
    else:
        llm = Clarifai(
            pat=GlobalConfig.CLARIFAI_PAT,
            user_id=GlobalConfig.CLARIFAI_USER_ID,
            app_id=GlobalConfig.CLARIFAI_APP_ID,
            model_id=GlobalConfig.CLARIFAI_MODEL_ID,
            verbose=True,
            # temperature=0.1,
        )
    print(llm)

    return llm


def generate_slides_content(topic: str) -> str:
    """
    Generate the outline/contents of slides for a presentation on a given topic.

    :param topic: Topic/subject matter/idea on which slides are to be generated
    :return: The content
    """

    global prompt
    global llm_contents

    if prompt is None:
        with open(GlobalConfig.SLIDES_TEMPLATE_FILE, 'r') as in_file:
            template_txt = in_file.read().strip()

        prompt = PromptTemplate.from_template(template_txt)

    formatted_prompt = prompt.format(topic=topic)
    print(f'formatted_prompt:\n{formatted_prompt}')

    if llm_contents is None:
        llm_contents = get_llm(use_gpt=False)

    slides_content = llm_contents(formatted_prompt, verbose=True)

    return slides_content


def text_to_json(content: str) -> str:
    """
    Convert input text into structured JSON representation.

    :param content: Input text
    :return: JSON string
    """

    global llm_json

    content = content.replace('```', '')

    # f-string is not used in order to prevent interpreting the brackets
    with open(GlobalConfig.JSON_TEMPLATE_FILE, 'r') as in_file:
        text = in_file.read()
        # Insert the actual text contents
        text = text.replace('<REPLACE_PLACEHOLDER>', content)

    text = text.strip()
    print(text)

    if llm_json is None:
        llm_json = get_llm(use_gpt=True)

    output = llm_json(text, verbose=True)
    output = output.strip()

    first_index = max(0, output.find('{'))
    last_index = min(output.rfind('}'), len(output))
    output = output[first_index: last_index + 1]

    return output


def text_to_yaml(content: str) -> str:
    """
    Convert input text into structured YAML representation.

    :param content: Input text
    :return: JSON string
    """

    global llm_json

    content = content.replace('```', '')

    # f-string is not used in order to prevent interpreting the brackets
    text = '''
You are a helpful AI assistant.
Convert the given slide deck text into structured YAML output.
Also, generate and add an engaging presentation title. 
The output should be only correct and valid YAML having the following structure:

title: "..."
slides:
  - heading: "..."
    bullet_points:
      - "..."
      - "..."
  - heading: "..."
    bullet_points:
      - "..."
      - "...":  # This line ends with a colon because it has a sub-block
        - "..."
      - "..."


Text:
'''
    text += content
    text += '''




Output:
```yaml
'''

    text = text.strip()
    print(text)

    if llm_json is None:
        llm_json = get_llm(use_gpt=True)

    output = llm_json(text, verbose=True)
    output = output.strip()

    # first_index = max(0, output.find('{'))
    # last_index = min(output.rfind('}'), len(output))
    # output = output[first_index: last_index + 1]

    return output


def get_related_websites(query: str) -> metaphor.api.SearchResponse:
    """
    Fetch Web search results for a given query.

    :param query: The query text
    :return: The search results object
    """

    global metaphor_client

    if not metaphor_client:
        metaphor_client = metaphor.Metaphor(api_key=GlobalConfig.METAPHOR_API_KEY)

    return metaphor_client.search(query, use_autoprompt=True, num_results=5)


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

    print('*** AI image generator...')
    print(url)

    start = time.time()
    response = requests.post(
        url=url,
        headers=headers,
        data=json.dumps(data)
    )
    stop = time.time()

    print('Response:', response, response.status_code)
    print('Image generation took', stop - start, 'seconds')
    img_data = ''

    if response.ok:
        print('*** Clarifai SDXL request: Response OK')
        json_data = json.loads(response.text)
        img_data = json_data['outputs'][0]['data']['image']['base64']
    else:
        print('Image generation failed:', response.text)

    return img_data


if __name__ == '__main__':
    # results = get_related_websites('5G AI WiFi 6')
    #
    # for a_result in results.results:
    #     print(a_result.title, a_result.url, a_result.extract)

    # get_ai_image('A talk on AI, covering pros and cons')
    pass
