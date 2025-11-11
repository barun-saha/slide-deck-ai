"""
Unit tests for the file manager module.
"""
import io
from typing import Any

import pytest

from slidedeckai.helpers import file_manager


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakePdf:
    def __init__(self, pages_text: list[str]) -> None:
        self.pages = [_FakePage(t) for t in pages_text]


def _make_fake_pdf_reader(pages_text: list[str]) -> Any:
    """Return a callable that behaves like PdfReader when called with a file.

    The returned object will have a .pages attribute with page objects that
    implement extract_text(). This lets tests avoid creating real PDF
    binaries and keeps tests deterministic.
    """
    def _reader(_fileobj: Any) -> _FakePdf:
        return _FakePdf(pages_text)

    return _reader


def test_get_pdf_contents_single_page(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_pdf_contents should return the text for a single-page PDF when
    page_range end is None.
    """
    fake_texts = ['Page one text']
    monkeypatch.setattr(
        file_manager, 'PdfReader', _make_fake_pdf_reader(fake_texts)
    )

    # When start == end, validate_page_range returns (start, None) — emulate
    # that contract here and exercise get_pdf_contents handling of end=None.
    result = file_manager.get_pdf_contents(
        pdf_file=io.BytesIO(b'pdf'),
        page_range=(1, None)
    )
    assert result == 'Page one text'


def test_get_pdf_contents_multi_page_range(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_pdf_contents should concatenate text from multiple pages in the
    provided range.
    """
    fake_texts = ['First', 'Second', 'Third']
    monkeypatch.setattr(
        file_manager, 'PdfReader', _make_fake_pdf_reader(fake_texts)
    )

    # Request pages 1..2 (inclusive). Internally the function iterates from
    # start-1 up to end (exclusive), so passing (1, 2) should return First + Second
    result = file_manager.get_pdf_contents(
        pdf_file=io.BytesIO(b'pdf'),
        page_range=(1, 2)
    )
    assert result == 'FirstSecond'


@pytest.mark.parametrize(
    'start,end,expected',
    [
        (0, 5, (1, 3)),  # start too small -> clamped to 1; end clamped to n_pages
        (2, 2, (2, None)),  # equal start & end -> end is None
        (10, 1, (1, None)),  # start > end -> start reset to 1
        (1, 100, (1, 3)),  # end too large -> clamped to n_pages
    ],
)
def test_validate_page_range_various(
    monkeypatch: pytest.MonkeyPatch, start: int, end: int, expected: tuple[int, Any]
) -> None:
    """validate_page_range should correctly normalize start/end values and
    return (start, None) when the constrained range is a single page.
    """
    fake_texts = ['A', 'B', 'C']
    monkeypatch.setattr(
        file_manager, 'PdfReader', _make_fake_pdf_reader(fake_texts)
    )
    result = file_manager.validate_page_range(
        pdf_file=io.BytesIO(b'pdf'),
        start=start,
        end=end
    )
    assert result == expected


def test_validate_page_range_two_page_return(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the validated range spans multiple pages, validate_page_range
    should return the clamped (start, end) pair with end not None.
    """
    fake_texts = ['A', 'B', 'C', 'D']
    monkeypatch.setattr(
        file_manager, 'PdfReader', _make_fake_pdf_reader(fake_texts)
    )
    # start=2 end=3 should be unchanged and returned as (2, 3)
    result = file_manager.validate_page_range(
        pdf_file=io.BytesIO(b'pdf'),
        start=2,
        end=3
    )
    assert result == (2, 3)


def test_get_pdf_contents_handles_empty_page_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pages may return empty strings; get_pdf_contents should concatenate
    them without failing.
    """
    fake_texts = ['', 'Line two', '']
    monkeypatch.setattr(
        file_manager, 'PdfReader', _make_fake_pdf_reader(fake_texts)
    )

    result = file_manager.get_pdf_contents(pdf_file=io.BytesIO(b"pdf"), page_range=(1, 3))
    assert result == 'Line two'
