"""
Command-line interface for SlideDeckAI.
"""
import argparse
from .core import SlideDeckAI

def main():
    """
    The main function for the CLI.
    """
    parser = argparse.ArgumentParser(description='Generate slide decks with SlideDeckAI.')
    parser.add_argument('--model', required=True, help='The name of the LLM model to use.')
    parser.add_argument('--topic', required=True, help='The topic of the slide deck.')
    parser.add_argument('--api-key', help='The API key for the LLM provider.')
    parser.add_argument('--template-id', type=int, default=0, help='The index of the PowerPoint template to use.')
    parser.add_argument('--output-path', help='The path to save the generated .pptx file.')
    args = parser.parse_args()

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

if __name__ == '__main__':
    main()
