"""
Command-line interface for SlideDeck AI.
"""
import argparse
import sys
import shutil

from slidedeckai.core import SlideDeckAI
from slidedeckai.global_config import GlobalConfig


def main():
    """
    The main function for the CLI.
    """
    parser = argparse.ArgumentParser(description='Generate slide decks with SlideDeck AI.')
    subparsers = parser.add_subparsers(dest='command')

    # Top-level flag to list supported models
    parser.add_argument(
        '-l',
        '--list-models',
        action='store_true',
        help='List supported model keys and exit.',
    )

    # 'generate' command
    parser_generate = subparsers.add_parser('generate', help='Generate a new slide deck.')
    parser_generate.add_argument(
        '--model',
        required=True,
        help=(
            'Model name to use. The model must be one of the supported models;'
            ' see `--list-models` for details.'
            ' Model name must be in the `[provider-code]model_name` format.'
        ),
    )
    parser_generate.add_argument(
        '--topic',
        required=True,
        help='The topic of the slide deck.',
    )
    parser_generate.add_argument(
        '--api-key',
        help=(
            'The API key for the LLM provider. Alternatively, set the appropriate API key'
            ' in the environment variable.'
        ),
    )
    parser_generate.add_argument(
        '--template-id',
        type=int,
        default=0,
        help='The index of the PowerPoint template to use.',
    )
    parser_generate.add_argument(
        '--output-path',
        help='The path to save the generated .pptx file.',
    )

    # Note: the 'launch' command has been intentionally disabled.

    # If no arguments are provided, show help and exit
    if len(sys.argv) == 1:
        parser.print_help()
        return

    args = parser.parse_args()

    # If --list-models flag was provided, print models and exit
    if getattr(args, 'list_models', False):
        print('Supported SlideDeck AI models (these are the only supported models):')
        for k in GlobalConfig.VALID_MODELS:
            print(k)
        return

    if args.command == 'generate':
        slide_generator = SlideDeckAI(
            model=args.model,
            topic=args.topic,
            api_key=args.api_key,
            template_idx=args.template_id,
        )

        pptx_path = slide_generator.generate()

        if args.output_path:
            shutil.move(str(pptx_path), args.output_path)
            print(f'\n🤖 Slide deck saved to: {args.output_path}')
        else:
            print(f'\n🤖 Slide deck saved to: {pptx_path}')


if __name__ == '__main__':
    main()
