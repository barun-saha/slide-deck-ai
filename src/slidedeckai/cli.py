"""
Command-line interface for SlideDeck AI.
"""
import argparse
import sys
import shutil
from typing import Any

from slidedeckai.core import SlideDeckAI
from slidedeckai.global_config import GlobalConfig


class CustomHelpFormatter(argparse.HelpFormatter):
    """
    Custom formatter for argparse that improves the display of choices.
    """
    def _format_action_invocation(self, action: Any) -> str:
        if not action.option_strings or action.nargs == 0:
            return super()._format_action_invocation(action)

        default = self._get_default_metavar_for_optional(action)
        args_string = self._format_args(action, default)

        # If there are choices, and it's the model argument, handle it specially
        if action.choices and '--model' in action.option_strings:
            return ', '.join(action.option_strings) + ' MODEL'

        return f"{', '.join(action.option_strings)} {args_string}"

    def _split_lines(self, text: str, width: int) -> list[str]:
        if text.startswith('Model choices:') or text.startswith('choose from'):
            # Special handling for model choices and error messages
            lines = []
            header = 'Available models:'
            lines.append(header)
            lines.append('-' * len(header))

            # Extract models from text
            if text.startswith('choose from'):
                models = [
                    m.strip("' ") for m in text.replace('choose from', '').split(',')
                ]
            else:
                models = text.split('\n')[1:]

            # Group models by provider
            provider_models = {}
            for model in sorted(models):
                if not model.strip():
                    continue
                if match := GlobalConfig.PROVIDER_REGEX.match(model):
                    provider = match.group(1)
                    if provider not in provider_models:
                        provider_models[provider] = []
                    provider_models[provider].append(model.strip())

            # Add models grouped by provider
            for provider in sorted(provider_models.keys()):
                lines.append(f'\n{provider}:')
                for model in provider_models[provider]:
                    lines.append(f'  {model}')

            return lines

        return super()._split_lines(text, width)


class CustomArgumentParser(argparse.ArgumentParser):
    """
    Custom argument parser that formats error messages better.
    """
    def error(self, message: str) -> None:
        """Custom error handler that formats model choices better"""
        if 'invalid choice' in message and '--model' in message:
            # Extract models from the error message
            choices_str = message[message.find('(choose from'):]
            models = [m.strip("' ") for m in choices_str.replace('(choose from', '').rstrip(')').split(',')]

            # Group models by provider
            provider_models = {}
            for model in sorted(models):
                if match := GlobalConfig.PROVIDER_REGEX.match(model):
                    provider = match.group(1)
                    if provider not in provider_models:
                        provider_models[provider] = []
                    provider_models[provider].append(model.strip())

            # Format the error message with grouped models
            error_lines = ['Error: Invalid model choice. Available models:']
            for provider in sorted(provider_models.keys()):
                error_lines.append(f'\n{provider}:')
                for model in sorted(provider_models[provider]):
                    error_lines.append(f'  • {model}')

            self.print_help()
            print('\n' + '\n'.join(error_lines), file=sys.stderr)
            sys.exit(2)

        super().error(message)


def format_models_list() -> str:
    """Format the models list in a nice grouped format with descriptions."""
    lines = ['Supported SlideDeck AI models:', '']

    # Group models by provider
    provider_models = {}
    for model, info in sorted(GlobalConfig.VALID_MODELS.items()):
        if match := GlobalConfig.PROVIDER_REGEX.match(model):
            provider = match.group(1)
            if provider not in provider_models:
                provider_models[provider] = []
            provider_models[provider].append((model, info))

    # Add models grouped by provider
    for provider in sorted(provider_models.keys()):
        lines.append(f'{provider}:')
        # Find the longest model name for alignment
        max_model_len = max(len(model) for model, _ in provider_models[provider])
        max_desc_len = max(len(info['description']) for _, info in provider_models[provider])

        # Format as a table with aligned columns
        format_str = f'  {{:<{max_model_len}}}  |  {{:<{max_desc_len}}}  |  {{:>4}}'
        lines.append('  ' + '-' * (max_model_len + max_desc_len + 13))

        for model, info in sorted(provider_models[provider]):
            paid_status = 'Paid' if info.get('paid', False) else 'Free'
            lines.append(format_str.format(
                model,
                info['description'],
                paid_status
            ))
        lines.append('')  # Add spacing between provider sections

    return '\n'.join(lines)


def format_model_help() -> str:
    """Format model choices as a grouped bulleted list for help text."""
    lines = []

    # Group models by provider
    provider_models = {}
    for model in sorted(GlobalConfig.VALID_MODELS.keys()):
        if match := GlobalConfig.PROVIDER_REGEX.match(model):
            provider = match.group(1)
            if provider not in provider_models:
                provider_models[provider] = []
            provider_models[provider].append(model)

    # Add models grouped by provider
    for provider in sorted(provider_models.keys()):
        lines.append(f'\n{provider}:')
        for model in sorted(provider_models[provider]):
            lines.append(f'  • {model}')

    return '\n'.join(lines)


def main():
    """
    The main function for the CLI.
    """
    parser = CustomArgumentParser(
        description='Generate slide decks with SlideDeck AI.',
        formatter_class=CustomHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command')

    # Top-level flag to list supported models
    parser.add_argument(
        '-l',
        '--list-models',
        action='store_true',
        help='List supported model keys and exit.',
    )

    # 'generate' command
    parser_generate = subparsers.add_parser(
        'generate',
        help='Generate a new slide deck.',
        formatter_class=CustomHelpFormatter
    )

    parser_generate.add_argument(
        '--model',
        required=True,
        choices=GlobalConfig.VALID_MODELS.keys(),
        help=(
            'Model name to use. Must be one of the supported models in the'
            ' `[provider-code]model_name` format.' + format_model_help()
        ),
        metavar='MODEL'
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
        print(format_models_list())
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
