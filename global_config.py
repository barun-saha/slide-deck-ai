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

    HF_MODELS = {
        'mistralai/Mistral-7B-Instruct-v0.2': {
            'description': 'faster, shorter',
            'max_new_tokens': 8192
        },
        'mistralai/Mistral-Nemo-Instruct-2407': {
            'description': 'longer response',
            'max_new_tokens': 12228
        },
    }
    LLM_MODEL_TEMPERATURE = 0.2
    LLM_MODEL_MIN_OUTPUT_LENGTH = 100
    LLM_MODEL_MAX_INPUT_LENGTH = 400  # characters

    HUGGINGFACEHUB_API_TOKEN = os.environ.get('HUGGINGFACEHUB_API_TOKEN', '')

    LOG_LEVEL = 'DEBUG'
    COUNT_TOKENS = False
    APP_STRINGS_FILE = 'strings.json'
    PRELOAD_DATA_FILE = 'examples/example_02.json'
    SLIDES_TEMPLATE_FILE = 'langchain_templates/template_combined.txt'
    INITIAL_PROMPT_TEMPLATE = 'langchain_templates/chat_prompts/initial_template_v4_two_cols_img.txt'
    REFINEMENT_PROMPT_TEMPLATE = 'langchain_templates/chat_prompts/refinement_template_v4_two_cols_img.txt'

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
        'Minimalist Sales Pitch': {
            'file': 'pptx_templates/Minimalist_sales_pitch.pptx',
            'caption': 'In high contrast ⬛'
        },
        'Ion Boardroom': {
            'file': 'pptx_templates/Ion_Boardroom.pptx',
            'caption': 'Make some bold decisions 🟥'
        },
        'Urban Monochrome': {
            'file': 'pptx_templates/Urban_monochrome.pptx',
            'caption': 'Marvel in a monochrome dream ⬜'
        },
    }

    # This is a long text, so not incorporated as a string in `strings.json`
    CHAT_USAGE_INSTRUCTIONS = (
        'Briefly describe your topic of presentation in the textbox provided below.'
        ' For example:\n'
        '- Make a slide deck on AI.'
        '\n\n'
        'Subsequently, you can add follow-up instructions, e.g.:\n'
        '- Can you add a slide on GPUs?'
        '\n\n'
        ' You can also ask it to refine any particular slide, e.g.:\n'
        '- Make the slide with title \'Examples of AI\' a bit more descriptive.'
        '\n\n'
        'Finally, click on the download button to download the slide deck.'
        ' See this [demo video](https://youtu.be/QvAKzNKtk9k) for a brief walkthrough.\n\n'
        'Currently, two LLMs are supported. **Mistral 7B Instruct v0.2** is fast and generates'
        ' shorter outputs. On the other hand, **Mistral Nemo Instruct 2407** usually generates'
        ' longer outputs but can also be slower. If one is not available, choose the other from'
        ' the dropdown list.\n\n'
        ' SlideDeck AI does not have access to the Web, apart for searching for images relevant'
        ' to the slides. Photos are added probabilistically; transparency needs to be changed'
        ' manually, if required.\n\n'
        '[SlideDeck AI](https://github.com/barun-saha/slide-deck-ai) is an Open-Source project,'
        ' released under the'
        ' [MIT license](https://github.com/barun-saha/slide-deck-ai?tab=MIT-1-ov-file#readme).'
        ' It is is powered by'
        ' [Mistral-Nemo-Instruct-2407](https://huggingface.co/mistralai/Mistral-Nemo-Instruct-2407)'
        ' and [Mistral 7B v0.2](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2).\n\n'
        '---\n\n'
        '© Copyright 2023-2024 Barun Saha.\n\n'
    )


logging.basicConfig(
    level=GlobalConfig.LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
