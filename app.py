"""
Streamlit app containing the UI and the application logic.
"""
import datetime
import logging
import pathlib
import random
import sys
import tempfile
from typing import List, Union

import json5
import streamlit as st
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

sys.path.append('..')
sys.path.append('../..')

import helpers.icons_embeddings as ice
from global_config import GlobalConfig
from helpers import llm_helper, pptx_helper, text_helper


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
def _get_llm():
    """
    Get an LLM instance.

    :return: The LLM.
    """

    return llm_helper.get_hf_endpoint()


@st.cache_data
def _get_icons_list() -> List[str]:
    """
    Get a list of available icons names without the dir name and file extension.

    :return: A llist of the icons.
    """

    return ice.get_icons_list()


APP_TEXT = _load_strings()

# Session variables
CHAT_MESSAGES = 'chat_messages'
DOWNLOAD_FILE_KEY = 'download_file_name'
IS_IT_REFINEMENT = 'is_it_refinement'
APPROX_TARGET_LENGTH = GlobalConfig.LLM_MODEL_MAX_OUTPUT_LENGTH / 2


logger = logging.getLogger(__name__)

texts = list(GlobalConfig.PPTX_TEMPLATE_FILES.keys())
captions = [GlobalConfig.PPTX_TEMPLATE_FILES[x]['caption'] for x in texts]
pptx_template = st.sidebar.radio(
    'Select a presentation template:',
    texts,
    captions=captions,
    horizontal=True
)


def build_ui():
    """
    Display the input elements for content generation.
    """

    st.title(APP_TEXT['app_name'])
    st.subheader(APP_TEXT['caption'])
    st.markdown(
        '![Visitors](https://api.visitorbadge.io/api/visitors?path=https%3A%2F%2Fhuggingface.co%2Fspaces%2Fbarunsaha%2Fslide-deck-ai&countColor=%23263759)'  # noqa: E501
    )

    with st.expander('Usage Policies and Limitations'):
        st.text(APP_TEXT['tos'] + '\n\n' + APP_TEXT['tos2'])

    set_up_chat_ui()


def set_up_chat_ui():
    """
    Prepare the chat interface and related functionality.
    """

    with st.expander('Usage Instructions'):
        st.markdown(GlobalConfig.CHAT_USAGE_INSTRUCTIONS)
        st.markdown(
            '[SlideDeck AI](https://github.com/barun-saha/slide-deck-ai) is an Open-Source project.'  # noqa: E501
            ' It is is powered by'  # noqa: E501
            ' [Mistral-Nemo-Instruct-2407](https://huggingface.co/mistralai/Mistral-Nemo-Instruct-2407).'  # noqa: E501
        )

    st.info(
        'If you like SlideDeck AI, please consider leaving a heart ❤️ on the'
        ' [Hugging Face Space](https://huggingface.co/spaces/barunsaha/slide-deck-ai/) or'
        ' a star ⭐ on [GitHub](https://github.com/barun-saha/slide-deck-ai).'
        ' Your [feedback](https://forms.gle/JECFBGhjvSj7moBx9) is appreciated.'
    )

    # view_messages = st.expander('View the messages in the session state')

    st.chat_message('ai').write(
        random.choice(APP_TEXT['ai_greetings'])
    )

    history = StreamlitChatMessageHistory(key=CHAT_MESSAGES)

    if _is_it_refinement():
        template = _get_prompt_template(is_refinement=True)
    else:
        template = _get_prompt_template(is_refinement=False)

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
        if not text_helper.is_valid_prompt(prompt):
            st.error(
                'Not enough information provided!'
                ' Please be a little more descriptive and type a few words'
                ' with a few characters :)'
            )
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
                    'previous_content': _get_last_response(),
                    'icons_list': '\n'.join(_get_icons_list())
                }
            )
        else:
            formatted_template = prompt_template.format(
                **{
                    'question': prompt,
                    'icons_list': '\n'.join(_get_icons_list())
                }
            )

        progress_bar = st.progress(0, 'Preparing to call LLM...')
        response = ''

        for chunk in _get_llm().stream(formatted_template):
            response += chunk

            # Update the progress bar
            progress_percentage = min(len(response) / APPROX_TARGET_LENGTH, 0.95)
            progress_bar.progress(
                progress_percentage,
                text='Streaming content...this might take a while...'
            )

        history.add_user_message(prompt)
        history.add_ai_message(response)

        # The content has been generated as JSON
        # There maybe trailing ``` at the end of the response -- remove them
        # To be careful: ``` may be part of the content as well when code is generated
        response_cleaned = text_helper.get_clean_json(response)

        logger.info(
            'Cleaned JSON response:: original length: %d | cleaned length: %d',
            len(response), len(response_cleaned)
        )
        # logger.debug('Cleaned JSON: %s', response_cleaned)

        # Now create the PPT file
        progress_bar.progress(
            GlobalConfig.LLM_PROGRESS_MAX,
            text='Finding photos online and generating the slide deck...'
        )
        path = generate_slide_deck(response_cleaned)
        progress_bar.progress(1.0, text='Done!')

        st.chat_message('ai').code(response, language='json')

        if path:
            _display_download_button(path)

        logger.info(
            '#messages in history / 2: %d',
            len(st.session_state[CHAT_MESSAGES]) / 2
        )


def generate_slide_deck(json_str: str) -> Union[pathlib.Path, None]:
    """
    Create a slide deck and return the file path. In case there is any error creating the slide
    deck, the path may be to an empty file.

    :param json_str: The content in *valid* JSON format.
    :return: The path to the .pptx file or `None` in case of error.
    """

    try:
        parsed_data = json5.loads(json_str)
    except ValueError:
        st.error(
            'Encountered error while parsing JSON...will fix it and retry'
        )
        logger.error(
            'Caught ValueError: trying again after repairing JSON...'
        )
        try:
            parsed_data = json5.loads(text_helper.fix_malformed_json(json_str))
        except ValueError:
            st.error(
                'Encountered an error again while fixing JSON...'
                'the slide deck cannot be created, unfortunately ☹'
                '\nPlease try again later.'
            )
            logger.error(
                'Caught ValueError: failed to repair JSON!'
            )

            return None

    if DOWNLOAD_FILE_KEY in st.session_state:
        path = pathlib.Path(st.session_state[DOWNLOAD_FILE_KEY])
    else:
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.pptx')
        path = pathlib.Path(temp.name)
        st.session_state[DOWNLOAD_FILE_KEY] = str(path)

        if temp:
            temp.close()

    try:
        logger.debug('Creating PPTX file: %s...', st.session_state[DOWNLOAD_FILE_KEY])
        pptx_helper.generate_powerpoint_presentation(
            parsed_data,
            slides_template=pptx_template,
            output_file_path=path
        )
    except Exception as ex:
        st.error(APP_TEXT['content_generation_error'])
        logger.error('Caught a generic exception: %s', str(ex))

    return path


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
