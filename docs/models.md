# Models

This section provides an overview of the large language models (LLMs) supported by SlideDeck AI for generating slide decks. SlideDeck AI leverages various LLMs to create high-quality presentations based on user inputs.

## Naming Convention

SlideDeck AI uses LiteLLM. However, the models here follow a different naming syntax. For example, to use Google Gemini 2.0 Flash Lite in SlideDeck AI, the model name would be `[gg]gemini-2.0-flash-lite`. This is automatically taken care of in the SlideDeck AI app when users choose any model. However, when using Python API, this naming convention needs to be followed.

In particular, model names in SlideDeck AI are specified in the `[code]model-name` format.
- The first two-character prefix code in square brackets indicates the provider, for example, `[oa]` for OpenAI, `[gg]` for Google Gemini, and so on. 
- Following the code, the model name is specified, for example, `gemini-2.0-flash` or `gpt-4o`.

Note that not every LLM may be suitable for slide generation tasks. SlideDeck AI generally works best with the Gemini models. Some models can generate short contents. So, it is recommended to try out a few different models to see which one works best for your specific use case.


## Supported Models

SlideDeck AI supports the following online LLMs:

| LLM                                 | Provider (code)          | Requires API key                                                                                                         | Characteristics          |
|:------------------------------------|:-------------------------|:-------------------------------------------------------------------------------------------------------------------------|:-------------------------|
| Claude Haiku 4.5                    | Anthropic (`an`)         | Mandatory; [get here](https://platform.claude.com/settings/keys)                                                         | Faster, detailed         |
| Gemini 2.0 Flash                    | Google Gemini API (`gg`) | Mandatory; [get here](https://aistudio.google.com/apikey)                                                                | Faster, longer content   |
| Gemini 2.0 Flash Lite               | Google Gemini API (`gg`) | Mandatory; [get here](https://aistudio.google.com/apikey)                                                                | Fastest, longer content  |
| Gemini 2.5 Flash                    | Google Gemini API (`gg`) | Mandatory; [get here](https://aistudio.google.com/apikey)                                                                | Faster, longer content   |
| Gemini 2.5 Flash Lite               | Google Gemini API (`gg`) | Mandatory; [get here](https://aistudio.google.com/apikey)                                                                | Fastest, longer content  |
| GPT-4.1-mini                        | OpenAI (`oa`)            | Mandatory; [get here](https://platform.openai.com/settings/organization/api-keys)                                        | Faster, medium content   |
| GPT-4.1-nano                        | OpenAI (`oa`)            | Mandatory; [get here](https://platform.openai.com/settings/organization/api-keys)                                        | Faster, shorter content  |
| GPT-5                               | OpenAI (`oa`)            | Mandatory; [get here](https://platform.openai.com/settings/organization/api-keys)                                        | Slow, shorter content    |
| GPT                                 | Azure OpenAI (`az`)      | Mandatory; [get here](https://ai.azure.com/resource/playground)  NOTE: You need to have your subscription/billing set up | Faster, longer content   |
| Command R+                          | Cohere (`co`)            | Mandatory; [get here](https://dashboard.cohere.com/api-keys)                                                             | Shorter, simpler content |
| Gemini-2.0-flash-001                | OpenRouter (`or`)        | Mandatory; [get here](https://openrouter.ai/settings/keys)                                                               | Faster, longer content   |
| GPT-3.5 Turbo                       | OpenRouter (`or`)        | Mandatory; [get here](https://openrouter.ai/settings/keys)                                                               | Faster, longer content   |
| DeepSeek-V3.1-Terminus              | SambaNova (`sn`)         | Mandatory; [get here](https://cloud.sambanova.ai/apis)                                                                   | Fast, detailed content   |
| Llama-3.3-Swallow-70B-Instruct-v0.4 | SambaNova (`sn`)         | Mandatory; [get here](https://cloud.sambanova.ai/apis)                                                                   | Fast, shorter            |
| DeepSeek V3-0324                    | Together AI (`to`)       | Mandatory; [get here](https://api.together.ai/settings/api-keys)                                                         | Slower, medium-length    |
| Llama 3.3 70B Instruct Turbo        | Together AI (`to`)       | Mandatory; [get here](https://api.together.ai/settings/api-keys)                                                         | Slower, detailed         |
| Llama 3.1 8B Instruct Turbo 128K    | Together AI (`to`)       | Mandatory; [get here](https://api.together.ai/settings/api-keys)                                                         | Faster, shorter          |

