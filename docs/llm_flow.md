# LLM Configuration and Propagation Flow

In this section, we will go through the flow of LLM configurations selected in the SlideDeck AI Streamlit UI and propagated down to the core engine and LiteLLM wrapper to make API calls.

## Overview Flow

Here is the step-by-step pipeline:

```text
+-------------------------------------------------------------+
|                app.py (Streamlit Sidebar UI)                |
+-------------------------------------------------------------+
                               |
                               | (1) Initializes SlideDeckAI / set_model()
                               v
+-------------------------------------------------------------+
|             src/slidedeckai/core.py (SlideDeckAI)           |
+-------------------------------------------------------------+
                               |
                               | (2) Triggers generate/revise -> _initialize_llm()
                               v
+-------------------------------------------------------------+
|             src/slidedeckai/core.py: _initialize_llm()      |
+-------------------------------------------------------------+
                               |
                               | (3) Calls get_litellm_llm()
                               v
+-------------------------------------------------------------+
|   src/slidedeckai/helpers/llm_helper.py: get_litellm_llm()  |
+-------------------------------------------------------------+
                               |
                               | (4) Instantiates
                               v
+-------------------------------------------------------------+
|         src/slidedeckai/helpers/llm_helper.py:              |
|                     LiteLLMWrapper                          |
+-------------------------------------------------------------+
                               |
                               | (5) wrapper.stream() -> stream_litellm_completion()
                               v
+-------------------------------------------------------------+
|         src/slidedeckai/helpers/llm_helper.py:              |
|                stream_litellm_completion()                  |
+-------------------------------------------------------------+
                               |
                               | (6) Calls litellm.completion()
                               v
+-------------------------------------------------------------+
|                    LiteLLM Library Client                   |
+-------------------------------------------------------------+
```

## Detailed Flow Steps

### 1. User Input in UI (`app.py`)
In the sidebar, users select the LLM provider/model and fill out parameters:
*   `llm_provider_to_use` (e.g., `[az]azure/open-ai`)
*   `api_key_token`
*   **Azure OpenAI-specific configurations** (when using Azure OpenAI):
    *   `azure_endpoint`
    *   `azure_deployment`
    *   `api_version`

### 2. Core Propagation (`src/slidedeckai/core.py`)
These configurations are passed directly to the `SlideDeckAI` core engine:
*   **On Initialization**: Inside `app.py`, a new instance of `SlideDeckAI` is constructed with all selected credentials.
*   **On Dynamic Settings Update**: If settings are updated in the sidebar, `app.py` triggers the `slide_generator.set_model()` method to safely update the model, API key, and Azure-specific fields on the active instance.

### 3. LLM Wrapper Initialization (`src/slidedeckai/helpers/llm_helper.py`)
When generation or revision starts:
1.  `SlideDeckAI` invokes its internal helper method `_initialize_llm()`.
2.  `_initialize_llm()` calls `llm_helper.get_litellm_llm()`, passing:
    *   `provider`: Extracted from the model's bracketed code prefix (e.g., `az` for Azure, `gg` for Gemini) using `llm_helper.get_provider_model()`.
    *   `model`: The specific model name.
    *   `api_key`, `azure_endpoint_url`, `azure_deployment_name`, `azure_api_version`.
3.  `llm_helper.get_litellm_llm()` instantiates a `LiteLLMWrapper` holding those credentials.

### 4. Streaming Execution (`llm_helper.py`)
1.  `SlideDeckAI` invokes `_stream_llm_response(llm, ...)` which calls `llm.stream(prompt)`.
2.  `LiteLLMWrapper.stream()` forwards the request to `stream_litellm_completion()`, providing the target provider, model, messages, and credentials.
3.  `stream_litellm_completion()` performs validation checks (e.g., verifying that the Azure deployment name is not empty for Azure OpenAI) and calls the external `litellm.completion()` API to stream chunks back to the client.
