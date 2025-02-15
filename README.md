---
title: SlideDeck AI
emoji: 🏢
colorFrom: yellow
colorTo: green
sdk: streamlit
sdk_version: 1.32.2
app_file: app.py
pinned: false
license: mit
---

# SlideDeck AI

We spend a lot of time on creating the slides and organizing our thoughts for any presentation. 
With SlideDeck AI, co-create slide decks on any topic with Generative Artificial Intelligence.
Describe your topic and let SlideDeck AI generate a PowerPoint slide deck for you—it's as simple as that!


# Process

SlideDeck AI works in the following way:

1. Given a topic description, it uses a Large Language Model (LLM) to generate the *initial* content of the slides. 
The output is generated as structured JSON data based on a pre-defined schema.
2. Next, it uses the keywords from the JSON output to search and download a few images with a certain probability.
3. Subsequently, it uses the `python-pptx` library to generate the slides, 
based on the JSON data from the previous step. 
A user can choose from a set of pre-defined presentation templates.
4. At this stage onward, a user can provide additional instructions to *refine* the content.
For example, one can ask to add another slide or modify an existing slide.
A history of instructions is maintained.
5. Every time SlideDeck AI generates a PowerPoint presentation, a download button is provided.
Clicking on the button will download the file.


# Summary of the LLMs

SlideDeck AI allows the use of different LLMs from four online providers—Hugging Face, Google, Cohere, and Together AI. These service providers—even the latter three—offer generous free usage of relevant LLMs without requiring any billing information.  

Based on several experiments, SlideDeck AI generally recommends the use of Mistral NeMo and Gemini Flash to generate the slide decks.

The supported LLMs offer different styles of content generation. Use one of the following LLMs along with relevant API keys/access tokens, as appropriate, to create the content of the slide deck:

| LLM                              | Provider (code) | Requires API key                                                                     | Characteristics          |
|:---------------------------------| :------- |:-------------------------------------------------------------------------------------|:-------------------------|
| Mistral 7B Instruct v0.2         | Hugging Face (`hf`) | Optional but strongly encouraged; [get here](https://huggingface.co/settings/tokens) | Faster, shorter content  |
| Mistral NeMo Instruct 2407       | Hugging Face (`hf`) | Optional but strongly encouraged; [get here](https://huggingface.co/settings/tokens) | Slower, longer content   |
| Gemini 1.5 Flash                 | Google Gemini API (`gg`) | Mandatory; [get here](https://aistudio.google.com/apikey)                            | Faster, longer content   |
| Gemini 2.0 Flash                 | Google Gemini API (`gg`) | Mandatory; [get here](https://aistudio.google.com/apikey)                            | Faster, longer content   |
| Gemini 2.0 Flash Lite            | Google Gemini API (`gg`) | Mandatory; [get here](https://aistudio.google.com/apikey)                            | Faster, longer content   |
| Command R+                       | Cohere (`co`) | Mandatory; [get here](https://dashboard.cohere.com/api-keys)                         | Shorter, simpler content |
| Llama 3.3 70B Instruct Turbo     | Together AI (`to`) | Mandatory; [get here](https://api.together.ai/settings/api-keys)                     | Detailed, slower         |
| Llama 3.1 8B Instruct Turbo 128K | Together AI (`to`) | Mandatory; [get here](https://api.together.ai/settings/api-keys)                     | Shorter                  |

The Mistral models (via Hugging Face) do not mandatorily require an access token. In other words, you are always free to use these two LLMs, subject to Hugging Face's usage constrains. However, you are strongly encouraged to get and use your own Hugging Face access token.

**IMPORTANT**: SlideDeck AI does **NOT** store your API keys/tokens or transmit them elsewhere. If you provide your API key, it is only used to invoke the relevant LLM to generate contents. That's it! This is an 
Open-Source project, so feel free to audit the code and convince yourself. 

In addition, offline LLMs provided by Ollama can be used. Read below to know more. 


# Icons

SlideDeck AI uses a subset of icons from [bootstrap-icons-1.11.3](https://github.com/twbs/icons)
 (MIT license) in the slides. A few icons from [SVG Repo](https://www.svgrepo.com/)
(CC0, MIT, and Apache licenses) are also used. 


# Local Development

SlideDeck AI uses LLMs via different providers, such as Hugging Face, Google, and Gemini.
To run this project by yourself, you need to provide the `HUGGINGFACEHUB_API_TOKEN` API key,
for example, in a `.env` file. Alternatively, you can provide the access token in the app's user interface itself (UI). For other LLM providers, the API key can only be specified in the UI.  For image search, the `PEXEL_API_KEY` should be made available as an environment variable. 
Visit the respective websites to obtain the API keys.

## Offline LLMs Using Ollama

SlideDeck AI allows the use of offline LLMs to generate the contents of the slide decks. This is typically suitable for individuals or organizations who would like to use self-hosted LLMs for privacy concerns, for example.

Offline LLMs are made available via Ollama. Therefore, a pre-requisite here is to have [Ollama installed](https://ollama.com/download) on the system and the desired [LLM](https://ollama.com/search) pulled locally.

In addition, the `RUN_IN_OFFLINE_MODE` environment variable needs to be set to `True` to enable the offline mode. This, for example, can be done using a `.env` file or from the terminal. The typical steps to use SlideDeck AI in offline mode (in a `bash` shell) are as follows:

```bash
ollama list  # View locally available LLMs
export RUN_IN_OFFLINE_MODE=True  # Enable the offline mode to use Ollama
git clone https://github.com/barun-saha/slide-deck-ai.git
cd slide-deck-ai
python -m venv venv  # Create a virtual environment
source venv/bin/activate  # On a Linux system
pip install -r requirements.txt
streamlit run ./app.py  # Run the application
```

The `.env` file should be created inside the `slide-deck-ai` directory. 

The UI is similar to the online mode. However, rather than selecting an LLM from a list, one has to write the name of the Ollama model to be used in a textbox. There is no API key asked here.

The online and offline modes are mutually exclusive. So, setting `RUN_IN_OFFLINE_MODE` to `False` will make SlideDeck AI use the online LLMs (i.e., the "original mode."). By default, `RUN_IN_OFFLINE_MODE` is set to `False`.

Finally, the focus is on using offline LLMs, not going completely offline. So, Internet connectivity would still be required to fetch the images from Pexels. 


# Live Demo

- [SlideDeck AI](https://huggingface.co/spaces/barunsaha/slide-deck-ai) on Hugging Face Spaces
- [Demo video](https://youtu.be/QvAKzNKtk9k) of the chat interface on YouTube


# Award

SlideDeck AI has won the 3rd Place in the [Llama 2 Hackathon with Clarifai](https://lablab.ai/event/llama-2-hackathon-with-clarifai) in 2023.