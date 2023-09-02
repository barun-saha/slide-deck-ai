from dataclasses import dataclass
from dotenv import load_dotenv
import os


load_dotenv()


@dataclass(frozen=True)
class GlobalConfig:
    CLARIFAI_PAT = os.environ.get('CLARIFAI_PAT', '')
    CLARIFAI_USER_ID = 'meta'
    CLARIFAI_APP_ID = 'Llama-2'
    CLARIFAI_MODEL_ID = 'llama2-13b-chat'

    CLARIFAI_USER_ID_GPT = 'openai'
    CLARIFAI_APP_ID_GPT = 'chat-completion'
    CLARIFAI_MODEL_ID_GPT = 'GPT-3_5-turbo'

    CLARIFAI_USER_ID_SD = 'stability-ai'
    CLARIFAI_APP_ID_SD = 'stable-diffusion-2'
    CLARIFAI_MODEL_ID_SD = 'stable-diffusion-xl'
    CLARIFAI_MODEL_VERSION_ID_SD = '0c919cc1edfc455dbc96207753f178d7'

    # LLM_MODEL_TEMPERATURE: float = 0.5
    LLM_MODEL_MIN_OUTPUT_LENGTH: int = 50
    LLM_MODEL_MAX_OUTPUT_LENGTH: int = 2000
    LLM_MODEL_MAX_INPUT_LENGTH: int = 1000

    METAPHOR_API_KEY = os.environ.get('METAPHOR_API_KEY', '')

    LOG_LEVEL = 'INFO'
    APP_STRINGS_FILE = 'strings.json'
    PRELOAD_DATA_FILE = 'examples/example_02.json'
    SLIDES_TEMPLATE_FILE = 'langchain_templates/template_07.txt'
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

