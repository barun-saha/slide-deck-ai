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
from pypdf import PdfReader
import requests
import streamlit as st
from streamlit_float import * # for floating UI elements
from dotenv import load_dotenv
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

import global_config as gcfg
import helpers.file_manager as filem
from global_config import GlobalConfig
from helpers import llm_helper, pptx_helper, text_helper

load_dotenv()

RUN_IN_OFFLINE_MODE = os.getenv('RUN_IN_OFFLINE_MODE', 'False').lower() == 'true'

float_init()  # Initialize streamlit_float

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
        selected_provider: str,
        selected_model: str,
        user_key: str,
        azure_deployment_url: str = '',
        azure_endpoint_name: str = '',
        azure_api_version: str = '',
) -> bool:
    """
    Validate user input and LLM selection.

    :param user_prompt: The prompt.
    :param selected_provider: The LLM provider.
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

    if not selected_provider or not selected_model:
        handle_error('No valid LLM provider and/or model name found!', False)
        return False

    if not llm_helper.is_valid_llm_provider_model(
            selected_provider, selected_model, user_key,
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
    # The PPT templates
    pptx_template = st.sidebar.radio(
        '1: Select a presentation template:',
        texts,
        captions=captions,
        horizontal=True
    )

    if RUN_IN_OFFLINE_MODE:
        llm_provider_to_use = st.text_input(
            label='2: Enter Ollama model name to use (e.g., mistral:v0.2):',
            help=(
                'Specify a correct, locally available LLM, found by running `ollama list`, for'
                ' example `mistral:v0.2` and `mistral-nemo:latest`. Having an Ollama-compatible'
                ' and supported GPU is strongly recommended.'
            )
        )
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
        provider_match = GlobalConfig.PROVIDER_REGEX.match(llm_provider_to_use)
        selected_provider = provider_match.group(1) if provider_match else llm_provider_to_use
        env_key_name = GlobalConfig.PROVIDER_ENV_KEYS.get(selected_provider)
        default_api_key = os.getenv(env_key_name, "") if env_key_name else ""

        # Always sync session state to env value if needed (auto-fill on provider change)
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

def apply_custom_css():
    # Custom CSS so that the file upload area is kind of transparent, remains near the bottom but is
    # a little enlarged for ease of use, and the extra things that are normally part of st.file_uploader, 
    # i.e. the "Drag and Drop File Here" label, the pdf's name and size label, upload icon, and browse files button, 
    # are hidden. What this CSS does is produce a simple 'zone' that the user can click or drop a file on. 
    st.markdown(
        '''
        <style>
            
            div[data-testid="stFileUploader"]{
                position:relative;
                opacity:0.5;
                width:200%;
                height:100px;
                left:-105%;
            }
            section[data-testid="stFileUploaderDropzone"]{
                position:absolute;
                width:100%;
                height:100%;
                top:0;
            }
            div[data-testid="stFileUploaderDropzoneInstructions"]{
                display:none;
            }
            div[data-testid="stFileUploaderFile"]{
                display:none;
            }
            div[data-testid="stFileUploaderFileName"]{
                display:none;
            }
        </style>
        ''',
        unsafe_allow_html=True
    )

def set_up_chat_ui():
    """
    Prepare the chat interface and related functionality.
    """

    with st.expander('Usage Instructions'):
        st.markdown(GlobalConfig.CHAT_USAGE_INSTRUCTIONS)

    st.info(APP_TEXT['like_feedback'])
    st.chat_message('ai').write(random.choice(APP_TEXT['ai_greetings']))

    history = StreamlitChatMessageHistory(key=CHAT_MESSAGES)
    prompt_template = ChatPromptTemplate.from_template(
        _get_prompt_template(
            is_refinement=_is_it_refinement()
        )
    )

    # Since Streamlit app reloads at every interaction, display the chat history
    # from the save session state
    for msg in history.messages:
        st.chat_message(msg.type).code(msg.content, language='json')

    # container to hold chat field
    prompt_container = st.container()
    with prompt_container:
        # Chat input below the uploader
        prompt = st.chat_input(
            placeholder=APP_TEXT['chat_placeholder'],
            max_chars=GlobalConfig.LLM_MODEL_MAX_INPUT_LENGTH,
            file_type=['pdf', ],
        )
    # make it stick near bottom 
    prompt_container.float("bottom:40px;width:50%;z-index:999;font-size:10pt;")

    # some CSS to simplify the look of the upload area
    apply_custom_css()

    # container to hold uploader
    upload_container = st.container()
    with upload_container:
        uploaded_pdf = st.file_uploader(
            "",
            type=["pdf"],
            label_visibility="visible",
        )

    # PDF Processing and Slider Logic
    if uploaded_pdf:
        reader = PdfReader(uploaded_pdf)
        total_pages = len(reader.pages)
        st.session_state["pdf_page_count"] = total_pages

        # Slider for page range
        max_slider = min(50, total_pages)  # enforce 50 page limit

        with st.sidebar:
            # display the pdf's name
            st.text(f"PDF Uploaded: {uploaded_pdf.name}")
            
            st.slider(
                label="4: Specify a page range to examine:",
                min_value=1,
                max_value=max_slider,
                value=(1, max_slider),
                key="page_range"
            )

    # make container stay near bottom too, but surround the chat and have dotted border for the visual cue
    upload_container.float("border-style:dashed solid;bottom:10px;width:150%;height:100px;font-size:10pt;left:0;")

    if prompt:
        prompt_text = prompt

        # if the user uploaded a pdf and specified a range, get the contents
        if uploaded_pdf and "page_range" in st.session_state:
            st.session_state[ADDITIONAL_INFO] = filem.get_pdf_contents(
                uploaded_pdf,
                st.session_state["page_range"]
            )

        provider, llm_name = llm_helper.get_provider_model(
            llm_provider_to_use,
            use_ollama=RUN_IN_OFFLINE_MODE
        )

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
            llm = llm_helper.get_langchain_llm(
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
        print("entered")
        print(f"filepath={file_path}")
        st.download_button(
            'Download PPTX file ⬇️',
            data=download_file,
            file_name='Presentation.pptx',
            key=datetime.datetime.now()
        )
    
    print("download")


def main():
    """
    Trigger application run.
    """

    build_ui()


if __name__ == '__main__':
    main()