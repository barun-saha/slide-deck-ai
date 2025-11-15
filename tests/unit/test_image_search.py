"""
Tests for the image search module.
"""
from io import BytesIO
from typing import Any, Dict

import pytest

from slidedeckai.helpers import image_search


class _MockResponse:
    """A tiny response-like object to simulate `requests` responses."""

    def __init__(
            self,
            *,
            content: bytes = b'',
            json_data: Any = None,
            status_ok: bool = True
    ) -> None:
        self.content = content
        self._json = json_data
        self._status_ok = status_ok

    def raise_for_status(self) -> None:
        """Raise an exception when status is not OK."""

        if not self._status_ok:
            raise RuntimeError('status not ok')

    def json(self) -> Any:
        """Return preconfigured JSON data."""

        return self._json


def _dummy_requests_get_success_search(
        url: str,
        headers: Dict[str, str],
        params: Dict[str, Any],
        timeout: int
):
    """Return a successful mock response for search_pexels."""
    # Validate that the function under test passes expected args
    assert 'Authorization' in headers
    assert 'User-Agent' in headers
    assert 'query' in params

    photos = [
        {
            'url': 'https://pexels.com/photo/1',
            'src': {'large': 'https://images/1_large.jpg'}
        },
        {
            'url': 'https://pexels.com/photo/2',
            'src': {'original': 'https://images/2_original.jpg'}
        },
        {
            'url': 'https://pexels.com/photo/3',
            'src': {'large': 'https://images/3_large.jpg'}
        }
    ]

    return _MockResponse(json_data={'photos': photos})


def _dummy_requests_get_image(
        url: str,
        headers: Dict[str, str],
        stream: bool, timeout: int
):
    """Return a mock image response for get_image_from_url."""
    assert stream is True
    assert 'Authorization' in headers
    data = b'\x89PNG\r\n\x1a\n...'

    return _MockResponse(content=data)


def test_extract_dimensions_with_params() -> None:
    """Extract_dimensions extracts width and height from URL query params."""
    url = 'https://images.example.com/photo.jpg?w=800&h=600'
    width, height = image_search.extract_dimensions(url)

    assert isinstance(width, int)
    assert isinstance(height, int)
    assert (width, height) == (800, 600)


def test_extract_dimensions_missing_params() -> None:
    """When dimensions are missing the function returns (0, 0)."""
    url = 'https://images.example.com/photo.jpg'
    assert image_search.extract_dimensions(url) == (0, 0)


def test_get_photo_url_from_api_response_none() -> None:
    """Returns (None, None) when there are no photos in the response."""
    result = image_search.get_photo_url_from_api_response({'not_photos': []})
    assert result == (None, None)


def test_get_photo_url_from_api_response_selects_large_and_original(monkeypatch) -> None:
    """Ensure the function picks the expected photo and returns correct URLs.

    This test patches random.choice to deterministically pick indices that exercise
    the 'large' and 'original' branches.
    """
    photos = [
        {'url': 'https://pexels.com/photo/1', 'src': {'large': 'https://images/1_large.jpg'}},
        {'url': 'https://pexels.com/photo/2', 'src': {'original': 'https://images/2_original.jpg'}},
        {'url': 'https://pexels.com/photo/3', 'src': {'large': 'https://images/3_large.jpg'}},
    ]

    # Ensure the Pexels API key is present so the helper will attempt to select
    # and return photo URLs rather than early-returning (None, None).
    monkeypatch.setenv('PEXEL_API_KEY', 'akey')

    # Force selection of index 1 (second photo) which only has 'original'
    monkeypatch.setattr(image_search.random, 'choice', lambda seq: 1)

    photo_url, page_url = image_search.get_photo_url_from_api_response({'photos': photos})

    assert page_url == 'https://pexels.com/photo/2'
    assert photo_url == 'https://images/2_original.jpg'

    # Force selection of index 0 which has 'large'
    monkeypatch.setattr(image_search.random, 'choice', lambda seq: 0)

    photo_url, page_url = image_search.get_photo_url_from_api_response({'photos': photos})

    assert page_url == 'https://pexels.com/photo/1'
    assert photo_url == 'https://images/1_large.jpg'


def test_get_image_from_url_success(monkeypatch) -> None:
    """get_image_from_url returns a BytesIO object with image content."""
    monkeypatch.setattr(
        'slidedeckai.helpers.image_search.requests.get',
        lambda *a, **k: _dummy_requests_get_image(*a, **k)
    )
    monkeypatch.setenv('PEXEL_API_KEY', 'dummykey')
    img = image_search.get_image_from_url('https://images/1_large.jpg')

    assert isinstance(img, BytesIO)
    data = img.getvalue()
    assert data.startswith(b'\x89PNG')


def test_search_pexels_success(monkeypatch) -> None:
    """search_pexels forwards the request and returns parsed JSON."""
    monkeypatch.setattr(
        'slidedeckai.helpers.image_search.requests.get',
        lambda *a, **k: _dummy_requests_get_success_search(*a, **k)
    )
    monkeypatch.setenv('PEXEL_API_KEY', 'akey')
    result = image_search.search_pexels(query='people', size='medium', per_page=3)

    assert isinstance(result, dict)
    assert 'photos' in result
    assert len(result['photos']) == 3


def test_search_pexels_raises_on_request_error(monkeypatch) -> None:
    """When requests.get raises an exception, it should propagate from search_pexels."""
    def _raise(*a, **k):
        raise RuntimeError('network')

    monkeypatch.setattr('slidedeckai.helpers.image_search.requests.get', _raise)
    monkeypatch.setenv('PEXEL_API_KEY', 'akey')

    with pytest.raises(RuntimeError):
        image_search.search_pexels(query='x')


def test_search_pexels_returns_empty_when_no_api_key(monkeypatch) -> None:
    """When PEXEL_API_KEY is not set, search_pexels should return an empty dict."""
    monkeypatch.delenv('PEXEL_API_KEY', raising=False)
    result = image_search.search_pexels(query='people')

    assert result == {}


def test_get_photo_url_from_api_response_returns_none_when_no_api_key(monkeypatch) -> None:
    """When PEXEL_API_KEY is not set, get_photo_url_from_api_response should return (None, None)."""
    photos = [
        {'url': 'https://pexels.com/photo/1', 'src': {'large': 'https://images/1_large.jpg'}}
    ]
    monkeypatch.delenv('PEXEL_API_KEY', raising=False)
    result = image_search.get_photo_url_from_api_response({'photos': photos})

    assert result == (None, None)
