"""
Utility functions to help with text processing.
"""
import json_repair as jr


def is_valid_prompt(prompt: str) -> bool:
    """
    Verify whether user input satisfies the concerned constraints.

    Args:
        prompt: The user input text.

    Returns:
        True if all criteria are satisfied; False otherwise.
    """
    if len(prompt) < 7 or ' ' not in prompt:
        return False

    return True


def get_clean_json(json_str: str) -> str:
    """
    Attempt to clean a JSON response string from the LLM by removing ```json at the beginning and
    trailing ``` and any text beyond that.
    CAUTION: May not be always accurate.

    Args:
        json_str: The input string in JSON format.

    Returns:
        The "cleaned" JSON string.
    """
    response_cleaned = json_str

    if json_str.startswith('```json'):
        json_str = json_str[7:]

    while True:
        idx = json_str.rfind('```')  # -1 on failure

        if idx <= 0:
            break

        # In the ideal scenario, the character before the last ``` should be
        # a new line or a closing bracket
        prev_char = json_str[idx - 1]

        if (prev_char == '}') or (prev_char == '\n' and json_str[idx - 2] == '}'):
            response_cleaned = json_str[:idx]

        json_str = json_str[:idx]

    return response_cleaned


def fix_malformed_json(json_str: str) -> str:
    """
    Try and fix the syntax error(s) in a JSON string.

    Args:
        json_str: The input JSON string.

    Returns:
        The fixed JSON string.
    """
    return jr.repair_json(json_str, skip_json_loads=True)


if __name__ == '__main__':
    JSON1 = '''{
    "key": "value"
    }
    '''
    JSON2 = '''["Reason": "Regular updates help protect against known vulnerabilities."]'''
    JSON3 = '''["Reason" Regular updates help protect against known vulnerabilities."]'''
    JSON4 = '''
    {"bullet_points": [
        ">> Write without stopping or editing",
        >> Set daily writing goals and stick to them,
        ">> Allow yourself to make mistakes"
    ],}
    '''

    print(fix_malformed_json(JSON1))
    print(fix_malformed_json(JSON2))
    print(fix_malformed_json(JSON3))
    print(fix_malformed_json(JSON4))
