"""
Search photos using Pexels API.
"""
import logging
import os
import random
import warnings
from io import BytesIO
from typing import Union, Literal
from urllib.parse import urlparse, parse_qs

import requests
from dotenv import load_dotenv


load_dotenv()


# If PEXEL_API_KEY env var is unavailable, issue a one-time warning
if not os.getenv('PEXEL_API_KEY'):
    warnings.warn(
        'PEXEL_API_KEY environment variable is not set. '
        'Image search functionality will not work without it.',
        stacklevel=2
    )

PEXELS_URL = 'https://api.pexels.com/v1/search'
REQUEST_HEADER = {
    'Authorization': os.getenv('PEXEL_API_KEY'),
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0',
}
REQUEST_TIMEOUT = 12
MAX_PHOTOS = 3


# Only show errors
logging.getLogger('urllib3').setLevel(logging.ERROR)
# Disable all child loggers of urllib3, e.g. urllib3.connectionpool
# logging.getLogger('urllib3').propagate = True


def search_pexels(
        query: str,
        size: Literal['small', 'medium', 'large'] = 'medium',
        per_page: int = MAX_PHOTOS
) -> dict:
    """
    Searches for images on Pexels using the provided query.

    This function sends a GET request to the Pexels API with the specified search query
    and authorization header containing the API key. It returns the JSON response from the API.

    [2024-08-31] Note:
    `curl` succeeds but API call via Python `requests` fail. Apparently, this could be due to
    Cloudflare (or others) blocking the requests, perhaps identifying as Web-scraping. So,
    changing the user-agent to Firefox.
    https://stackoverflow.com/a/74674276/147021
    https://stackoverflow.com/a/51268523/147021
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent/Firefox#linux

    Args:
        query: The search query for finding images.
        size: The size of the images: small, medium, or large.
        per_page: No. of results to be displayed per page.

    Returns:
        The JSON response from the Pexels API containing search results. Empty dict if API key
        is not set.

    Raises:
        requests.exceptions.RequestException: If the request to the Pexels API fails.
    """
    if not os.getenv('PEXEL_API_KEY'):
        return {}

    params = {
        'query': query,
        'size': size,
        'page': 1,
        'per_page': per_page
    }
    response = requests.get(
        PEXELS_URL,
        headers=REQUEST_HEADER,
        params=params,
        timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()  # Ensure the request was successful

    return response.json()


def get_photo_url_from_api_response(
        json_response: dict
) -> tuple[Union[str, None], Union[str, None]]:
    """
    Return a randomly chosen photo from a Pexels search API response. In addition, also return
    the original URL of the page on Pexels.

    Args:
        json_response: The JSON response.

    Returns:
        The selected photo URL and page URL or `None`. Empty tuple if no photos found or API key
        is not set.
    """
    if not os.getenv('PEXEL_API_KEY'):
        return None, None

    page_url = None
    photo_url = None

    if 'photos' in json_response:
        photos = json_response['photos']

        if photos:
            photo_idx = random.choice(list(range(MAX_PHOTOS)))
            photo = photos[photo_idx]

            if 'url' in photo:
                page_url = photo['url']

            if 'src' in photo:
                if 'large' in photo['src']:
                    photo_url = photo['src']['large']
                elif 'original' in photo['src']:
                    photo_url = photo['src']['original']

    return photo_url, page_url


def get_image_from_url(url: str) -> BytesIO:
    """
    Fetches an image from the specified URL and returns it as a BytesIO object.

    This function sends a GET request to the provided URL, retrieves the image data,
    and wraps it in a BytesIO object, which can be used like a file.

    Args:
        url: The URL of the image to be fetched.

    Returns:
        A BytesIO object containing the image data.

    Raises:
        requests.exceptions.RequestException: If the request to the URL fails.
    """
    response = requests.get(url, headers=REQUEST_HEADER, stream=True, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    image_data = BytesIO(response.content)

    return image_data


def extract_dimensions(url: str) -> tuple[int, int]:
    """
    Extracts the height and width from the URL parameters.

    Args:
        url: The URL containing the image dimensions.

    Returns:
        A tuple containing the width and height as integers.
    """
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    width = int(query_params.get('w', [0])[0])
    height = int(query_params.get('h', [0])[0])

    return width, height


if __name__ == '__main__':
    print(
        search_pexels(
            query='people'
        )
    )
