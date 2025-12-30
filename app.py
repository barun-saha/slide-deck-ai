"""
Streamlit app containing the UI and the application logic.
"""
import datetime
import logging
import os
import pathlib
import random
import sys

import httpx
import json5
import ollama
import requests
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath('src'))
from slidedeckai.core import SlideDeckAI
from slidedeckai import global_config as gcfg
from slidedeckai.global_config import GlobalConfig
from slidedeckai.helpers import llm_helper, text_helper
import slidedeckai.helpers.file_manager as filem
from slidedeckai.helpers.chat_helper import ChatMessage, HumanMessage, AIMessage
from slidedeckai.helpers import chat_helper


load_dotenv()
logger = logging.getLogger(__name__)


RUN_IN_OFFLINE_MODE = os.getenv('RUN_IN_OFFLINE_MODE', 'False').lower() == 'true'

# Session variables
SLIDE_GENERATOR = 'slide_generator_instance'
CHAT_MESSAGES = 'chat_messages'
DOWNLOAD_FILE_KEY = 'download_file_name'
IS_IT_REFINEMENT = 'is_it_refinement'
ADDITIONAL_INFO = 'additional_info'
PDF_FILE_KEY = 'pdf_file'
API_INPUT_KEY = 'api_key_input'

TEXTS = list(GlobalConfig.PPTX_TEMPLATE_FILES.keys())
CAPTIONS = [GlobalConfig.PPTX_TEMPLATE_FILES[x]['caption'] for x in TEXTS]


class StreamlitChatMessageHistory:
    """Chat message history stored in Streamlit session state."""

    def __init__(self, key: str):
        """Initialize the chat message history."""
        self.key = key
        if key not in st.session_state:
            st.session_state[key] = []

    @property
    def messages(self):
        """Get all chat messages in the history."""
        return st.session_state[self.key]

    def add_user_message(self, content: str):
        """Add a user message to the history."""
        st.session_state[self.key].append(HumanMessage(content))

    def add_ai_message(self, content: str):
        """Add an AI message to the history."""
        st.session_state[self.key].append(AIMessage(content))


@st.cache_data
def _load_strings() -> dict:
    """
    Load various strings to be displayed in the app.

    Returns:
        The dictionary of strings.
    """
    with open(GlobalConfig.APP_STRINGS_FILE, 'r', encoding='utf-8') as in_file:
        return json5.loads(in_file.read())


@st.cache_data
def _get_prompt_template(is_refinement: bool) -> str:
    """
    Return a prompt template.

    Args:
        is_refinement: Whether this is the initial or refinement prompt.

    Returns:
        The prompt template as f-string.
    """
    if is_refinement:
        with open(GlobalConfig.REFINEMENT_PROMPT_TEMPLATE, 'r', encoding='utf-8') as in_file:
            template = in_file.read()
    else:
        with open(GlobalConfig.INITIAL_PROMPT_TEMPLATE, 'r', encoding='utf-8') as in_file:
            template = in_file.read()

    return template


def are_all_inputs_valid(
        user_prompt: str,
        provider: str,
        selected_model: str,
        user_key: str,
        azure_deployment_url: str = '',
        azure_endpoint_name: str = '',
        azure_api_version: str = '',
) -> bool:
    """
    Validate user input and LLM selection.

    Args:
        user_prompt: The prompt.
        provider: The LLM provider.
        selected_model: Name of the model.
        user_key: User-provided API key.
        azure_deployment_url: Azure OpenAI deployment URL.
        azure_endpoint_name: Azure OpenAI model endpoint.
        azure_api_version: Azure OpenAI API version.

    Returns:
        `True` if all inputs "look" OK; `False` otherwise.
    """
    if not text_helper.is_valid_prompt(user_prompt):
        handle_error(
            'Not enough information provided!'
            ' Please be a little more descriptive and type a few words'
            ' with a few characters :)',
            False
        )
        return False

    if not provider or not selected_model:
        handle_error('No valid LLM provider and/or model name found!', False)
        return False

    if not llm_helper.is_valid_llm_provider_model(
            provider, selected_model, user_key,
            azure_endpoint_name, azure_deployment_url, azure_api_version
    ):
        handle_error(
            'The LLM settings do not look correct. Make sure that an API key/access token'
            ' is provided if the selected LLM requires it. An API key should be 6-200 characters'
            ' long, only containing alphanumeric characters, hyphens, and underscores.\n\n'
            'If you are using Azure OpenAI, make sure that you have provided the additional and'
            ' correct configurations.',
            False
        )
        return False

    return True


def handle_error(error_msg: str, should_log: bool):
    """
    Display an error message in the app.

    Args:
        error_msg: The error message to be displayed.
        should_log: If `True`, log the message.
    """
    if should_log:
        logger.error(error_msg)

    st.error(error_msg)


def reset_api_key():
    """
    Clear API key input when a different LLM is selected from the dropdown list.
    """
    st.session_state.api_key_input = ''


def reset_chat_history():
    """
    Clear the chat history and related session state variables.
    """
    # Clear session state variables using pop with None default
    st.session_state.pop(SLIDE_GENERATOR, None)
    st.session_state.pop(CHAT_MESSAGES, None)
    st.session_state.pop(IS_IT_REFINEMENT, None)
    st.session_state.pop(ADDITIONAL_INFO, None)
    st.session_state.pop(PDF_FILE_KEY, None)
    
    # Remove previously generated temp PPTX file
    temp_pptx_path = st.session_state.pop(DOWNLOAD_FILE_KEY, None)
    if temp_pptx_path:
        pptx_path = pathlib.Path(temp_pptx_path)
        if pptx_path.exists() and pptx_path.is_file():
            pptx_path.unlink()


APP_TEXT = _load_strings()


# -----= UI display begins here =-----


with st.sidebar:
    # New Chat button at the top of sidebar
    col1, col2, col3 = st.columns([.17, 0.8, .1])
    with col2:
        if st.button('New Chat 💬', help='Start a new conversation', key='new_chat_button'):
            reset_chat_history()  # Reset the chat history when the button is clicked
    
    # The PPT templates
    pptx_template = st.sidebar.radio(
        '1: Select a presentation template:',
        TEXTS,
        captions=CAPTIONS,
        horizontal=True
    )

    if RUN_IN_OFFLINE_MODE:
        llm_provider_to_use = st.text_input(
            label='2: Enter Ollama model name to use (e.g., gemma3:1b):',
            help=(
                'Specify a correct, locally available LLM, found by running `ollama list`, for'
                ' example, `gemma3:1b`, `mistral:v0.2`, and `mistral-nemo:latest`. Having an'
                ' Ollama-compatible and supported GPU is strongly recommended.'
            )
        )
        # If a SlideDeckAI instance already exists in session state, update its model
        # to reflect the user change rather than reusing the old model
        # No API key required for local models
        if SLIDE_GENERATOR in st.session_state and llm_provider_to_use:
            try:
                st.session_state[SLIDE_GENERATOR].set_model(llm_provider_to_use)
            except Exception as e:
                logger.error('Failed to update model on existing SlideDeckAI: %s', e)
                # If updating fails, drop the stored instance so a new one is created
                st.session_state.pop(SLIDE_GENERATOR, None)

        api_key_token: str = ''
        azure_endpoint: str = ''
        azure_deployment: str = ''
        api_version: str = ''
    else:
        # The online LLMs
        llm_provider_to_use = st.sidebar.selectbox(
            label='2: Select a suitable LLM to use:\n\n(Gemini and Mistral-Nemo are recommended)',
            options=[f'{k} ({v["description"]})' for k, v in GlobalConfig.VALID_MODELS.items()],
            index=GlobalConfig.DEFAULT_MODEL_INDEX,
            help=GlobalConfig.LLM_PROVIDER_HELP,
            on_change=reset_api_key
        ).split(' ')[0]
        
        # --- Automatically fetch API key from .env if available ---
        # Extract provider key using regex
        provider_match = GlobalConfig.PROVIDER_REGEX.match(llm_provider_to_use)
        if provider_match:
            selected_provider = provider_match.group(1)
        else:
            # If regex doesn't match, try to extract provider from the beginning
            selected_provider = (
                llm_provider_to_use.split(' ')[0]
                if ' ' in llm_provider_to_use else llm_provider_to_use
            )
            logger.warning(
                'Provider regex did not match for: %s, using: %s',
                llm_provider_to_use, selected_provider
            )
        
        # Validate that the selected provider is valid
        if selected_provider not in GlobalConfig.VALID_PROVIDERS:
            logger.error('Invalid provider: %s', selected_provider)
            handle_error(f'Invalid provider selected: {selected_provider}', True)
            st.stop()
        
        env_key_name = GlobalConfig.PROVIDER_ENV_KEYS.get(selected_provider)
        default_api_key = os.getenv(env_key_name, '') if env_key_name else ''

        # Always sync session state to env value if needed (autofill on provider change)
        if default_api_key and st.session_state.get(API_INPUT_KEY, None) != default_api_key:
            st.session_state[API_INPUT_KEY] = default_api_key

        api_key_token = st.text_input(
            label=(
                '3: Paste your API key/access token:\n\n'
                '*Mandatory* for all providers.'
            ),
            key=API_INPUT_KEY,
            type='password',
            disabled=bool(default_api_key),
        )

        # If a model was updated in the sidebar, make sure to update it in the SlideDeckAI instance
        if SLIDE_GENERATOR in st.session_state and llm_provider_to_use:
            try:
                st.session_state[SLIDE_GENERATOR].set_model(llm_provider_to_use, api_key_token)
            except Exception as e:
                logger.error('Failed to update model on existing SlideDeckAI: %s', e)
                # If updating fails, drop the stored instance so a new one is created
                st.session_state.pop(SLIDE_GENERATOR, None)

        # Additional configs for Azure OpenAI
        with st.expander('**Azure OpenAI-specific configurations**'):
            azure_endpoint = st.text_input(
                label=(
                    '4: Azure endpoint URL, e.g., https://example.openai.azure.com/.\n\n'
                    '*Mandatory* for Azure OpenAI (only).'
                )
            )
            azure_deployment = st.text_input(
                label=(
                    '5: Deployment name on Azure OpenAI:\n\n'
                    '*Mandatory* for Azure OpenAI (only).'
                ),
            )
            api_version = st.text_input(
                label=(
                    '6: API version:\n\n'
                    '*Mandatory* field. Change based on your deployment configurations.'
                ),
                value='2024-05-01-preview',
            )

    # Make slider with initial values
    page_range_slider = st.slider(
        'Specify a page range for the uploaded PDF file (if any):',
        1, GlobalConfig.MAX_ALLOWED_PAGES,
        [1, GlobalConfig.MAX_ALLOWED_PAGES]
    )
    st.session_state['page_range_slider'] = page_range_slider


def build_ui():
    """
    Display the input elements for content generation.
    """
    st.title(APP_TEXT['app_name'])
    st.subheader(APP_TEXT['caption'])
    st.markdown(
        '![Visitors](https://api.visitorbadge.io/api/visitors?path=https%3A%2F%2Fhuggingface.co%2Fspaces%2Fbarunsaha%2Fslide-deck-ai&countColor=%23263759)'  # noqa: E501
    )

    today = datetime.date.today()
    if today.month == 1 and 1 <= today.day <= 15:
        st.success(
            (
                'Wishing you a happy and successful New Year!'
                ' It is your appreciation that keeps SlideDeck AI going.'
                f' May you make some great slide decks in {today.year} ✨'
            ),
            icon='🎆'
        )

    with st.expander('Usage Policies and Limitations'):
        st.text(APP_TEXT['tos'] + '\n\n' + APP_TEXT['tos2'])

    set_up_chat_ui()


def set_up_chat_ui():
    """
    Prepare the chat interface and related functionality.
    """
    # Set start and end page
    st.session_state['start_page'] = st.session_state['page_range_slider'][0]
    st.session_state['end_page'] = st.session_state['page_range_slider'][1]

    with st.expander('Usage Instructions'):
        st.markdown(GlobalConfig.CHAT_USAGE_INSTRUCTIONS)

    st.info(APP_TEXT['like_feedback'])
    st.chat_message('ai').write(random.choice(APP_TEXT['ai_greetings']))

    history = StreamlitChatMessageHistory(key=CHAT_MESSAGES)

    # Since Streamlit app reloads at every interaction, display the chat history
    # from the save session state
    for msg in history.messages:
        st.chat_message(msg.type).code(msg.content, language='json')

    # Chat input at the bottom
    prompt = st.chat_input(
        placeholder=APP_TEXT['chat_placeholder'],
        max_chars=GlobalConfig.LLM_MODEL_MAX_INPUT_LENGTH,
        accept_file=True,
        file_type=['pdf', ],
    )

    if prompt:
        prompt_text = prompt.text or ''
        if prompt['files']:
            # Store uploaded pdf in session state
            uploaded_pdf = prompt['files'][0]
            st.session_state[PDF_FILE_KEY] = uploaded_pdf
            # Apparently, Streamlit stores uploaded files in memory and clears on browser close
            # https://docs.streamlit.io/knowledge-base/using-streamlit/where-file-uploader-store-when-deleted

        # Check if pdf file is uploaded
        # (we can use the same file if the user doesn't upload a new one)
        if PDF_FILE_KEY in st.session_state:
            # Get validated page range
            (
                st.session_state['start_page'],
                st.session_state['end_page']
            ) = filem.validate_page_range(
                st.session_state[PDF_FILE_KEY],
                st.session_state['start_page'],
                st.session_state['end_page']
            )
            # Show sidebar text for page selection and file name
            with st.sidebar:
                if st.session_state['end_page'] is None:  # If the PDF has only one page
                    st.text(
                        f'Extracting page {st.session_state["start_page"]} in'
                        f' {st.session_state["pdf_file"].name}'
                    )
                else:
                    st.text(
                        f'Extracting pages {st.session_state["start_page"]} to'
                        f' {st.session_state["end_page"]} in {st.session_state["pdf_file"].name}'
                    )

        st.chat_message('user').write(prompt_text)

        if SLIDE_GENERATOR in st.session_state:
            slide_generator = st.session_state[SLIDE_GENERATOR]
        else:
            slide_generator = SlideDeckAI(
                model=llm_provider_to_use,
                topic=prompt_text,
                api_key=api_key_token.strip(),
                template_idx=list(GlobalConfig.PPTX_TEMPLATE_FILES.keys()).index(pptx_template),
                pdf_path_or_stream=st.session_state.get(PDF_FILE_KEY),
                pdf_page_range=(
                    st.session_state.get('start_page'), st.session_state.get('end_page')
                ),
            )
            st.session_state[SLIDE_GENERATOR] = slide_generator

        progress_bar = st.progress(0, 'Preparing to call LLM...')

        def progress_callback(current_progress):
            progress_bar.progress(
                min(current_progress / gcfg.get_max_output_tokens(llm_provider_to_use), 0.95),
                text='Streaming content...this might take a while...'
            )

        try:
            if _is_it_refinement():
                path = slide_generator.revise(
                    instructions=prompt_text, progress_callback=progress_callback
                )
            else:
                path = slide_generator.generate(progress_callback=progress_callback)

            progress_bar.progress(1.0, text='Done!')

            if path:
                st.session_state[DOWNLOAD_FILE_KEY] = str(path)
                history.add_user_message(prompt_text)
                history.add_ai_message(slide_generator.last_response)
                st.chat_message('ai').code(slide_generator.last_response, language='json')
                _display_download_button(path)
            else:
                handle_error('Failed to generate slide deck.', True)

        except (httpx.ConnectError, requests.exceptions.ConnectionError):
            handle_error(
                'A connection error occurred while streaming content from the LLM endpoint.'
                ' Unfortunately, the slide deck cannot be generated. Please try again later.'
                ' Alternatively, try selecting a different LLM from the dropdown list. If you are'
                ' using Ollama, make sure that Ollama is already running on your system.',
                True
            )
        except ollama.ResponseError:
            handle_error(
                'The model is unavailable with Ollama on your system.'
                ' Make sure that you have provided the correct LLM name or pull it.'
                ' View LLMs available locally by running `ollama list`.',
                True
            )
        except Exception as ex:
            if 'litellm.AuthenticationError' in str(ex):
                handle_error(
                    'LLM API authentication failed. Make sure that you have provided'
                    ' a valid, correct API key. Read **[how to get free LLM API keys]'
                    '(https://github.com/barun-saha/slide-deck-ai?tab=readme-ov-file'
                    '#unmatched-flexibility-choose-your-ai-brain)**.',
                    True
                )
            else:
                handle_error('An unexpected error occurred: ' + str(ex), True)


def _is_it_refinement() -> bool:
    """
    Whether it is the initial prompt or a refinement.

    Returns:
        True if it is the initial prompt; False otherwise.
    """
    if IS_IT_REFINEMENT in st.session_state:
        return True

    if len(st.session_state[CHAT_MESSAGES]) >= 2:
        # Prepare for the next call
        st.session_state[IS_IT_REFINEMENT] = True
        return True

    return False


def _get_user_messages() -> list[str]:
    """
    Get a list of user messages submitted until now from the session state.

    Returns:
        The list of user messages.
    """
    return [
        msg.content for msg in st.session_state[CHAT_MESSAGES]
        if isinstance(msg, chat_helper.HumanMessage)
    ]


def _display_download_button(file_path: pathlib.Path):
    """
    Display a download button to download a slide deck.

    Args:
        file_path: The path of the .pptx file.
    """
    with open(file_path, 'rb') as download_file:
        st.download_button(
            'Download PPTX file ⬇️',
            data=download_file,
            file_name='Presentation.pptx',
            key=datetime.datetime.now()
        )


if __name__ == '__main__':
    build_ui()
