"""
A set of configurations used by the app.
"""
import logging
import os
import re
from pathlib import Path

from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()

_SRC_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class GlobalConfig:
    """
    A data class holding the configurations.
    """
    PROVIDER_ANTHROPIC = 'an'
    PROVIDER_AZURE_OPENAI = 'az'
    PROVIDER_COHERE = 'co'
    PROVIDER_GOOGLE_GEMINI = 'gg'
    PROVIDER_OLLAMA = 'ol'
    PROVIDER_OPENAI = 'oa'
    PROVIDER_OPENROUTER = 'or'
    PROVIDER_TOGETHER_AI = 'to'
    PROVIDER_SAMBANOVA = 'sn'

    LITELLM_PROVIDER_MAPPING = {
        PROVIDER_ANTHROPIC: 'anthropic',
        PROVIDER_GOOGLE_GEMINI: 'gemini',
        PROVIDER_AZURE_OPENAI: 'azure',
        PROVIDER_OPENROUTER: 'openrouter',
        PROVIDER_COHERE: 'cohere',
        PROVIDER_SAMBANOVA: 'sambanova',
        PROVIDER_TOGETHER_AI: 'together_ai',
        PROVIDER_OLLAMA: 'ollama',
        PROVIDER_OPENAI: 'openai',
    }

    VALID_PROVIDERS = {
        PROVIDER_ANTHROPIC,
        PROVIDER_AZURE_OPENAI,
        PROVIDER_COHERE,
        PROVIDER_GOOGLE_GEMINI,
        PROVIDER_OLLAMA,
        PROVIDER_OPENAI,
        PROVIDER_OPENROUTER,
        PROVIDER_SAMBANOVA,
        PROVIDER_TOGETHER_AI,
    }
    PROVIDER_ENV_KEYS = {
        PROVIDER_ANTHROPIC: 'ANTHROPIC_API_KEY',
        PROVIDER_COHERE: 'COHERE_API_KEY',
        PROVIDER_GOOGLE_GEMINI: 'GOOGLE_API_KEY',
        PROVIDER_AZURE_OPENAI: 'AZURE_OPENAI_API_KEY',
        PROVIDER_OPENAI: 'OPENAI_API_KEY',
        PROVIDER_OPENROUTER: 'OPENROUTER_API_KEY',
        PROVIDER_SAMBANOVA: 'SAMBANOVA_API_KEY',
        PROVIDER_TOGETHER_AI: 'TOGETHER_API_KEY',
    }
    PROVIDER_REGEX = re.compile(r'\[(.*?)\]')
    VALID_MODELS = {
        '[an]claude-haiku-4-5': {
            'description': 'faster, detailed',
            'max_new_tokens': 8192,
            'paid': True,
        },
        '[az]azure/open-ai': {
            'description': 'faster, detailed',
            'max_new_tokens': 8192,
            'paid': True,
        },
        '[co]command-r-08-2024': {
            'description': 'simpler, slower',
            'max_new_tokens': 4096,
            'paid': True,
        },
        '[gg]gemini-2.0-flash': {
            'description': 'fast, detailed',
            'max_new_tokens': 8192,
            'paid': True,
        },
        '[gg]gemini-2.0-flash-lite': {
            'description': 'fastest, detailed',
            'max_new_tokens': 8192,
            'paid': True,
        },
        '[gg]gemini-2.5-flash': {
            'description': 'fast, detailed',
            'max_new_tokens': 8192,
            'paid': True,
        },
        '[gg]gemini-2.5-flash-lite': {
            'description': 'fastest, detailed',
            'max_new_tokens': 8192,
            'paid': True,
        },
        '[oa]gpt-4.1-mini': {
            'description': 'faster, medium',
            'max_new_tokens': 8192,
            'paid': True,
        },
        '[oa]gpt-4.1-nano': {
            'description': 'faster, shorter',
            'max_new_tokens': 8192,
            'paid': True,
        },
        '[oa]gpt-5-nano': {
            'description': 'slow, shorter',
            'max_new_tokens': 8192,
            'paid': True,
        },
        '[or]google/gemini-2.0-flash-001': {
            'description': 'Google Gemini-2.0-flash-001 (via OpenRouter)',
            'max_new_tokens': 8192,
            'paid': True,
        },
        '[or]openai/gpt-3.5-turbo': {
            'description': 'OpenAI GPT-3.5 Turbo (via OpenRouter)',
            'max_new_tokens': 4096,
            'paid': True,
        },
        '[sn]DeepSeek-V3.1-Terminus': {
            'description': 'fast, detailed',
            'max_new_tokens': 8192,
            'paid': True,
        },
        '[sn]Llama-3.3-Swallow-70B-Instruct-v0.4': {
            'description': 'fast, shorter',
            'max_new_tokens': 8192,
            'paid': True,
        },
        '[to]deepseek-ai/DeepSeek-V3': {
            'description': 'slower, medium',
            'max_new_tokens': 8192,
            'paid': True,
        },
        '[to]meta-llama/Llama-3.3-70B-Instruct-Turbo': {
            'description': 'slower, detailed',
            'max_new_tokens': 4096,
            'paid': True,
        },
        '[to]meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo-128K': {
            'description': 'faster, shorter',
            'max_new_tokens': 4096,
            'paid': True,
        }
    }
    LLM_PROVIDER_HELP = (
        'LLM provider codes:\n\n'
        '- **[an]**: Anthropic\n'
        '- **[az]**: Azure OpenAI\n'
        '- **[co]**: Cohere\n'
        '- **[gg]**: Google Gemini API\n'
        '- **[oa]**: OpenAI\n'
        '- **[or]**: OpenRouter\n\n'
        '- **[sn]**: SambaNova\n'
        '- **[to]**: Together AI\n\n'
        '[Find out more](https://github.com/barun-saha/slide-deck-ai?tab=readme-ov-file#summary-of-the-llms)'
    )
    DEFAULT_MODEL_INDEX = int(os.environ.get('DEFAULT_MODEL_INDEX', '4'))
    LLM_MODEL_TEMPERATURE = 0.2
    MAX_PAGE_COUNT = 50
    MAX_ALLOWED_PAGES = 150
    LLM_MODEL_MAX_INPUT_LENGTH = 1000  # characters

    LOG_LEVEL = 'DEBUG'
    COUNT_TOKENS = False
    APP_STRINGS_FILE = _SRC_DIR / 'strings.json'
    PRELOAD_DATA_FILE = _SRC_DIR / 'examples/example_02.json'
    INITIAL_PROMPT_TEMPLATE = _SRC_DIR / 'prompts/initial_template_v4_two_cols_img.txt'
    REFINEMENT_PROMPT_TEMPLATE = _SRC_DIR / 'prompts/refinement_template_v4_two_cols_img.txt'

    LLM_PROGRESS_MAX = 90
    ICONS_DIR = _SRC_DIR / 'icons/png128/'
    TINY_BERT_MODEL = 'gaunernst/bert-mini-uncased'
    EMBEDDINGS_FILE_NAME = _SRC_DIR / 'file_embeddings/embeddings.npy'
    ICONS_FILE_NAME = _SRC_DIR / 'file_embeddings/icons.npy'

    PPTX_TEMPLATE_FILES = {
        'Basic': {
            'file': _SRC_DIR / 'pptx_templates/Blank.pptx',
            'caption': 'A good start (Uses [photos](https://unsplash.com/photos/AFZ-qBPEceA) by [cetteup](https://unsplash.com/@cetteup?utm_content=creditCopyText&utm_medium=referral&utm_source=unsplash) on [Unsplash](https://unsplash.com/photos/a-foggy-forest-filled-with-lots-of-trees-d3ci37Gcgxg?utm_content=creditCopyText&utm_medium=referral&utm_source=unsplash)) 🟧'
        },
        'Ion Boardroom': {
            'file': _SRC_DIR / 'pptx_templates/Ion_Boardroom.pptx',
            'caption': 'Make some bold decisions 🟥'
        },
        'Minimalist Sales Pitch': {
            'file': _SRC_DIR / 'pptx_templates/Minimalist_sales_pitch.pptx',
            'caption': 'In high contrast ⬛'
        },
        'Urban Monochrome': {
            'file': _SRC_DIR / 'pptx_templates/Urban_monochrome.pptx',
            'caption': 'Marvel in a monochrome dream ⬜'
        },
    }

    # This is a long text, so not incorporated as a string in `strings.json`
    CHAT_USAGE_INSTRUCTIONS = (
        'Briefly describe your topic of presentation in the textbox provided below. For example:\n'
        '- Make a slide deck on AI.'
        '\n\n'
        'Subsequently, you can add follow-up instructions, e.g.:\n'
        '- Can you add a slide on GPUs?'
        '\n\n'
        ' You can also ask it to refine any particular slide, e.g.:\n'
        '- Make the slide with title \'Examples of AI\' a bit more descriptive.'
        '\n\n'
        'Finally, click on the download button at the bottom to download the slide deck.'
        ' See this [demo video](https://youtu.be/QvAKzNKtk9k) for a brief walkthrough.\n\n'
        'Remember, the conversational interface is meant to (and will) update yor *initial*/'
        '*previous* slide deck. If you want to create a new slide deck on a different topic,'
        ' start a new chat session by reloading this page.'
        '\n\nSlideDeck AI can algo generate a presentation based on a PDF file. You can upload'
        ' a PDF file using the chat widget. Only a single file and up to max 50 pages will be'
        ' considered. For PDF-based slide deck generation, LLMs with large context windows, such'
        ' as Gemini and GPT, are recommended. Note: images from the PDF files will'
        ' not be used.'
        '\n\nAlso, note that the uploaded file might disappear from the page after click.'
        ' You do not need to upload the same file again to continue'
        ' the interaction and refining—the contents of the PDF file will be retained in the'
        ' same interactive session.'
        '\n\nCurrently, paid or *free-to-use* LLMs from several providers are supported.'
        ' A [summary of the supported LLMs]('
        'https://github.com/barun-saha/slide-deck-ai?tab=readme-ov-file#unmatched-flexibility-choose-your-ai-brain)'
        ' is available for reference. SlideDeck AI does **NOT** store your API keys.'
        '\n\nSlideDeck AI does not have access to the Web, apart for searching for images relevant'
        ' to the slides. Photos are added probabilistically; transparency needs to be changed'
        ' manually, if required.\n\n'
        '[SlideDeck AI](https://github.com/barun-saha/slide-deck-ai) is an Open-Source project,'
        ' released under the'
        ' [MIT license](https://github.com/barun-saha/slide-deck-ai?tab=MIT-1-ov-file#readme).'
        '\n\n---\n\n'
        '© Copyright 2023-2025 Barun Saha.\n\n'
    )


# Centralized logging configuration (early):
# - Ensure noisy third-party loggers (httpx, httpcore, urllib3, LiteLLM, etc.) are set to WARNING
# - Disable propagation so they don't bubble up to the root logger
# - Capture warnings from the warnings module into logging
# The log suppression must run before the noisy library is imported/initialised!
LOGGERS_TO_SUPPRESS = [
    'asyncio',
    'httpx',
    'httpcore',
    'langfuse',
    'LiteLLM',
    'litellm',
    'openai',
    'urllib3',
    'urllib3.connectionpool',
]

logging.basicConfig(
    level=GlobalConfig.LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

for _lg in LOGGERS_TO_SUPPRESS:
    logger_obj = logging.getLogger(_lg)
    logger_obj.setLevel(logging.WARNING)
    # Prevent these logs from propagating to the root logger
    logger_obj.propagate = False

# Capture warnings from the warnings module (optional, helps centralize output)
if hasattr(logging, 'captureWarnings'):
    logging.captureWarnings(True)


def get_max_output_tokens(llm_name: str) -> int:
    """
    Get the max output tokens value configured for an LLM. Return a default value if not configured.

    :param llm_name: The name of the LLM.
    :return: Max output tokens or a default count.
    """

    try:
        return GlobalConfig.VALID_MODELS[llm_name]['max_new_tokens']
    except KeyError:
        return 2048
