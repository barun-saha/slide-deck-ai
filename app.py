import base64
import os
import json5
import shutil
import time
import streamlit as st
import streamlit.runtime.scriptrunner as st_sr
from typing import List, Tuple

import llm_helper
import pptx_helper
from global_config import GlobalConfig


APP_TEXT = json5.loads(open(GlobalConfig.APP_STRINGS_FILE, 'r').read())
GB_CONVERTER = 2 ** 30


@st.cache_data
def get_contents_wrapper(text: str) -> str:
    """
    Fetch and cache the slide deck contents on a topic by calling an external API.

    :param text: The presentation topic
    :return: The slide deck contents or outline
    """

    return llm_helper.generate_slides_content(text).strip()


@st.cache_data
def get_json_wrapper(text: str) -> str:
    """
    Fetch and cache the JSON-formatted slide deck contents by calling an external API.

    :param text: The slide deck contents or outline
    :return: The JSON-formatted contents
    """

    return llm_helper.text_to_json(text)


@st.cache_data
def get_web_search_results_wrapper(text: str) -> List[Tuple[str, str]]:
    """
    Fetch and cache the Web search results on a given topic.

    :param text: The topic
    :return: A list of (title, link) tuples
    """

    results = []
    search_results = llm_helper.get_related_websites(text)

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

    total, used, free = shutil.disk_usage('/')
    total = total // GB_CONVERTER
    used = used // GB_CONVERTER
    free = free // GB_CONVERTER
    used_perc = 100.0 * used / total
    print(f'Total: {total} GB\n'
          f'Used: {used} GB\n'
          f'Free: {free} GB')

    print('\n'.join(os.listdir()))

    return used_perc


def build_ui():
    """
    Display the input elements for content generation. Only covers the first step.
    """

    get_disk_used_percentage()

    st.title(APP_TEXT['app_name'])
    st.subheader(APP_TEXT['caption'])
    # st.markdown(
    #     '![Visitors](https://api.visitorbadge.io/api/visitors?path=https%3A%2F%2Fhuggingface.co%2Fspaces%2Fbarunsaha%2Fslide-deck-ai&countColor=%23263759)'
    # )
    st.divider()

    st.header(APP_TEXT['section_headers'][0])
    st.caption(APP_TEXT['section_captions'][0])

    try:
        with open(GlobalConfig.PRELOAD_DATA_FILE, 'r') as in_file:
            preload_data = json5.loads(in_file.read())
    except (FileExistsError, FileNotFoundError):
        preload_data = {'topic': '', 'audience': ''}

    # with st.form('describe-topic-form'):
    topic = st.text_area(
        APP_TEXT['input_labels'][0],
        value=preload_data['topic']
    )

    # Button with callback function
    st.button(APP_TEXT['button_labels'][0], on_click=button_clicked, args=[0])
    # desc_topic_btn_submitted = st.form_submit_button(
    #     APP_TEXT['button_labels'][0],
    #     on_click=button_clicked,
    #     args=[0]
    # )

    if st.session_state.clicked[0]:
        # if desc_topic_btn_submitted:
        progress_text = 'Generating contents for your slides...give it a moment'
        progress_bar = st.progress(0, text=progress_text)

        topic_txt = topic.strip()
        process_topic_inputs(topic_txt, progress_bar)


def process_topic_inputs(topic: str, progress_bar):
    """
    Process the inputs to generate contents for the slides.

    :param topic: The presentation topic
    :param progress_bar: Progress bar from the page
    :return:
    """

    topic_length = len(topic)
    print(f'Input length:: topic: {topic_length}')

    if topic_length >= 10:
        print(
            f'Topic: {topic}\n'
        )
        print('=' * 20)

        target_length = min(topic_length, GlobalConfig.LLM_MODEL_MAX_INPUT_LENGTH)

        try:
            slides_content = get_contents_wrapper(topic[:target_length])
            content_length = len(slides_content)

            print('=' * 20)
            print(f'Slides content:\n{slides_content}')
            print(f'Content length: {content_length}')
            print('=' * 20)
            st.write(f'''Slides content:\n{slides_content}''')
            progress_bar.progress(100, text='Done!')

            if content_length == 0:
                st.error(APP_TEXT['content_generation_failure_error'])
                return

            st.info(
                'The generated content doesn\'t look so great?'
                ' Need alternatives? Just change your description text and try again.',
                icon="💡️"
            )

            # Move on to step 2
            st.divider()
            st.header(APP_TEXT['section_headers'][1])
            st.caption(APP_TEXT['section_captions'][1])

            # Streamlit multiple buttons work in a weird way!
            # Click on any button, the page just reloads!
            # Buttons are not "stateful"
            # https://blog.streamlit.io/10-most-common-explanations-on-the-streamlit-forum/#1-buttons-aren%E2%80%99t-stateful
            # Apparently, "nested button click" needs to be handled differently
            # https://playground.streamlit.app/?q=triple-button

            st.button(APP_TEXT['button_labels'][1], on_click=button_clicked, args=[1])

            if st.session_state.clicked[1]:
                progress_text = 'Converting...give it a moment'
                progress_bar = st.progress(0, text=progress_text)

                process_slides_contents(slides_content, progress_bar)
        except ValueError as ve:
            st.error(f'Unfortunately, an error occurred: {ve}! '
                     f'Please change the text, try again later, or report it, sharing your inputs.')

    else:
        st.error('Not enough information provided! Please be little more descriptive :)')


def process_slides_contents(text: str, progress_bar: st.progress):
    """
    Convert given text into structured data and display. Update the UI.

    :param text: The contents generated for the slides
    :param progress_bar: Progress bar for this step
    """

    print('JSON button clicked')
    json_str = ''

    try:
        json_str = get_json_wrapper(text)
    except Exception as ex:
        st.error(f'An exception occurred while trying to convert to JSON.'
                 f' It could be because of heavy traffic or something else.'
                 f' Try doing it again or try again later.\n'
                 f' Error message: {ex}')
        # st.stop()

    # yaml_str = llm_helper.text_to_yaml(text)
    print('=' * 20)
    print(f'JSON:\n{json_str}')
    print('=' * 20)
    st.code(json_str, language='json')

    if len(json_str) > 0:
        progress_bar.progress(100, text='Done!')
        st.info(
            'Tip: In some scenarios, the JSON creates a deeper nesting of the bullet points'
            ' than what is expected. You can try to regenerate the JSON'
            ' by making a minor change in the topic description in the previous step, e.g.,'
            ' by adding or removing a character. Alternatively, you can edit this in the slide'
            ' deck that would be generated in the next step.',
            icon="💡️"
        )
    else:
        st.error('Unfortunately, JSON generation failed, so the next steps would lead to nowhere.'
                 ' Try again or come back later.')

    # Now, step 3
    st.divider()
    st.header(APP_TEXT['section_headers'][2])
    st.caption(APP_TEXT['section_captions'][2])

    texts = list(GlobalConfig.PPTX_TEMPLATE_FILES.keys())
    captions = [GlobalConfig.PPTX_TEMPLATE_FILES[x]['caption'] for x in texts]

    # with st.form('create-slides-form'):
    pptx_template = st.radio(
        'Select a presentation template:',
        texts,
        captions=captions,
        horizontal=True
    )

    st.button(APP_TEXT['button_labels'][2], on_click=button_clicked, args=[2])
    # create_slides_btn_submitted = st.form_submit_button(APP_TEXT['button_labels'][2])

    if st.session_state.clicked[2]:
        # if create_slides_btn_submitted:
        progress_text = 'Creating the slide deck...give it a moment'
        progress_bar = st.progress(0, text=progress_text)

        # Get a unique name for the file to save -- use the session ID
        ctx = st_sr.get_script_run_ctx()
        session_id = ctx.session_id
        timestamp = time.time()
        output_file_name = f'{session_id}_{timestamp}.pptx'

        all_headers = pptx_helper.generate_powerpoint_presentation(
            json_str,
            as_yaml=False,
            slides_template=pptx_template,
            output_file_name=output_file_name
        )
        progress_bar.progress(100, text='Done!')

        # st.download_button('Download file', binary_contents)  # Defaults to 'application/octet-stream'

        with open(output_file_name, 'rb') as f:
            st.download_button('Download PPTX file', f, file_name=output_file_name)

        bonus_divider = st.empty()
        bonus_header = st.empty()
        bonus_caption = st.empty()

        urls_text = st.empty()
        urls_list = st.empty()

        img_empty = st.empty()
        img_text = st.empty()
        img_contents = st.empty()
        img_tip = st.empty()

        st.divider()
        st.text(APP_TEXT['tos'])
        st.text(APP_TEXT['tos2'])

        show_bonus_stuff(
            all_headers,
            bonus_divider,
            bonus_header,
            bonus_caption,
            urls_text,
            urls_list,
            img_empty,
            img_text,
            img_contents,
            img_tip
        )


def show_bonus_stuff(
        ppt_headers: List,
        *st_placeholders
):
    """
    Show relevant links and images for the presentation topic.

    :param ppt_headers: A list of all slide headers
    """

    (
        bonus_divider,
        bonus_header,
        bonus_caption,
        urls_text,
        urls_list,
        img_empty,
        img_text,
        img_contents,
        img_tip
    ) = st_placeholders

    bonus_divider.divider()
    bonus_header.header(APP_TEXT['section_headers'][3])
    bonus_caption.caption(APP_TEXT['section_captions'][3])

    urls_text.write(APP_TEXT['urls_info'])

    # Use the presentation title and the slides headers to find relevant info online
    ppt_text = ' '.join(ppt_headers)
    search_results = get_web_search_results_wrapper(ppt_text)
    md_text_items = []

    for (title, link) in search_results:
        md_text_items.append(f'[{title}]({link})')

    urls_list.markdown('\n\n'.join(md_text_items))

    img_empty.write('')
    img_text.write(APP_TEXT['image_info'])
    image = get_ai_image_wrapper(ppt_text)

    if len(image) > 0:
        image = base64.b64decode(image)
        img_contents.image(image, caption=ppt_text)
        img_tip.info('Tip: Right-click on the image to save it.', icon="💡️")


def button_clicked(button):
    """
    Update the button clicked value in session state.
    """

    st.session_state.clicked[button] = True


def main():
    # Initialize the key in session state to manage the nested buttons states
    if 'clicked' not in st.session_state:
        st.session_state.clicked = {0: False, 1: False, 2: False}

    build_ui()


if __name__ == '__main__':
    main()
