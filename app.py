import json5
import time
import streamlit as st
import streamlit.runtime.scriptrunner as st_sr

import llm_helper
import pptx_helper
from global_config import GlobalConfig


APP_TEXT = json5.loads(open(GlobalConfig.APP_STRINGS_FILE, 'r').read())


def build_ui():
    """
    Display the input elements for content generation. Only covers the first step.
    """

    st.title(APP_TEXT['app_name'])
    st.subheader(APP_TEXT['caption'])
    st.divider()

    st.header(APP_TEXT['section_headers'][0])
    st.caption(APP_TEXT['section_captions'][0])

    try:
        with open(GlobalConfig.PRELOAD_DATA_FILE, 'r') as in_file:
            preload_data = json5.loads(in_file.read())
    except (FileExistsError, FileNotFoundError):
        preload_data = {'topic': '', 'audience': ''}

    topic = st.text_area(
        APP_TEXT['input_labels'][0],
        value=preload_data['topic']
    )

    # Button with callback function
    st.button(APP_TEXT['button_labels'][0], on_click=button_clicked, args=[0])

    if st.session_state.clicked[0]:
        progress_text = 'Generating your presentation slides...give it a moment'
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

    if topic_length > 10:
        print(
            f'Topic: {topic}\n'
        )
        print('=' * 20)

        target_length = min(topic_length, GlobalConfig.LLM_MODEL_MAX_INPUT_LENGTH)

        try:
            slides_content = llm_helper.generate_slides_content(topic[:target_length]).strip()
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
                ' Need alternatives? Just change your description text and try again.'
                ' For example, you can start describing like "Create a slide deck on..."',
                icon="ℹ️"
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
    json_str = llm_helper.text_to_json(text)
    # yaml_str = llm_helper.text_to_yaml(text)
    print('=' * 20)
    print(f'JSON:\n{json_str}')
    print('=' * 20)
    st.code(json_str, language='json')

    progress_bar.progress(100, text='Done!')

    # Now, step 3
    st.divider()
    st.header(APP_TEXT['section_headers'][2])
    st.caption(APP_TEXT['section_captions'][2])

    st.button(APP_TEXT['button_labels'][2], on_click=button_clicked, args=[2])

    if st.session_state.clicked[2]:
        progress_text = 'Creating the slide deck...give it a moment'
        progress_bar = st.progress(0, text=progress_text)

        # Get a unique name for the file to save -- use the session ID
        ctx = st_sr.get_script_run_ctx()
        session_id = ctx.session_id
        timestamp = time.time()
        output_file_name = f'{session_id}_{timestamp}.pptx'

        pptx_helper.generate_powerpoint_presentation(json_str, as_yaml=False, output_file_name=output_file_name)
        progress_bar.progress(100, text='Done!')

        # st.download_button('Download file', binary_contents)  # Defaults to 'application/octet-stream'

        with open(output_file_name, 'rb') as f:
            st.download_button('Download PPTX file', f, file_name=output_file_name)


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
