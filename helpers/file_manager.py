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
        page_range: tuple[int, int],
        max_pages: int = GlobalConfig.MAX_PAGE_COUNT
) -> str:
    """
    Extract the text contents from a PDF file.

    :param pdf_file: The uploaded PDF file.
    :param max_pages: The max no. of pages to extract contents from.
    :return: The contents.
    """

    reader = PdfReader(pdf_file)

    total_pages = len(reader.pages)
    n_pages = min(max_pages, total_pages)

    start, end = page_range
    start = max(1, start)
    end = min(n_pages, end)

    text = ''
    for page_num in range(start - 1, end):
        page = reader.pages[page_num]
        text += page.extract_text()

    return text
