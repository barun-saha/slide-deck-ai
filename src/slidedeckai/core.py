"""
Core functionality of SlideDeck AI.
"""
import logging
import os
import pathlib
import tempfile
from typing import Union, Any

import json5
from dotenv import load_dotenv

from . import global_config as gcfg
from .global_config import GlobalConfig
from .helpers import file_manager as filem
from .helpers import llm_helper, pptx_helper, text_helper
from .helpers.chat_helper import ChatMessageHistory

load_dotenv()

RUN_IN_OFFLINE_MODE = os.getenv('RUN_IN_OFFLINE_MODE', 'False').lower() == 'true'
VALID_MODEL_NAMES = list(GlobalConfig.VALID_MODELS.keys())
VALID_TEMPLATE_NAMES = list(GlobalConfig.PPTX_TEMPLATE_FILES.keys())

logger = logging.getLogger(__name__)


def _process_llm_chunk(chunk: Any) -> str:
    """
    Helper function to process LLM response chunks consistently.

    Args:
        chunk: The chunk received from the LLM stream.

    Returns:
        The processed text from the chunk.
    """
    if isinstance(chunk, str):
        return chunk

    content = getattr(chunk, 'content', None)
    return content if content is not None else str(chunk)


def _stream_llm_response(llm: Any, prompt: str, progress_callback=None) -> str:
    """
    Helper function to stream LLM responses with consistent handling.

    Args:
        llm: The LLM instance to use for generating responses.
        prompt: The prompt to send to the LLM.
        progress_callback: A callback function to report progress.

    Returns:
        The complete response from the LLM.

    Raises:
        RuntimeError: If there's an error getting response from LLM.
    """
    response = ''
    try:
        for chunk in llm.stream(prompt):
            chunk_text = _process_llm_chunk(chunk)
            response += chunk_text
            if progress_callback:
                progress_callback(len(response))
        return response
    except Exception as e:
        logger.error('Error streaming LLM response: %s', str(e))
        raise RuntimeError(f'Failed to get response from LLM: {str(e)}') from e


class SlideDeckAI:
    """
    The main class for generating slide decks.
    """

    def __init__(
            self,
            model: str,
            topic: str,
            api_key: str = None,
            pdf_path_or_stream=None,
            pdf_page_range=None,
            template_idx: int = 0
    ):
        """
        Initialize the SlideDeckAI object.

        Args:
            model: The name of the LLM model to use.
            topic: The topic of the slide deck.
            api_key: The API key for the LLM provider.
            pdf_path_or_stream: The path to a PDF file or a file-like object.
            pdf_page_range: A tuple representing the page range to use from the PDF file.
            template_idx: The index of the PowerPoint template to use.

        Raises:
            ValueError: If the model name is not in VALID_MODELS.
        """
        if model not in GlobalConfig.VALID_MODELS:
            raise ValueError(
                f'Invalid model name: {model}.'
                f' Must be one of: {", ".join(VALID_MODEL_NAMES)}.'
            )

        self.model: str = model
        self.topic: str = topic
        self.api_key: str = api_key
        self.pdf_path_or_stream = pdf_path_or_stream
        self.pdf_page_range = pdf_page_range
        # Validate template_idx is within valid range
        num_templates = len(GlobalConfig.PPTX_TEMPLATE_FILES)
        self.template_idx: int = template_idx if 0 <= template_idx < num_templates else 0
        self.chat_history = ChatMessageHistory()
        self.last_response = None
        logger.info('Using model: %s', model)

    def _initialize_llm(self):
        """
        Initialize and return an LLM instance with the current configuration.

        Returns:
            Configured LLM instance.
        """
        provider, llm_name = llm_helper.get_provider_model(
            self.model,
            use_ollama=RUN_IN_OFFLINE_MODE
        )

        return llm_helper.get_litellm_llm(
            provider=provider,
            model=llm_name,
            max_new_tokens=gcfg.get_max_output_tokens(self.model),
            api_key=self.api_key,
        )

    def _get_prompt_template(self, is_refinement: bool) -> str:
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

    def generate(self, progress_callback=None):
        """
        Generate the initial slide deck.

        Args:
            progress_callback: Optional callback function to report progress.

        Returns:
            The path to the generated .pptx file.
        """
        additional_info = ''
        if self.pdf_path_or_stream:
            additional_info = filem.get_pdf_contents(self.pdf_path_or_stream, self.pdf_page_range)

        self.chat_history.add_user_message(self.topic)
        prompt_template = self._get_prompt_template(is_refinement=False)
        formatted_template = prompt_template.format(
            question=self.topic,
            additional_info=additional_info
        )

        llm = self._initialize_llm()
        response = _stream_llm_response(llm, formatted_template, progress_callback)

        self.last_response = text_helper.get_clean_json(response)
        self.chat_history.add_ai_message(self.last_response)

        return self._generate_slide_deck(self.last_response)

    def revise(self, instructions, progress_callback=None):
        """
        Revise the slide deck with new instructions.

        Args:
            instructions: The instructions for revising the slide deck.
            progress_callback: Optional callback function to report progress.

        Returns:
            The path to the revised .pptx file.

        Raises:
            ValueError: If no slide deck exists or chat history is full.
        """
        if not self.last_response:
            raise ValueError('You must generate a slide deck before you can revise it.')

        if len(self.chat_history.messages) >= 16:
            raise ValueError('Chat history is full. Please reset to continue.')

        self.chat_history.add_user_message(instructions)

        prompt_template = self._get_prompt_template(is_refinement=True)

        list_of_msgs = [
            f'{idx + 1}. {msg.content}'
            for idx, msg in enumerate(self.chat_history.messages) if msg.role == 'user'
        ]

        additional_info = ''
        if self.pdf_path_or_stream:
            additional_info = filem.get_pdf_contents(self.pdf_path_or_stream, self.pdf_page_range)

        formatted_template = prompt_template.format(
            instructions='\n'.join(list_of_msgs),
            previous_content=self.last_response,
            additional_info=additional_info,
        )

        llm = self._initialize_llm()
        response = _stream_llm_response(llm, formatted_template, progress_callback)

        self.last_response = text_helper.get_clean_json(response)
        self.chat_history.add_ai_message(self.last_response)

        return self._generate_slide_deck(self.last_response)

    def _generate_slide_deck(self, json_str: str) -> Union[pathlib.Path, None]:
        """
        Create a slide deck and return the file path.

        Args:
            json_str: The content in valid JSON format.

        Returns:
            The path to the .pptx file or None in case of error.
        """
        try:
            parsed_data = json5.loads(json_str)
        except (ValueError, RecursionError) as e:
            logger.error('Error parsing JSON: %s', e)
            try:
                parsed_data = json5.loads(text_helper.fix_malformed_json(json_str))
            except (ValueError, RecursionError) as e2:
                logger.error('Error parsing fixed JSON: %s', e2)
                return None

        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.pptx')
        path = pathlib.Path(temp.name)
        temp.close()

        try:
            pptx_helper.generate_powerpoint_presentation(
                parsed_data,
                slides_template=VALID_TEMPLATE_NAMES[self.template_idx],
                output_file_path=path
            )
        except Exception as ex:
            logger.error('Caught a generic exception: %s', str(ex))
            return None

        return path

    def set_model(self, model_name: str, api_key: str | None = None):
        """
        Set the LLM model (and API key) to use.

        Args:
            model_name: The name of the model to use.
            api_key: The API key for the LLM provider.

        Raises:
            ValueError: If the model name is not in VALID_MODELS.
        """
        if model_name not in GlobalConfig.VALID_MODELS:
            raise ValueError(
                f'Invalid model name: {model_name}.'
                f' Must be one of: {", ".join(VALID_MODEL_NAMES)}.'
            )
        self.model = model_name
        if api_key:
            self.api_key = api_key
        logger.debug('Model set to: %s', model_name)

    def set_template(self, idx):
        """
        Set the PowerPoint template to use.

        Args:
            idx: The index of the template to use.
        """
        num_templates = len(GlobalConfig.PPTX_TEMPLATE_FILES)
        self.template_idx = idx if 0 <= idx < num_templates else 0

    def reset(self):
        """
        Reset the chat history and internal state.
        """
        self.chat_history = ChatMessageHistory()
        self.last_response = None
        self.template_idx = 0
        self.topic = ''
