---
title: Slide Deck Ai
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


# Process

SlideDeck AI works in the following way:

1. Given a topic description, it uses Llama 2 to generate the outline/contents of the slides.
2. Next, it uses GPT 3.5 to convert the output from the previous step into JSON.
3. Subsequently, it uses the `python-pptx` library to generate the slides, 
based on the JSON data from the previous step. 
Here, a user can choose from a set of three pre-defined presentation templates.
4. In addition, it uses Metaphor to fetch Web pages related to the topic.
5. Finally, it uses Stable Diffusion 2 to generate an image, based on the title and each slide heading.


# Local Development

SlideDeck AI uses the Clarifai API of LangChain to realize the first two steps. 
It also sends a Web request to Clarifai for the final step.
To run this project by yourself, you need to provide the `CLARIFAI_PAT` and `METAPHOR_API_KEY` API keys,
for example, in a `.env` file.

