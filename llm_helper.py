import metaphor_python as metaphor
from langchain import PromptTemplate
from langchain.llms import Clarifai

from global_config import GlobalConfig


prompt = None
llm_contents = None
llm_yaml = None
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

    global llm_yaml

    content = content.replace('```', '')

    # f-string is not used in order to prevent interpreting the brackets
    text = '''
Convert the given slide deck text into structured JSON output.
Also, generate and add an engaging presentation title. 
The output should be only correct and valid JSON having the following structure:

{
    "title": "...",
    "slides": [
        {
            "heading": "...",
            "bullet_points": [
                "...",
                [
                    "...",
                    "..."
                ]
            ]
        },
        {
            ...
        },
    ]
}


Text:
'''
    text += content
    text += '''


Output:
```json
'''

    text = text.strip()
    print(text)

    if llm_yaml is None:
        llm_yaml = get_llm(use_gpt=True)

    output = llm_yaml(text, verbose=True)
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

    global llm_yaml

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

    if llm_yaml is None:
        llm_yaml = get_llm(use_gpt=True)

    output = llm_yaml(text, verbose=True)
    output = output.strip()

    # first_index = max(0, output.find('{'))
    # last_index = min(output.rfind('}'), len(output))
    # output = output[first_index: last_index + 1]

    return output


def get_related_websites(query: str) -> metaphor.api.SearchResponse:
    global metaphor_client

    if not metaphor_client:
        metaphor_client = metaphor.Metaphor(api_key=GlobalConfig.METAPHOR_API_KEY)

    return metaphor_client.search(query, use_autoprompt=True, num_results=5)


if __name__ == '__main__':
    results = get_related_websites('5G AI WiFi 6')

    for a_result in results.results:
        print(a_result.title, a_result.url, a_result.extract)

