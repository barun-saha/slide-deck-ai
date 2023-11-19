---
title: SlideDeck AI
emoji: 🏢
colorFrom: yellow
colorTo: green
sdk: streamlit
sdk_version: 1.26.0
app_file: app.py
pinned: false
license: mit
---

# SlideDeck AI

We spend a lot of time on creating the slides and organizing our thoughts for any presentation. 
With SlideDeck AI, co-create slide decks on any topic with Generative Artificial Intelligence.
Describe your topic and let SlideDeck AI generate a PowerPoint slide deck for you—it's as simple as that!

SlideDeck AI is powered by [Mistral 7B Instruct](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.1).
Originally, it was built using the Llama 2 API provided by Clarifai.

# Process

SlideDeck AI works in the following way:

1. Given a topic description, it uses Mistral 7B Instruct to generate the outline/contents of the slides. 
The output is generated as structured JSON data based on a pre-defined schema.
2. Subsequently, it uses the `python-pptx` library to generate the slides, 
based on the JSON data from the previous step. 
Here, a user can choose from a set of three pre-defined presentation templates.
3. In addition, it uses Metaphor to fetch Web pages related to the topic.

4. ~~Finally, it uses Stable Diffusion 2 to generate an image, based on the title and each slide heading.~~


# Local Development

SlideDeck AI uses [Mistral 7B Instruct](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.1) 
via the Hugging Face Inference API.
To run this project by yourself, you need to provide the `HUGGINGFACEHUB_API_TOKEN` and `METAPHOR_API_KEY` API keys,
for example, in a `.env` file. Visit the respective websites to obtain the keys.


# Live Demo

[SlideDeck AI](https://huggingface.co/spaces/barunsaha/slide-deck-ai)


# Award

SlideDeck AI has won the 3rd Place in the [Llama 2 Hackathon with Clarifai](https://lablab.ai/event/llama-2-hackathon-with-clarifai).