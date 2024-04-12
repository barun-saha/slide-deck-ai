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

SlideDeck AI is powered by [Mistral 7B Instruct](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2).
Originally, it was built using the Llama 2 API provided by Clarifai.

*Update*: Legacy SlideDeck AI allowed one-shot generation of a slide deck based on the inputs. 
In contrast, SlideDeck AI *Reloaded* enables an iterative workflow with a conversational interface,
where you can create and improve the presentation.


# Process

SlideDeck AI works in the following way:

1. Given a topic description, it uses Mistral 7B Instruct to generate the *initial* content of the slides. 
The output is generated as structured JSON data based on a pre-defined schema.
2. Subsequently, it uses the `python-pptx` library to generate the slides, 
based on the JSON data from the previous step. 
A user can choose from a set of three pre-defined presentation templates.
3. At this stage onward, a user can provide additional instructions to refine the content.
For example, one can ask to add another slide or modify an existing slide.
A history of instructions is maintained.
4. Every time SlideDeck AI generates a PowerPoint presentation, a download button is provided.
Clicking on the button will download the file.


# Known Issues

- **Incorrect JSON**: Sometimes the JSON generated could be syntactically incorrect. 
You can try asking SlideDeck AI to regenerate the content and fix the JSON syntax error.
This, however, is not guaranteed to work. The alternative is to reload the website and try again.
- **Connection timeout**: Requests sent to the Hugging Face Inference endpoint might time out.
A maximum of five retries are attempted. If it still does not work, wait for a while and try again.

The following is not an issue but might appear as a strange behavior:
- **Cannot paste text in the input box**: If the length of the copied text is greater than the maximum
number of allowed characters in the textbox, pasting would not work.


# Local Development

SlideDeck AI uses [Mistral 7B Instruct](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2) 
via the Hugging Face Inference API.
To run this project by yourself, you need to provide the `HUGGINGFACEHUB_API_TOKEN` API key,
for example, in a `.env` file. Visit the respective websites to obtain the keys.


# Live Demo

[SlideDeck AI](https://huggingface.co/spaces/barunsaha/slide-deck-ai) on Hugging Face Spaces


# Award

SlideDeck AI has won the 3rd Place in the [Llama 2 Hackathon with Clarifai](https://lablab.ai/event/llama-2-hackathon-with-clarifai) in 2023.