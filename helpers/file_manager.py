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
    :param page_range: The range of pages to extract contents from.
    :param max_pages: The max no. of pages to extract contents from.
    :return: The contents.
    """

    reader = PdfReader(pdf_file)

    # get number of pages
    total_pages = len(reader.pages)
    n_pages = min(max_pages, total_pages)  # set n_pages to min of 50 or the pdf length if the pdf is shorter than 50 pages 

    # ensure validity
    start, end = page_range                # set start and end per the range (user-specified values)
    start = max(1, start)                  # set start to max of 1, or user-spec start
    end = min(n_pages, end)                # set end to min of n_pages, or user-spec end  

    logger.info(f"start={start}")
    logger.info(f"end={end}")
    text = ''
    for page_num in range(start - 1, end):
        page = reader.pages[page_num]
        text += page.extract_text()

    return text
