"""
A set of configurations used by the app.
"""
import logging
import os

from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class GlobalConfig:
    """
    A data class holding the configurations.
    """

    PROVIDER_COHERE = 'co'
    PROVIDER_GOOGLE_GEMINI = 'gg'
    PROVIDER_HUGGING_FACE = 'hf'
    PROVIDER_OLLAMA = 'ol'
    PROVIDER_TOGETHER_AI = 'to'
    PROVIDER_AZURE_OPENAI = 'az'
    PROVIDER_OPENROUTER = 'or'
    VALID_PROVIDERS = {
        PROVIDER_COHERE,
        PROVIDER_GOOGLE_GEMINI,
        PROVIDER_HUGGING_FACE,
        PROVIDER_OLLAMA,
        PROVIDER_TOGETHER_AI,
        PROVIDER_AZURE_OPENAI,
        PROVIDER_OPENROUTER,
    }
    VALID_MODELS = {
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
        '[hf]mistralai/Mistral-7B-Instruct-v0.2': {
            'description': 'faster, shorter',
            'max_new_tokens': 8192,
            'paid': False,
        },
        '[hf]mistralai/Mistral-Nemo-Instruct-2407': {
            'description': 'longer response',
            'max_new_tokens': 8192,
            'paid': False,
        },
        '[to]meta-llama/Llama-3.3-70B-Instruct-Turbo': {
            'description': 'detailed, slower',
            'max_new_tokens': 4096,
            'paid': True,
        },
        '[to]meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo-128K': {
            'description': 'shorter, faster',
            'max_new_tokens': 4096,
            'paid': True,
        },
        '[or]openai/gpt-3.5-turbo': {
            'description': 'OpenAI GPT-3.5 Turbo (via OpenRouter)',
            'max_new_tokens': 2048,
        },
        '[or]openrouter/gpt-4-omni': {
            'description': 'OpenRouter GPT-4 Omni',
            'max_new_tokens': 8192,
            'paid': True,
        }
    }
    LLM_PROVIDER_HELP = (
        'LLM provider codes:\n\n'
        '- **[az]**: Azure OpenAI\n'
        '- **[co]**: Cohere\n'
        '- **[gg]**: Google Gemini API\n'
        '- **[hf]**: Hugging Face Inference API\n'
        '- **[to]**: Together AI\n'
        '- **[or]**: OpenRouter\n\n'
        '[Find out more](https://github.com/barun-saha/slide-deck-ai?tab=readme-ov-file#summary-of-the-llms)'
    )
    DEFAULT_MODEL_INDEX = int(os.environ.get('DEFAULT_MODEL_INDEX', '4'))
    LLM_MODEL_TEMPERATURE = 0.2
    MAX_PAGE_COUNT = 50

    LOG_LEVEL = 'DEBUG'
    COUNT_TOKENS = False
    APP_STRINGS_FILE = 'strings.json'
    PRELOAD_DATA_FILE = 'examples/example_02.json'
    INITIAL_PROMPT_TEMPLATE = 'prompts/initial_template_v4_two_cols_img.txt'
    REFINEMENT_PROMPT_TEMPLATE = 'prompts/refinement_template_v4_two_cols_img.txt'

    LLM_PROGRESS_MAX = 90
    ICONS_DIR = 'icons/png128/'
    TINY_BERT_MODEL = 'gaunernst/bert-mini-uncased'
    EMBEDDINGS_FILE_NAME = 'file_embeddings/embeddings.npy'
    ICONS_FILE_NAME = 'file_embeddings/icons.npy'

    PPTX_TEMPLATE_FILES = {
        'Basic': {
            'file': 'pptx_templates/Blank.pptx',
            'caption': 'A good start (Uses [photos](https://unsplash.com/photos/AFZ-qBPEceA) by [cetteup](https://unsplash.com/@cetteup?utm_content=creditCopyText&utm_medium=referral&utm_source=unsplash) on [Unsplash](https://unsplash.com/photos/a-foggy-forest-filled-with-lots-of-trees-d3ci37Gcgxg?utm_content=creditCopyText&utm_medium=referral&utm_source=unsplash)) 🟧'
        },
        'Ion Boardroom': {
            'file': 'pptx_templates/Ion_Boardroom.pptx',
            'caption': 'Make some bold decisions 🟥'
        },
        'Minimalist Sales Pitch': {
            'file': 'pptx_templates/Minimalist_sales_pitch.pptx',
            'caption': 'In high contrast ⬛'
        },
        'Urban Monochrome': {
            'file': 'pptx_templates/Urban_monochrome.pptx',
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
        ' as Gemini, GPT, and Mistral-Nemo, are recommended. Note: images from the PDF files will'
        ' not be used.'
        '\n\nAlso, note that the uploaded file might disappear from the page after click.'
        ' You do not need to upload the same file again to continue'
        ' the interaction and refining—the contents of the PDF file will be retained in the'
        ' same interactive session.'
        '\n\nCurrently, paid or *free-to-use* LLMs from five different providers are supported.'
        ' A [summary of the supported LLMs]('
        'https://github.com/barun-saha/slide-deck-ai/blob/main/README.md#summary-of-the-llms)'
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


logging.basicConfig(
    level=GlobalConfig.LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


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
