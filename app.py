"""
Streamlit app containing the UI and the application logic.
"""
import datetime
import logging
import os
import pathlib
import random
import tempfile
from typing import List, Union

import httpx
import huggingface_hub
import json5
import ollama
import requests
import streamlit as st
from dotenv import load_dotenv
from streamlit_extras.bottom_container import bottom

import global_config as gcfg
import helpers.file_manager as filem
from global_config import GlobalConfig
from helpers import chat_helper, llm_helper, pptx_helper, text_helper

load_dotenv()

RUN_IN_OFFLINE_MODE = os.getenv('RUN_IN_OFFLINE_MODE', 'False').lower() == 'true'


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

    :param user_prompt: The prompt.
    :param provider: The LLM provider.
    :param selected_model: Name of the model.
    :param user_key: User-provided API key.
    :param azure_deployment_url: Azure OpenAI deployment URL.
    :param azure_endpoint_name: Azure OpenAI model endpoint.
    :param azure_api_version: Azure OpenAI API version.
    :return: `True` if all inputs "look" OK; `False` otherwise.
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
            ' is provided if the selected LLM requires it. An API key should be 6-94 characters'
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

    :param error_msg: The error message to be displayed.
    :param should_log: If `True`, log the message.
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
    if CHAT_MESSAGES in st.session_state:
        del st.session_state[CHAT_MESSAGES]
    if IS_IT_REFINEMENT in st.session_state:
        del st.session_state[IS_IT_REFINEMENT]
    if ADDITIONAL_INFO in st.session_state:
        del st.session_state[ADDITIONAL_INFO]
    if 'pdf_file' in st.session_state:
        del st.session_state['pdf_file']
    if DOWNLOAD_FILE_KEY in st.session_state:
        del st.session_state[DOWNLOAD_FILE_KEY]
    st.rerun()


APP_TEXT = _load_strings()

# Session variables
CHAT_MESSAGES = 'chat_messages'
DOWNLOAD_FILE_KEY = 'download_file_name'
IS_IT_REFINEMENT = 'is_it_refinement'
ADDITIONAL_INFO = 'additional_info'


logger = logging.getLogger(__name__)

texts = list(GlobalConfig.PPTX_TEMPLATE_FILES.keys())
captions = [GlobalConfig.PPTX_TEMPLATE_FILES[x]['caption'] for x in texts]

with st.sidebar:
    # Reset button at the top of sidebar
    if st.button("🔄 Reset Chat", help="Clear chat history and start a new conversation", use_container_width=True):
        reset_chat_history()
    
    st.markdown("---")  # Separator
    
    # The PPT templates
    pptx_template = st.sidebar.radio(
        '1: Select a presentation template:',
        texts,
        captions=captions,
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
        api_key_token: str = ''
        azure_endpoint: str = ''
        azure_deployment: str = ''
        api_version: str = ''
    else:
        # The online LLMs
        selected_option = st.sidebar.selectbox(
            label='2: Select a suitable LLM to use:\n\n(Gemini and Mistral-Nemo are recommended)',
            options=[f'{k} ({v["description"]})' for k, v in GlobalConfig.VALID_MODELS.items()],
            index=GlobalConfig.DEFAULT_MODEL_INDEX,
            help=GlobalConfig.LLM_PROVIDER_HELP,
            on_change=reset_api_key
        )
        
        # Extract provider key more robustly using regex
        provider_match = GlobalConfig.PROVIDER_REGEX.match(selected_option)
        if provider_match:
            llm_provider_to_use = selected_option  # Use full string for get_provider_model
        else:
            # Fallback: try to extract the key before the first space
            llm_provider_to_use = selected_option.split(' ')[0]
            logger.warning(f"Could not parse provider from selectbox option: {selected_option}")

        # --- Automatically fetch API key from .env if available ---
        provider_match = GlobalConfig.PROVIDER_REGEX.match(llm_provider_to_use)
        if provider_match:
            selected_provider = provider_match.group(1)
        else:
            # If regex doesn't match, try to extract provider from the beginning
            selected_provider = llm_provider_to_use.split(' ')[0] if ' ' in llm_provider_to_use else llm_provider_to_use
            logger.warning(f"Provider regex did not match for: {llm_provider_to_use}, using: {selected_provider}")
        
        # Validate that the selected provider is valid
        if selected_provider not in GlobalConfig.VALID_PROVIDERS:
            logger.error(f"Invalid provider: {selected_provider}")
            handle_error(f"Invalid provider selected: {selected_provider}", True)
            st.error(f"Invalid provider selected: {selected_provider}")
            st.stop()
        
        env_key_name = GlobalConfig.PROVIDER_ENV_KEYS.get(selected_provider)
        default_api_key = os.getenv(env_key_name, "") if env_key_name else ""

        # Always sync session state to env value if needed (autofill on provider change)
        if default_api_key and st.session_state.get('api_key_input', None) != default_api_key:
            st.session_state['api_key_input'] = default_api_key

        api_key_token = st.text_input(
            label=(
                '3: Paste your API key/access token:\n\n'
                '*Mandatory* for all providers.'
            ),
            key='api_key_input',
            type='password',
            disabled=bool(default_api_key),
        )

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

    history = chat_helper.StreamlitChatMessageHistory(key=CHAT_MESSAGES)
    prompt_template = chat_helper.ChatPromptTemplate.from_template(
        _get_prompt_template(
            is_refinement=_is_it_refinement()
        )
    )

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
            st.session_state['pdf_file'] = uploaded_pdf
            # Apparently, Streamlit stores uploaded files in memory and clears on browser close
            # https://docs.streamlit.io/knowledge-base/using-streamlit/where-file-uploader-store-when-deleted

        # Check if pdf file is uploaded
        # (we can use the same file if the user doesn't upload a new one)
        if 'pdf_file' in st.session_state:
            # Get validated page range
            (
                st.session_state['start_page'],
                st.session_state['end_page']
            ) = filem.validate_page_range(
                st.session_state['pdf_file'],
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

            # Get pdf contents
            st.session_state[ADDITIONAL_INFO] = filem.get_pdf_contents(
                st.session_state['pdf_file'],
                (st.session_state['start_page'], st.session_state['end_page'])
            )
        provider, llm_name = llm_helper.get_provider_model(
            llm_provider_to_use,
            use_ollama=RUN_IN_OFFLINE_MODE
        )

        # Validate that provider and model were parsed successfully
        if not provider or not llm_name:
            handle_error(
                f'Failed to parse provider and model from: "{llm_provider_to_use}". '
                f'Please select a valid LLM from the dropdown.',
                True
            )
            return

        user_key = api_key_token.strip()
        az_deployment = azure_deployment.strip()
        az_endpoint = azure_endpoint.strip()
        api_ver = api_version.strip()

        if not are_all_inputs_valid(
                prompt_text, provider, llm_name, user_key,
                az_deployment, az_endpoint, api_ver
        ):
            return

        logger.info(
            'User input: %s | #characters: %d | LLM: %s',
            prompt_text, len(prompt_text), llm_name
        )
        st.chat_message('user').write(prompt_text)

        if _is_it_refinement():
            user_messages = _get_user_messages()
            user_messages.append(prompt_text)
            list_of_msgs = [
                f'{idx + 1}. {msg}' for idx, msg in enumerate(user_messages)
            ]
            formatted_template = prompt_template.format(
                **{
                    'instructions': '\n'.join(list_of_msgs),
                    'previous_content': _get_last_response(),
                    'additional_info': st.session_state.get(ADDITIONAL_INFO, ''),
                }
            )
        else:
            formatted_template = prompt_template.format(
                **{
                    'question': prompt_text,
                    'additional_info': st.session_state.get(ADDITIONAL_INFO, ''),
                }
            )

        progress_bar = st.progress(0, 'Preparing to call LLM...')
        response = ''

        try:
            llm = llm_helper.get_litellm_llm(
                provider=provider,
                model=llm_name,
                max_new_tokens=gcfg.get_max_output_tokens(llm_provider_to_use),
                api_key=user_key,
                azure_endpoint_url=az_endpoint,
                azure_deployment_name=az_deployment,
                azure_api_version=api_ver,
            )

            if not llm:
                handle_error(
                    'Failed to create an LLM instance! Make sure that you have selected the'
                    ' correct model from the dropdown list and have provided correct API key'
                    ' or access token.',
                    False
                )
                return

            for chunk in llm.stream(formatted_template):
                if isinstance(chunk, str):
                    response += chunk
                else:
                    content = getattr(chunk, 'content', None)
                    if content is not None:
                        response += content
                    else:
                        response += str(chunk)

                # Update the progress bar with an approx progress percentage
                progress_bar.progress(
                    min(
                        len(response) / gcfg.get_max_output_tokens(llm_provider_to_use),
                        0.95
                    ),
                    text='Streaming content...this might take a while...'
                )
        except (httpx.ConnectError, requests.exceptions.ConnectionError):
            handle_error(
                'A connection error occurred while streaming content from the LLM endpoint.'
                ' Unfortunately, the slide deck cannot be generated. Please try again later.'
                ' Alternatively, try selecting a different LLM from the dropdown list. If you are'
                ' using Ollama, make sure that Ollama is already running on your system.',
                True
            )
            return
        except huggingface_hub.errors.ValidationError as ve:
            handle_error(
                f'An error occurred while trying to generate the content: {ve}'
                '\nPlease try again with a significantly shorter input text.',
                True
            )
            return
        except ollama.ResponseError:
            handle_error(
                f'The model `{llm_name}` is unavailable with Ollama on your system.'
                f' Make sure that you have provided the correct LLM name or pull it using'
                f' `ollama pull {llm_name}`. View LLMs available locally by running `ollama list`.',
                True
            )
            return
        except Exception as ex:
            _msg = str(ex)
            if 'payment required' in _msg.lower():
                handle_error(
                    'The available inference quota has exhausted.'
                    ' Please use your own Hugging Face access token. Paste your token in'
                    ' the input field on the sidebar to the left.'
                    '\n\nDon\'t have a token? Get your free'
                    ' [HF access token](https://huggingface.co/settings/tokens) now'
                    ' and start creating your slide deck! For gated models, you may need to'
                    ' visit the model\'s page and accept the terms or service.'
                    '\n\nAlternatively, choose a different LLM and provider from the list.',
                    should_log=True
                )
            else:
                handle_error(
                    f'An unexpected error occurred while generating the content: {_msg}'
                    '\n\nPlease try again later, possibly with different inputs.'
                    ' Alternatively, try selecting a different LLM from the dropdown list.'
                    ' If you are using Azure OpenAI, Cohere, Gemini, or Together AI models, make'
                    ' sure that you have provided a correct API key.'
                    ' Read **[how to get free LLM API keys](https://github.com/barun-saha/slide-deck-ai?tab=readme-ov-file#summary-of-the-llms)**.',
                    True
                )
            return

        history.add_user_message(prompt_text)
        history.add_ai_message(response)

        # The content has been generated as JSON
        # There maybe trailing ``` at the end of the response -- remove them
        # To be careful: ``` may be part of the content as well when code is generated
        response = text_helper.get_clean_json(response)
        logger.info(
            'Cleaned JSON length: %d', len(response)
        )

        # Now create the PPT file
        progress_bar.progress(
            GlobalConfig.LLM_PROGRESS_MAX,
            text='Finding photos online and generating the slide deck...'
        )
        progress_bar.progress(1.0, text='Done!')
        st.chat_message('ai').code(response, language='json')

        if path := generate_slide_deck(response):
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
        handle_error(
            'Encountered error while parsing JSON...will fix it and retry',
            True
        )
        try:
            parsed_data = json5.loads(text_helper.fix_malformed_json(json_str))
        except ValueError:
            handle_error(
                'Encountered an error again while fixing JSON...'
                'the slide deck cannot be created, unfortunately ☹'
                '\nPlease try again later.',
                True
            )
            return None
    except RecursionError:
        handle_error(
            'Encountered a recursion error while parsing JSON...'
            'the slide deck cannot be created, unfortunately ☹'
            '\nPlease try again later.',
            True
        )
        return None
    except Exception:
        handle_error(
            'Encountered an error while parsing JSON...'
            'the slide deck cannot be created, unfortunately ☹'
            '\nPlease try again later.',
            True
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
        msg.content for msg in st.session_state[CHAT_MESSAGES] if isinstance(msg, chat_helper.HumanMessage)
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
