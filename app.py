import base64
import os
import pathlib
import json5
import logging
import shutil
import time
import streamlit as st
import streamlit.runtime.scriptrunner as st_sr
from typing import List, Tuple
import metaphor_python as metaphor
import tempfile

import llm_helper
import pptx_helper
from global_config import GlobalConfig


APP_TEXT = json5.loads(open(GlobalConfig.APP_STRINGS_FILE, 'r').read())
GB_CONVERTER = 2 ** 30


logging.basicConfig(
    level=GlobalConfig.LOG_LEVEL,
    format='%(asctime)s - %(message)s',
)


@st.cache_data
def get_contents_wrapper(text: str) -> str:
    """
    Fetch and cache the slide deck contents on a topic by calling an external API.

    :param text: The presentation topic
    :return: The slide deck contents or outline in JSON format
    """

    logging.info('LLM call because of cache miss...')
    return llm_helper.generate_slides_content(text).strip()


@st.cache_resource
def get_metaphor_client_wrapper() -> metaphor.Metaphor:
    """
    Create a Metaphor client for semantic Web search.

    :return: Metaphor instance
    """

    return metaphor.Metaphor(api_key=GlobalConfig.METAPHOR_API_KEY)


@st.cache_data
def get_web_search_results_wrapper(text: str) -> List[Tuple[str, str]]:
    """
    Fetch and cache the Web search results on a given topic.

    :param text: The topic
    :return: A list of (title, link) tuples
    """

    results = []
    search_results = get_metaphor_client_wrapper().search(
        text,
        use_autoprompt=True,
        num_results=5
    )

    for a_result in search_results.results:
        results.append((a_result.title, a_result.url))

    return results


@st.cache_data
def get_ai_image_wrapper(text: str) -> str:
    """
    Fetch and cache a Base 64-encoded image by calling an external API.

    :param text: The image prompt
    :return: The Base 64-encoded image
    """

    return llm_helper.get_ai_image(text)


def get_disk_used_percentage() -> float:
    """
    Compute the disk usage.

    :return: Percentage of the disk space currently used
    """

    total, used, free = shutil.disk_usage(__file__)
    total = total // GB_CONVERTER
    used = used // GB_CONVERTER
    free = free // GB_CONVERTER
    used_perc = 100.0 * used / total

    logging.debug(f'Total: {total} GB\n'
                  f'Used: {used} GB\n'
                  f'Free: {free} GB')

    logging.debug('\n'.join(os.listdir()))

    return used_perc


def build_ui():
    """
    Display the input elements for content generation. Only covers the first step.
    """

    # get_disk_used_percentage()

    st.title(APP_TEXT['app_name'])
    st.subheader(APP_TEXT['caption'])

    with st.form('my_form'):
        # Topic input
        try:
            with open(GlobalConfig.PRELOAD_DATA_FILE, 'r') as in_file:
                preload_data = json5.loads(in_file.read())
        except (FileExistsError, FileNotFoundError):
            preload_data = {'topic': '', 'audience': ''}

        topic = st.text_area(
            APP_TEXT['input_labels'][0],
            value=preload_data['topic']
        )

        texts = list(GlobalConfig.PPTX_TEMPLATE_FILES.keys())
        captions = [GlobalConfig.PPTX_TEMPLATE_FILES[x]['caption'] for x in texts]

        pptx_template = st.radio(
            'Select a presentation template:',
            texts,
            captions=captions,
            horizontal=True
        )

        st.divider()
        submit = st.form_submit_button('Generate slide deck')

    if submit:
        # st.write(f'Clicked {time.time()}')
        progress_text = 'Generating the slides...give it a moment'
        progress_bar = st.progress(0, text=progress_text)

        topic_txt = topic.strip()
        generate_presentation(topic_txt, pptx_template, progress_bar)

    st.divider()
    st.text(APP_TEXT['tos'])
    st.text(APP_TEXT['tos2'])

    st.markdown(
        '![Visitors](https://api.visitorbadge.io/api/visitors?path=https%3A%2F%2Fhuggingface.co%2Fspaces%2Fbarunsaha%2Fslide-deck-ai&countColor=%23263759)'
    )


def generate_presentation(topic: str, pptx_template: str, progress_bar):
    """
    Process the inputs to generate the slides.

    :param topic: The presentation topic based on which contents are to be generated
    :param pptx_template: The PowerPoint template name to be used
    :param progress_bar: Progress bar from the page
    :return:
    """

    topic_length = len(topic)
    logging.debug(f'Input length:: topic: {topic_length}')

    if topic_length >= 10:
        logging.debug(
            f'Topic: {topic}\n'
        )

        target_length = min(topic_length, GlobalConfig.LLM_MODEL_MAX_INPUT_LENGTH)

        try:
            # Step 1: Generate the contents in JSON format using an LLM
            json_str = process_slides_contents(topic[:target_length], progress_bar)

            # Step 2: Generate the slide deck based on the template specified
            if len(json_str) > 0:
                st.info(
                    'Tip: The generated content doesn\'t look so great?'
                    ' Need alternatives? Just change your description text and try again.',
                    icon="💡️"
                )
            else:
                st.error('Unfortunately, JSON generation failed, so the next steps would lead to nowhere.'
                         ' Try again or come back later.')
                return

            all_headers = generate_slide_deck(json_str, pptx_template, progress_bar)

            # Step 3: Bonus stuff: Web references and AI art
            show_bonus_stuff(all_headers)

        except ValueError as ve:
            st.error(f'Unfortunately, an error occurred: {ve}! '
                     f'Please change the text, try again later, or report it, sharing your inputs.')

    else:
        st.error('Not enough information provided! Please be little more descriptive :)')


def process_slides_contents(text: str, progress_bar: st.progress) -> str:
    """
    Convert given text into structured data and display. Update the UI.

    :param text: The topic description for the presentation
    :param progress_bar: Progress bar for this step
    :return: The contents as a JSON-formatted string
    """

    json_str = ''

    try:
        logging.info(f'Calling LLM for content generation on the topic: {text}')
        json_str = get_contents_wrapper(text)
    except Exception as ex:
        st.error(f'An exception occurred while trying to convert to JSON.'
                 f' It could be because of heavy traffic or something else.'
                 f' Try doing it again or try again later.\n'
                 f' Error message: {ex}')

    logging.debug(f'JSON: {json_str}')

    progress_bar.progress(50, text='Contents generated')

    with st.expander('The generated contents (in JSON format)'):
        st.code(json_str, language='json')

    return json_str


def generate_slide_deck(json_str: str, pptx_template: str, progress_bar) -> List:
    """
    Create a slide deck.

    :param json_str: The contents in JSON format
    :param pptx_template: The PPTX template name
    :param progress_bar: Progress bar
    :return: A list of all slide headers and the title
    """

    progress_text = 'Creating the slide deck...give it a moment'
    progress_bar.progress(75, text=progress_text)

    # # Get a unique name for the file to save -- use the session ID
    # ctx = st_sr.get_script_run_ctx()
    # session_id = ctx.session_id
    # timestamp = time.time()
    # output_file_name = f'{session_id}_{timestamp}.pptx'

    temp = tempfile.NamedTemporaryFile(delete=False, suffix='.pptx')
    path = pathlib.Path(temp.name)

    logging.info('Creating PPTX file...')
    all_headers = pptx_helper.generate_powerpoint_presentation(
        json_str,
        as_yaml=False,
        slides_template=pptx_template,
        output_file_path=path
    )
    progress_bar.progress(100, text='Done!')

    with open(path, 'rb') as f:
        st.download_button('Download PPTX file', f, file_name='Presentation.pptx')

    return all_headers


def show_bonus_stuff(ppt_headers: List[str]):
    """
    Show bonus stuff for the presentation.

    :param ppt_headers: A list of the slide headings.
    """

    # Use the presentation title and the slide headers to find relevant info online
    logging.info('Calling Metaphor search...')
    ppt_text = ' '.join(ppt_headers)
    search_results = get_web_search_results_wrapper(ppt_text)
    md_text_items = []

    for (title, link) in search_results:
        md_text_items.append(f'[{title}]({link})')

    with st.expander('Related Web references'):
        st.markdown('\n\n'.join(md_text_items))

    # Avoid image generation. It costs time and an API call, so just limit to the text generation.
    with st.expander('AI-generated image on the presentation topic'):
        logging.info('Calling SDXL for image generation...')
        # img_empty.write('')
        # img_text.write(APP_TEXT['image_info'])
        image = get_ai_image_wrapper(ppt_text)

        if len(image) > 0:
            image = base64.b64decode(image)
            st.image(image, caption=ppt_text)
            st.info('Tip: Right-click on the image to save it.', icon="💡️")
            logging.info('Image added')


def main():
    build_ui()


if __name__ == '__main__':
    main()
