import logging
import os

from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class GlobalConfig:
    HF_LLM_MODEL_NAME = 'mistralai/Mistral-7B-Instruct-v0.2'
    LLM_MODEL_TEMPERATURE: float = 0.2
    LLM_MODEL_MIN_OUTPUT_LENGTH: int = 50
    LLM_MODEL_MAX_OUTPUT_LENGTH: int = 2000
    LLM_MODEL_MAX_INPUT_LENGTH: int = 100

    HUGGINGFACEHUB_API_TOKEN = os.environ.get('HUGGINGFACEHUB_API_TOKEN', '')
    METAPHOR_API_KEY = os.environ.get('METAPHOR_API_KEY', '')

    LOG_LEVEL = 'DEBUG'
    APP_STRINGS_FILE = 'strings.json'
    PRELOAD_DATA_FILE = 'examples/example_02.json'
    SLIDES_TEMPLATE_FILE = 'langchain_templates/template_combined.txt'
    JSON_TEMPLATE_FILE = 'langchain_templates/text_to_json_template_02.txt'

    PPTX_TEMPLATE_FILES = {
        'Blank': {
            'file': 'pptx_templates/Blank.pptx',
            'caption': 'A good start'
        },
        'Ion Boardroom': {
            'file': 'pptx_templates/Ion_Boardroom.pptx',
            'caption': 'Make some bold decisions'
        },
        'Urban Monochrome': {
            'file': 'pptx_templates/Urban_monochrome.pptx',
            'caption': 'Marvel in a monochrome dream'
        }
    }

    CHAT_USAGE_INSTRUCTIONS = (
        'Briefly describe your topic of presentation in the textbox provided below.'
        ' Subsequently, you can add follow-up instructions, e.g., "Can you add a slide on GPUs?"'
        ' You can also ask AI to refine any particular slide, e.g., "Make the slide with title'
        ' \'Examples of AI\' a bit more descriptive."'
        '\n\n'
        'SlideDeck AI generates only text content. It does not have access to the Internet.'
    )


logging.basicConfig(
    level=GlobalConfig.LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
