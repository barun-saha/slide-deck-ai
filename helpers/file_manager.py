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
        page_range: tuple[int, int]) -> str:
    """
    Extract the text contents from a PDF file.

    :param pdf_file: The uploaded PDF file.
    :param page_range: The range of pages to extract contents from.
    :return: The contents.
    """

    reader = PdfReader(pdf_file)

    start, end = page_range  # set start and end per the range (user-specified values)
    
    print(f"Name: {pdf_file.name} Page range: {start} to {end}")
    text = ''
    for page_num in range(start - 1, end):
        page = reader.pages[page_num]
        text += page.extract_text()

    return text

def validate_page_range(pdf_file: st.runtime.uploaded_file_manager.UploadedFile,
                        start:int, end:int) -> tuple[int, int]:
    """
    Validate the page range.

    :param pdf_file: The uploaded PDF file.
    :param start: The start page 
    :param end: The end page
    :return: The validated page range tuple
    """
    n_pages = len(PdfReader(pdf_file).pages)

    # set start to max of 1 or specified start (whichever's higher)
    start = max(1, start)

    # set end to min of pdf length or specified end (whichever's lower)
    end = min(n_pages, end)

    if start > end:  # if the start is higher than the end, make it 1
        start = 1

    return start, end
