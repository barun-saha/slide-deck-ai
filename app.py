import datetime
import logging
import pathlib
import random
import tempfile
from typing import List

import json5
import streamlit as st
from langchain_community.chat_message_histories import (
    StreamlitChatMessageHistory
)
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from transformers import AutoTokenizer

from global_config import GlobalConfig
from helpers import llm_helper, pptx_helper


@st.cache_data
def _load_strings() -> dict:
    """
    Load various strings to be displayed in the app.
    :return: The dictionary of strings.
    """

    with open(GlobalConfig.APP_STRINGS_FILE, 'r', encoding='utf-8') as in_file:
        return json5.loads(in_file.read())


@st.cache_data
def _get_prompt_template(is_refinement: bool) -> str:
    """
    Return a prompt template.

    :param is_refinement: Whether this is the initial or refinement prompt.
    :return: The prompt template as f-string.
    """

    if is_refinement:
        with open(GlobalConfig.REFINEMENT_PROMPT_TEMPLATE, 'r', encoding='utf-8') as in_file:
            template = in_file.read()
    else:
        with open(GlobalConfig.INITIAL_PROMPT_TEMPLATE, 'r', encoding='utf-8') as in_file:
            template = in_file.read()

    return template


@st.cache_resource
def _get_tokenizer() -> AutoTokenizer:
    """
    Get Mistral tokenizer for counting tokens.

    :return: The tokenizer.
    """

    return AutoTokenizer.from_pretrained(
        pretrained_model_name_or_path=GlobalConfig.HF_LLM_MODEL_NAME
    )


APP_TEXT = _load_strings()

# Session variables
CHAT_MESSAGES = 'chat_messages'
DOWNLOAD_FILE_KEY = 'download_file_name'
IS_IT_REFINEMENT = 'is_it_refinement'

logger = logging.getLogger(__name__)
progress_bar = st.progress(0, text='Setting up SlideDeck AI...')

texts = list(GlobalConfig.PPTX_TEMPLATE_FILES.keys())
captions = [GlobalConfig.PPTX_TEMPLATE_FILES[x]['caption'] for x in texts]
pptx_template = st.sidebar.radio(
    'Select a presentation template:',
    texts,
    captions=captions,
    horizontal=True
)


def display_page_header_content():
    """
    Display content in the page header.
    """

    st.title(APP_TEXT['app_name'])
    st.subheader(APP_TEXT['caption'])
    # st.markdown(
    #     '![Visitors](https://api.visitorbadge.io/api/visitors?path=https%3A%2F%2Fhuggingface.co%2Fspaces%2Fbarunsaha%2Fslide-deck-ai&countColor=%23263759)'  # noqa: E501
    # )


def display_page_footer_content():
    """
    Display content in the page footer.
    """

    st.text(APP_TEXT['tos'] + '\n\n' + APP_TEXT['tos2'])


def build_ui():
    """
    Display the input elements for content generation.
    """

    display_page_header_content()

    with st.expander('Usage Policies and Limitations'):
        display_page_footer_content()

    progress_bar.progress(50, text='Setting up chat interface...')
    set_up_chat_ui()


def set_up_chat_ui():
    """
    Prepare the chat interface and related functionality.
    """

    with st.expander('Usage Instructions'):
        st.write(GlobalConfig.CHAT_USAGE_INSTRUCTIONS)
        st.markdown(
            'SlideDeck AI is powered by'
            ' [Mistral-7B-Instruct-v0.2](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2)'
        )

    # view_messages = st.expander('View the messages in the session state')

    st.chat_message('ai').write(
        random.choice(APP_TEXT['ai_greetings'])
    )
    progress_bar.progress(100, text='Done!')
    progress_bar.empty()

    history = StreamlitChatMessageHistory(key=CHAT_MESSAGES)

    if _is_it_refinement():
        template = _get_prompt_template(is_refinement=True)
        logger.debug('Getting refinement template')
    else:
        template = _get_prompt_template(is_refinement=False)
        logger.debug('Getting initial template')

    prompt_template = ChatPromptTemplate.from_template(template)

    # Since Streamlit app reloads at every interaction, display the chat history
    # from the save session state
    for msg in history.messages:
        msg_type = msg.type
        if msg_type == 'user':
            st.chat_message(msg_type).write(msg.content)
        else:
            st.chat_message(msg_type).code(msg.content, language='json')

    if prompt := st.chat_input(
        placeholder=APP_TEXT['chat_placeholder'],
        max_chars=GlobalConfig.LLM_MODEL_MAX_INPUT_LENGTH
    ):

        progress_bar_pptx = st.progress(0, 'Preparing to run...')
        if not _is_valid_prompt(prompt):
            return

        logger.info('User input: %s | #characters: %d', prompt, len(prompt))
        st.chat_message('user').write(prompt)

        user_messages = _get_user_messages()
        user_messages.append(prompt)
        list_of_msgs = [
            f'{idx + 1}. {msg}' for idx, msg in enumerate(user_messages)
        ]
        list_of_msgs = '\n'.join(list_of_msgs)

        if _is_it_refinement():
            formatted_template = prompt_template.format(
                **{
                    'instructions': list_of_msgs,
                    'previous_content': _get_last_response()
                }
            )
        else:
            formatted_template = prompt_template.format(
                **{
                    'question': prompt,
                }
            )

        progress_bar_pptx.progress(5, 'Calling LLM...will retry if connection times out...')
        response: dict = llm_helper.hf_api_query({
            'inputs': formatted_template,
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

        if len(response) > 0 and 'generated_text' in response[0]:
            response: str = response[0]['generated_text'].strip()

        st.chat_message('ai').code(response, language='json')

        history.add_user_message(prompt)
        history.add_ai_message(response)

        if GlobalConfig.COUNT_TOKENS:
            tokenizer = _get_tokenizer()
            tokens_count_in = len(tokenizer.tokenize(formatted_template))
            tokens_count_out = len(tokenizer.tokenize(response))
            logger.debug(
                'Tokens count:: input: %d, output: %d',
                tokens_count_in, tokens_count_out
            )

        # _display_messages_history(view_messages)

        # The content has been generated as JSON
        # There maybe trailing ``` at the end of the response -- remove them
        # To be careful: ``` may be part of the content as well when code is generated
        progress_bar_pptx.progress(50, 'Analyzing response...')
        response_cleaned = _clean_json(response)

        # Now create the PPT file
        progress_bar_pptx.progress(75, 'Creating the slide deck...give it a moment...')
        generate_slide_deck(response_cleaned)
        progress_bar_pptx.progress(100, text='Done!')


def generate_slide_deck(json_str: str):
    """
    Create a slide deck.

    :param json_str: The content in *valid* JSON format.
    """

    if DOWNLOAD_FILE_KEY in st.session_state:
        path = pathlib.Path(st.session_state[DOWNLOAD_FILE_KEY])
        logger.debug('DOWNLOAD_FILE_KEY found in session')
    else:
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.pptx')
        path = pathlib.Path(temp.name)
        st.session_state[DOWNLOAD_FILE_KEY] = str(path)
        logger.debug('DOWNLOAD_FILE_KEY not found in session')

        if temp:
            temp.close()

    logger.debug('Creating PPTX file: %s...', st.session_state[DOWNLOAD_FILE_KEY])

    try:
        pptx_helper.generate_powerpoint_presentation(
            json_str,
            slides_template=pptx_template,
            output_file_path=path
        )

        _display_download_button(path)
    except ValueError as ve:
        st.error(APP_TEXT['json_parsing_error'])
        logger.error('%s', APP_TEXT['json_parsing_error'])
        logger.error('Additional error info: %s', str(ve))
    except Exception as ex:
        st.error(APP_TEXT['content_generation_error'])
        logger.error('Caught a generic exception: %s', str(ex))


def _is_valid_prompt(prompt: str) -> bool:
    """
    Verify whether user input satisfies the concerned constraints.

    :param prompt: The user input text.
    :return: True if all criteria are satisfied; False otherwise.
    """

    if len(prompt) < 5 or ' ' not in prompt:
        st.error(
            'Not enough information provided!'
            ' Please be a little more descriptive and type a few words with a few characters :)'
        )
        return False

    return True


def _is_it_refinement() -> bool:
    """
    Whether it is the initial prompt or a refinement.

    :return: True if it is the initial prompt; False otherwise.
    """

    if IS_IT_REFINEMENT in st.session_state:
        return True

    if len(st.session_state[CHAT_MESSAGES]) >= 2:
        # Prepare for the next call
        st.session_state[IS_IT_REFINEMENT] = True
        return True

    return False


def _get_user_messages() -> List[str]:
    """
    Get a list of user messages submitted until now from the session state.

    :return: The list of user messages.
    """

    return [
        msg.content for msg in st.session_state[CHAT_MESSAGES] if isinstance(msg, HumanMessage)
    ]


def _get_last_response() -> str:
    """
    Get the last response generated by AI.

    :return: The response text.
    """

    return st.session_state[CHAT_MESSAGES][-1].content


def _display_messages_history(view_messages: st.expander):
    """
    Display the history of messages.

    :param view_messages: The list of AI and Human messages.
    """

    with view_messages:
        view_messages.json(st.session_state[CHAT_MESSAGES])

def _clean_json(json_str: str) -> str:
    """
    Attempt to clean a JSON response string from the LLM by removing the trailing ```
    and any text beyond that. May not be always accurate.

    :param json_str: The input string in JSON format.
    :return: The "cleaned" JSON string.
    """

    str_len = len(json_str)
    response_cleaned = json_str

    try:
        idx = json_str.rindex('```')
        logger.debug(
            'Fixing JSON response: str_len: %d, idx of ```: %d',
            str_len, idx
        )

        if idx + 3 == str_len:
            # The response ends with ``` -- most likely the end of JSON response string
            response_cleaned = json_str[:idx]
        elif idx + 3 < str_len:
            # Looks like there are some more content beyond the last ```
            # In the best case, it would be some additional plain-text response from the LLM
            # and is unlikely to contain } or ] that are present in JSON
            if '}' not in json_str[idx + 3:]:  # the remainder of the text
                response_cleaned = json_str[:idx]
    except ValueError:
        # No ``` found
        pass

    return response_cleaned


def _display_download_button(file_path: pathlib.Path):
    """
    Display a download button to download a slide deck.

    :param file_path: The path of the .pptx file.
    """

    with open(file_path, 'rb') as download_file:
        st.download_button(
            'Download PPTX file ⬇️',
            data=download_file,
            file_name='Presentation.pptx',
            key=datetime.datetime.now()
        )


def main():
    """
    Trigger application run.
    """

    build_ui()


if __name__ == '__main__':
    main()
