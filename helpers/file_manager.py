"""
File manager helper to work with uploaded files.
"""
import logging
import os
import sys

import streamlit as st
from pypdf import PdfReader

sys.path.append('..')
sys.path.append('../..')

from global_config import GlobalConfig


logger = logging.getLogger(__name__)


def get_pdf_contents(
        pdf_file: st.runtime.uploaded_file_manager.UploadedFile,
        max_pages: int = GlobalConfig.MAX_PAGE_COUNT
) -> str:
    """
    Extract the text contents from a PDF file.

    :param pdf_file: The uploaded PDF file.
    :param max_pages: The max no. of pages to extract contents from.
    :return: The contents.
    """

    reader = PdfReader(pdf_file)
    n_pages = min(max_pages, len(reader.pages))
    text = ''

    for page in range(n_pages):
        page = reader.pages[page]
        text += page.extract_text()

    return text
