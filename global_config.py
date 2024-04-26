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
    LLM_MODEL_MAX_OUTPUT_LENGTH: int = 4096
    LLM_MODEL_MAX_INPUT_LENGTH: int = 750

    HUGGINGFACEHUB_API_TOKEN = os.environ.get('HUGGINGFACEHUB_API_TOKEN', '')
    METAPHOR_API_KEY = os.environ.get('METAPHOR_API_KEY', '')

    LOG_LEVEL = 'DEBUG'
    COUNT_TOKENS = False
    APP_STRINGS_FILE = 'strings.json'
    PRELOAD_DATA_FILE = 'examples/example_02.json'
    SLIDES_TEMPLATE_FILE = 'langchain_templates/template_combined.txt'
    # JSON_TEMPLATE_FILE = 'langchain_templates/text_to_json_template_02.txt'
    INITIAL_PROMPT_TEMPLATE = 'langchain_templates/chat_prompts/initial_template_v2_steps.txt'
    REFINEMENT_PROMPT_TEMPLATE = 'langchain_templates/chat_prompts/refinement_template_v2_steps.txt'

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

    # This is a long text, so not incorporated as a string in `strings.json`
    CHAT_USAGE_INSTRUCTIONS = (
        'Briefly describe your topic of presentation in the textbox provided below.'
        ' For example, "Make a slide deck on AI." Subsequently, you can add follow-up'
        ' instructions, e.g., "Can you add a slide on GPUs?" You can also ask it to refine any'
        ' particular slide, e.g., "Make the slide with title \'Examples of AI\' a bit more'
        ' descriptive." See this [demo video](https://youtu.be/QvAKzNKtk9k).'
        ' As another example, sometimes the formatting of generated Python code can be a bit weird.'
        ' You can try it telling, "Split multi-line codes into multiple lines," and hope for a fix.'
        '\n\n'
        'SlideDeck AI generates only text content. It does not have access to the Web.'
        '\n\n'
        'If you like SlideDeck AI, please consider leaving a heart ❤️ on the'
        ' [Hugging Face Space](https://huggingface.co/spaces/barunsaha/slide-deck-ai/) or'
        ' a star ⭐ on [GitHub](https://github.com/barun-saha/slide-deck-ai).'
    )


logging.basicConfig(
    level=GlobalConfig.LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
