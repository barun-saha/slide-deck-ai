"""
Command-line interface for SlideDeckAI.
"""
import argparse
import subprocess
import sys
from .core import SlideDeckAI

def main():
    """
    The main function for the CLI.
    """
    parser = argparse.ArgumentParser(description='Generate slide decks with SlideDeckAI.')
    subparsers = parser.add_subparsers(dest='command')

    # 'generate' command
    parser_generate = subparsers.add_parser('generate', help='Generate a new slide deck.')
    parser_generate.add_argument('--model', required=True, help='The name of the LLM model to use.')
    parser_generate.add_argument('--topic', required=True, help='The topic of the slide deck.')
    parser_generate.add_argument('--api-key', help='The API key for the LLM provider.')
    parser_generate.add_argument('--template-id', type=int, default=0, help='The index of the PowerPoint template to use.')
    parser_generate.add_argument('--output-path', help='The path to save the generated .pptx file.')

    # 'launch' command
    subparsers.add_parser('launch', help='Launch the Streamlit app.')

    args = parser.parse_args()

    if args.command == 'generate':
        slide_generator = SlideDeckAI(
            model=args.model,
            topic=args.topic,
            api_key=args.api_key,
            template_idx=args.template_id,
        )

        pptx_path = slide_generator.generate()

        if args.output_path:
            import shutil
            shutil.move(str(pptx_path), args.output_path)
            print(f"Slide deck saved to {args.output_path}")
        else:
            print(f"Slide deck saved to {pptx_path}")
    elif args.command == 'launch':
        # Get the path to the app.py file
        import os
        import slidedeckai
        app_path = os.path.join(os.path.dirname(slidedeckai.__file__), '..', '..', 'app.py')
        subprocess.run([sys.executable, '-m', 'streamlit', 'run', app_path])

if __name__ == '__main__':
    main()
