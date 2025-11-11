"""
File manager to help with uploaded PDF files.
"""
import logging

import streamlit as st
from pypdf import PdfReader


logger = logging.getLogger(__name__)


def get_pdf_contents(
        pdf_file: st.runtime.uploaded_file_manager.UploadedFile,
        page_range: tuple[int, None] | tuple[int, int]
) -> str:
    """
    Extract the text contents from a PDF file.

    Args:
        pdf_file: The uploaded PDF file.
        page_range: The range of pages to extract contents from.

    Returns:
        The contents.
    """
    reader = PdfReader(pdf_file)
    start, end = page_range  # Set start and end per the range (user-specified values)
    text = ''

    if end is None:
        # If end is None (where PDF has only 1 page or start = end), extract start
        end = start

    # Get the text from the specified page range
    for page_num in range(start - 1, end):
        text += reader.pages[page_num].extract_text()

    return text

def validate_page_range(
        pdf_file: st.runtime.uploaded_file_manager.UploadedFile,
        start:int, end:int
) -> tuple[int, None] | tuple[int, int]:
    """
    Validate the page range for the uploaded PDF file. Adjusts start and end
    to be within the valid range of pages in the PDF.

    Args:
        pdf_file: The uploaded PDF file.
        start: The start page
        end: The end page

    Returns:
        The validated page range tuple
    """
    n_pages = len(PdfReader(pdf_file).pages)

    # Set start to max of 1 or specified start (whichever's higher)
    start = max(1, start)
    # Set end to min of pdf length or specified end (whichever's lower)
    end = min(n_pages, end)

    if start > end:  # If the start is higher than the end, make it 1
        start = 1

    if start == end:
        # If start = end (including when PDF is 1 page long), set end to None
        return start, None

    return start, end
