"""
Generate and save the embeddings of a pre-defined list of icons.
Compare them with keywords embeddings to find most relevant icons.
"""
from typing import Union

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from transformers import BertTokenizer, BertModel

from ..global_config import GlobalConfig


tokenizer = BertTokenizer.from_pretrained(GlobalConfig.TINY_BERT_MODEL)
model = BertModel.from_pretrained(GlobalConfig.TINY_BERT_MODEL)


def get_icons_list() -> list[str]:
    """
    Get a list of available icons.

    Returns:
        The icons file names.
    """
    items = GlobalConfig.ICONS_DIR.glob('*.png')
    items = [item.stem for item in items]

    return items


def get_embeddings(texts: Union[str, list[str]]) -> np.ndarray:
    """
    Generate embeddings for a list of texts using a pre-trained language model.

    Args:
        texts: A string or a list of strings to be converted into embeddings.

    Returns:
        A NumPy array containing the embeddings for the input texts.

    Raises:
        ValueError: If the input is not a string or a list of strings, or if any element
         in the list is not a string.

    Example usage:
    >>> keyword = 'neural network'
    >>> file_names = ['neural_network_icon.png', 'data_analysis_icon.png', 'machine_learning.png']
    >>> keyword_embeddings = get_embeddings(keyword)
    >>> file_name_embeddings = get_embeddings(file_names)
    """
    inputs = tokenizer(texts, return_tensors='pt', padding=True, max_length=128, truncation=True)
    outputs = model(**inputs)

    return outputs.last_hidden_state.mean(dim=1).detach().numpy()


def save_icons_embeddings():
    """
    Generate and save the embeddings for the icon file names.
    """
    file_names = get_icons_list()
    print(f'{len(file_names)} icon files available...')
    file_name_embeddings = get_embeddings(file_names)
    print(f'file_name_embeddings.shape: {file_name_embeddings.shape}')

    # Save embeddings to a file
    np.save(GlobalConfig.EMBEDDINGS_FILE_NAME, file_name_embeddings)
    np.save(GlobalConfig.ICONS_FILE_NAME, file_names)  # Save file names for reference


def load_saved_embeddings() -> tuple[np.ndarray, np.ndarray]:
    """
    Load precomputed embeddings and icons file names.

    Returns:
        The embeddings and the icon file names.
    """
    file_name_embeddings = np.load(GlobalConfig.EMBEDDINGS_FILE_NAME)
    file_names = np.load(GlobalConfig.ICONS_FILE_NAME)

    return file_name_embeddings, file_names


def find_icons(keywords: list[str]) -> list[str]:
    """
    Find relevant icon file names for a list of keywords.

    Args:
        keywords: The list of one or more keywords.

    Returns:
        A list of the file names relevant for each keyword.
    """
    keyword_embeddings = get_embeddings(keywords)
    file_name_embeddings, file_names = load_saved_embeddings()

    # Compute similarity
    similarities = cosine_similarity(keyword_embeddings, file_name_embeddings)
    icon_files = file_names[np.argmax(similarities, axis=-1)]

    return icon_files


def main():
    """
    Example usage.
    """
    # Run this again if icons are to be added/removed
    save_icons_embeddings()

    keywords = [
        'deep learning',
        '',
        'recycling',
        'handshake',
        'Ferry',
        'rain drop',
        'speech bubble',
        'mental resilience',
        'turmeric',
        'Art',
        'price tag',
        'Oxygen',
        'oxygen',
        'Social Connection',
        'Accomplishment',
        'Python',
        'XML',
        'Handshake',
    ]
    icon_files = find_icons(keywords)
    print(
        f'The relevant icon files are:\n'
        f'{list(zip(keywords, icon_files))}'
    )

    # BERT tiny:
    # [('deep learning', 'deep-learning'), ('', '123'), ('recycling', 'refinery'),
    #  ('handshake', 'dash-circle'), ('Ferry', 'cart'), ('rain drop', 'bucket'),
    #  ('speech bubble', 'globe'), ('mental resilience', 'exclamation-triangle'),
    #  ('turmeric', 'kebab'), ('Art', 'display'), ('price tag', 'bug-fill'),
    #  ('Oxygen', 'radioactive')]

    # BERT mini
    # [('deep learning', 'deep-learning'), ('', 'compass'), ('recycling', 'tools'),
    #  ('handshake', 'bandaid'), ('Ferry', 'cart'), ('rain drop', 'trash'),
    #  ('speech bubble', 'image'), ('mental resilience', 'recycle'), ('turmeric', 'linkedin'),
    #  ('Art', 'book'), ('price tag', 'card-image'), ('Oxygen', 'radioactive')]

    # BERT small
    # [('deep learning', 'deep-learning'), ('', 'gem'), ('recycling', 'tools'),
    #  ('handshake', 'handbag'), ('Ferry', 'truck'), ('rain drop', 'bucket'),
    #  ('speech bubble', 'strategy'), ('mental resilience', 'deep-learning'),
    #  ('turmeric', 'flower'),
    #  ('Art', 'book'), ('price tag', 'hotdog'), ('Oxygen', 'radioactive')]


if __name__ == '__main__':
    main()
