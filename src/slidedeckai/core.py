"""
Core classes for SlideDeckAI.
"""
import logging
import os
import pathlib
import tempfile
from typing import Union

import json5
from dotenv import load_dotenv

from . import global_config as gcfg
from .global_config import GlobalConfig
from .helpers import llm_helper, pptx_helper, text_helper
from .helpers.chat_helper import ChatMessageHistory

load_dotenv()

RUN_IN_OFFLINE_MODE = os.getenv('RUN_IN_OFFLINE_MODE', 'False').lower() == 'true'

logger = logging.getLogger(__name__)

class SlideDeckAI:
    """
    The main class for generating slide decks.
    """

    def __init__(self, model, topic, api_key=None, pdf_file_path=None, pdf_page_range=None, template_idx=0, additional_info=''):
        """
        Initializes the SlideDeckAI object.

        :param model: The name of the LLM model to use.
        :param topic: The topic of the slide deck.
        :param api_key: The API key for the LLM provider.
        :param pdf_file_path: The path to a PDF file to use as a source for the slide deck.
        :param pdf_page_range: A tuple representing the page range to use from the PDF file.
        :param template_idx: The index of the PowerPoint template to use.
        :param additional_info: Additional information to be sent to the LLM, such as text from a PDF.
        """
        self.model = model
        self.topic = topic
        self.api_key = api_key
        self.pdf_file_path = pdf_file_path
        self.pdf_page_range = pdf_page_range
        self.template_idx = template_idx
        self.additional_info = additional_info
        self.chat_history = ChatMessageHistory()
        self.last_response = None

    def _get_prompt_template(self, is_refinement: bool) -> str:
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

    def generate(self, progress_callback=None):
        """
        Generates the initial slide deck.
        :return: The path to the generated .pptx file.
        """
        self.chat_history.add_user_message(self.topic)
        prompt_template = self._get_prompt_template(is_refinement=False)
        formatted_template = prompt_template.format(question=self.topic, additional_info=self.additional_info)

        provider, llm_name = llm_helper.get_provider_model(self.model, use_ollama=RUN_IN_OFFLINE_MODE)

        llm = llm_helper.get_litellm_llm(
            provider=provider,
            model=llm_name,
            max_new_tokens=gcfg.get_max_output_tokens(self.model),
            api_key=self.api_key,
        )

        response = ""
        for chunk in llm.stream(formatted_template):
            if isinstance(chunk, str):
                response += chunk
            else:
                content = getattr(chunk, 'content', None)
                if content is not None:
                    response += content
                else:
                    response += str(chunk)
            if progress_callback:
                progress_callback(len(response))

        self.last_response = text_helper.get_clean_json(response)
        self.chat_history.add_ai_message(self.last_response)

        return self._generate_slide_deck(self.last_response)

    def revise(self, instructions, progress_callback=None):
        """
        Revises the slide deck with new instructions.

        :param instructions: The instructions for revising the slide deck.
        :return: The path to the revised .pptx file.
        """
        if not self.last_response:
            raise ValueError("You must generate a slide deck before you can revise it.")

        if len(self.chat_history.messages) >= 16:
            raise ValueError("Chat history is full. Please reset to continue.")

        self.chat_history.add_user_message(instructions)

        prompt_template = self._get_prompt_template(is_refinement=True)

        list_of_msgs = [f'{idx + 1}. {msg.content}' for idx, msg in enumerate(self.chat_history.messages) if msg.role == 'user']

        formatted_template = prompt_template.format(
            instructions='\n'.join(list_of_msgs),
            previous_content=self.last_response,
            additional_info=self.additional_info,
        )

        provider, llm_name = llm_helper.get_provider_model(self.model, use_ollama=RUN_IN_OFFLINE_MODE)

        llm = llm_helper.get_litellm_llm(
            provider=provider,
            model=llm_name,
            max_new_tokens=gcfg.get_max_output_tokens(self.model),
            api_key=self.api_key,
        )

        response = ""
        for chunk in llm.stream(formatted_template):
            if isinstance(chunk, str):
                response += chunk
            else:
                content = getattr(chunk, 'content', None)
                if content is not None:
                    response += content
                else:
                    response += str(chunk)
            if progress_callback:
                progress_callback(len(response))

        self.last_response = text_helper.get_clean_json(response)
        self.chat_history.add_ai_message(self.last_response)

        return self._generate_slide_deck(self.last_response)

    def _generate_slide_deck(self, json_str: str) -> Union[pathlib.Path, None]:
        """
        Create a slide deck and return the file path.

        :param json_str: The content in *valid* JSON format.
        :return: The path to the .pptx file or `None` in case of error.
        """
        try:
            parsed_data = json5.loads(json_str)
        except (ValueError, RecursionError) as e:
            logger.error("Error parsing JSON: %s", e)
            try:
                parsed_data = json5.loads(text_helper.fix_malformed_json(json_str))
            except (ValueError, RecursionError) as e2:
                logger.error("Error parsing fixed JSON: %s", e2)
                return None

        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.pptx')
        path = pathlib.Path(temp.name)
        temp.close()

        try:
            pptx_helper.generate_powerpoint_presentation(
                parsed_data,
                slides_template=list(GlobalConfig.PPTX_TEMPLATE_FILES.keys())[self.template_idx],
                output_file_path=path
            )
        except Exception as ex:
            logger.exception('Caught a generic exception: %s', str(ex))
            return None

        return path

    def set_template(self, idx):
        """
        Sets the PowerPoint template to use.

        :param idx: The index of the template to use.
        """
        self.template_idx = idx

    def reset(self):
        """
        Resets the chat history.
        """
        self.chat_history = ChatMessageHistory()
        self.last_response = None
