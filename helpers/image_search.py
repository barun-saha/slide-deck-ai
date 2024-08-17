"""
Search photos using Pexels API.
"""
import os
import random
from io import BytesIO
from typing import Union, Tuple, Literal
from urllib.parse import urlparse, parse_qs

import requests


REQUEST_TIMEOUT = 12
MAX_PHOTOS = 2


def search_pexels(
        query: str,
        size: Literal['small', 'medium', 'large'] = 'medium',
        per_page: int = MAX_PHOTOS
) -> dict:
    """
    Searches for images on Pexels using the provided query.

    This function sends a GET request to the Pexels API with the specified search query
    and authorization header containing the API key. It returns the JSON response from the API.

    :param query: The search query for finding images.
    :param size: The size of the images: small, medium, or large.
    :param per_page: No. of results to be displayed per page.
    :return: The JSON response from the Pexels API containing search results.
    :raises requests.exceptions.RequestException: If the request to the Pexels API fails.
    """

    url = 'https://api.pexels.com/v1/search'
    headers = {
        'Authorization': os.getenv('PEXEL_API_KEY')
    }
    params = {
        'query': query,
        'size': size,
        'page': 1,
        'per_page': per_page
    }
    response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()  # Ensure the request was successful

    return response.json()


def get_photo_url_from_api_response(
        json_response: dict
) -> Tuple[Union[str, None], Union[str, None]]:
    """
    Return a randomly chosen photo from a Pexels search API response. In addition, also return
    the original URL of the page on Pexels.

    :param json_response: The JSON response.
    :return: The selected photo URL and page URL or `None`.
    """

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

    :param url: The URL of the image to be fetched.
    :return: A BytesIO object containing the image data.
    :raises requests.exceptions.RequestException: If the request to the URL fails.
    """

    response = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    image_data = BytesIO(response.content)

    return image_data


def extract_dimensions(url: str) -> Tuple[int, int]:
    """
    Extracts the height and width from the URL parameters.

    :param url: The URL containing the image dimensions.
    :return: A tuple containing the width and height as integers.
    """
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    width = int(query_params.get('w', [0])[0])
    height = int(query_params.get('h', [0])[0])

    return width, height