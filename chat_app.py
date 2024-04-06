import logging
import random

import json5
import streamlit as st
from langchain_community.chat_message_histories import (
    StreamlitChatMessageHistory
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory

from global_config import GlobalConfig
from helpers import llm_helper


APP_TEXT = json5.loads(open(GlobalConfig.APP_STRINGS_FILE, 'r', encoding='utf-8').read())
# langchain.debug = True
# langchain.verbose = True

logger = logging.getLogger(__name__)
progress_bar = st.progress(0, text='Setting up SlideDeck AI...')


def display_page_header_content():
    """
    Display content in the page header.
    """

    st.title(APP_TEXT['app_name'])
    st.subheader(APP_TEXT['caption'])
    st.markdown(
        'Powered by'
        ' [Mistral-7B-Instruct-v0.2](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2)'
    )


def display_page_footer_content():
    """
    Display content in the page footer.
    """

    st.text(APP_TEXT['tos'] + '\n\n' + APP_TEXT['tos2'])
    # st.markdown(
    #     '![Visitors](https://api.visitorbadge.io/api/visitors?path=https%3A%2F%2Fhuggingface.co%2Fspaces%2Fbarunsaha%2Fslide-deck-ai&countColor=%23263759)'  # noqa: E501
    # )


def build_ui():
    """
    Display the input elements for content generation.
    """

    display_page_header_content()

    with st.expander('Usage Policies and Limitations'):
        display_page_footer_content()

    progress_bar.progress(50, text='Setting up chat interface...')
    set_up_chat_ui()


def set_up_chat_ui():
    """
    Prepare the chat interface and related functionality.
    """

    history = StreamlitChatMessageHistory(key='chat_messages')
    llm = llm_helper.get_hf_endpoint()

    with open(GlobalConfig.CHAT_TEMPLATE_FILE, 'r', encoding='utf-8') as in_file:
        template = in_file.read()

    prompt = ChatPromptTemplate.from_template(template)

    chain = prompt | llm

    chain_with_history = RunnableWithMessageHistory(
        chain,
        lambda session_id: history,  # Always return the instance created earlier
        input_messages_key='question',
        history_messages_key='chat_history',
    )

    with st.expander('Usage Instructions'):
        st.write(GlobalConfig.CHAT_USAGE_INSTRUCTIONS)

    st.chat_message('ai').write(
        random.choice(APP_TEXT['ai_greetings'])
    )

    for msg in history.messages:
        st.chat_message(msg.type).markdown(msg.content)

    progress_bar.progress(100, text='Done!')
    progress_bar.empty()

    if prompt := st.chat_input(
        placeholder=APP_TEXT['chat_placeholder'],
        max_chars=GlobalConfig.LLM_MODEL_MAX_INPUT_LENGTH
    ):
        logger.debug('User input: %s', prompt)
        st.chat_message('user').write(prompt)

        # As usual, new messages are added to StreamlitChatMessageHistory when the Chain is called
        config = {'configurable': {'session_id': 'any'}}
        response = chain_with_history.invoke({'question': prompt}, config)
        st.chat_message('ai').markdown('```json\n' + response)


def main():
    """
    Trigger application run.
    """

    build_ui()


if __name__ == '__main__':
    main()
