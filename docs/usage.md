# Usage

Using SlideDeck AI, you can create a PowerPoint presentation on any topic like this:

```python
from slidedeckai.core import SlideDeckAI


slide_generator = SlideDeckAI(
    model='[gg]gemini-2.5-flash-lite',
    topic='Make a slide deck on AI',
    api_key='your-google-api-key',  # Or set via environment variable
)
pptx_path = slide_generator.generate()
print(f'🤖 Generated slide deck: {pptx_path}')
```

To change the slide template, use the `template_idx` parameter with values between 0 and 3, both inclusive.

Check out the list of [supported LLMs and the two-character provider codes](https://github.com/barun-saha/slide-deck-ai/?tab=readme-ov-file#summary-of-the-llms).
SlideDeck AI uses LiteLLM. You can either provide your [API key](https://docs.litellm.ai/docs/set_keys) in the code as shown above or set as an environment variable.

You can also use SlideDeck AI from the command line interface like this:
```bash
slidedeckai generate --model '[gg]gemini-2.5-flash-lite' --topic 'Make a slide deck on AI' --api-key 'your-google-api-key'
```

List supported models (these are the only models supported by SlideDeck AI):
```bash
slidedeckai --list-models
```
