import json_repair as jr


def is_valid_prompt(prompt: str) -> bool:
    """
    Verify whether user input satisfies the concerned constraints.

    :param prompt: The user input text.
    :return: True if all criteria are satisfied; False otherwise.
    """

    if len(prompt) < 7 or ' ' not in prompt:
        return False

    return True


def get_clean_json(json_str: str) -> str:
    """
    Attempt to clean a JSON response string from the LLM by removing the trailing ```
    and any text beyond that.
    CAUTION: May not be always accurate.

    :param json_str: The input string in JSON format.
    :return: The "cleaned" JSON string.
    """

    # An example of response containing JSON and other text:
    # {
    #     "title": "AI and the Future: A Transformative Journey",
    #     "slides": [
    #       ...
    #     ]
    # }    <<---- This is end of valid JSON content
    # ```
    #
    # ```vbnet
    # Please note that the JSON output is in valid format but the content of the "Role of GPUs in AI" slide is just an example and may not be factually accurate. For accurate information, you should consult relevant resources and update the content accordingly.
    # ```
    response_cleaned = json_str

    while True:
        idx = json_str.rfind('```')  # -1 on failure

        if idx <= 0:
            break

        # In the ideal scenario, the character before the last ``` should be
        # a new line or a closing bracket }
        prev_char = json_str[idx - 1]

        if (prev_char == '}') or (prev_char == '\n' and json_str[idx - 2] == '}'):
            response_cleaned = json_str[:idx]

        json_str = json_str[:idx]

    return response_cleaned


def fix_malformed_json(json_str: str) -> str:
    """
    Try and fix the syntax error(s) in a JSON string.

    :param json_str: The input JSON string.
    :return: The fixed JSOn string.
    """

    return jr.repair_json(json_str, skip_json_loads=True)


if __name__ == '__main__':
    json1 = '''{
    "key": "value"
    }
    '''
    json2 = '''["Reason": "Regular updates help protect against known vulnerabilities."]'''
    json3 = '''["Reason" Regular updates help protect against known vulnerabilities."]'''
    json4 = '''
    {"bullet_points": [
        ">> Write without stopping or editing",
        >> Set daily writing goals and stick to them,
        ">> Allow yourself to make mistakes"
    ],}
    '''

    print(fix_malformed_json(json1))
    print(fix_malformed_json(json2))
    print(fix_malformed_json(json3))
    print(fix_malformed_json(json4))
