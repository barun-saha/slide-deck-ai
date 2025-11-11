"""
Unit tests for the icons embeddings module.
"""
import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np


def _reload_module_with_dummies(monkeypatch: Any, emb_dim: int = 4):
    """
    Reload the icons_embeddings module after monkeypatching the
    Transformers constructors to return lightweight dummy objects.

    This prevents network/download or heavy model initialization during
    tests and allows deterministic embeddings.

    Args:
        monkeypatch: The pytest monkeypatch fixture.
        emb_dim: The embedding dimensionality that the dummy model
            should produce.

    Returns:
        The reloaded module object.
    """
    class DummyTokenizer:
        def __call__(self, texts, return_tensors=None, padding=None,
                     max_length=None, truncation=None):
            if isinstance(texts, str):
                texts_list = [texts]
            else:
                texts_list = list(texts)

            return {'texts': texts_list}


    class DummyTensor:
        def __init__(self, arr: np.ndarray) -> None:
            self.arr = arr

        def mean(self, dim: int) -> 'DummyTensor':
            # Take numpy mean along the requested axis to emulate PyTorch.
            return DummyTensor(self.arr.mean(axis=dim))

        def detach(self) -> 'DummyTensor':
            return self

        def numpy(self) -> np.ndarray:
            return self.arr


    class DummyModel:
        def __call__(self, **inputs: Any) -> SimpleNamespace:
            texts = inputs.get('texts', [])
            n = len(texts)
            seq_len = 3
            arr = np.arange(n * seq_len * emb_dim, dtype=float)
            arr = arr.reshape((n, seq_len, emb_dim))
            return SimpleNamespace(last_hidden_state=DummyTensor(arr))

    monkeypatch.setattr(
        'transformers.BertTokenizer.from_pretrained',
        lambda name: DummyTokenizer(),
    )
    monkeypatch.setattr(
        'transformers.BertModel.from_pretrained',
        lambda name: DummyModel(),
    )

    if 'slidedeckai.helpers.icons_embeddings' in sys.modules:
        mod = importlib.reload(sys.modules['slidedeckai.helpers.icons_embeddings'])
    else:
        mod = importlib.import_module('slidedeckai.helpers.icons_embeddings')

    return mod


def test_get_icons_list(tmp_path: Path, monkeypatch: Any) -> None:
    """
    get_icons_list should return the stems of PNG files in the
    configured icons directory.
    """
    mod = _reload_module_with_dummies(monkeypatch)

    # Prepare a temporary icons directory with some files.
    icons_dir = tmp_path / 'icons'
    icons_dir.mkdir()
    (icons_dir / 'apple.png').write_text('x')
    (icons_dir / 'banana.png').write_text('y')
    (icons_dir / 'not_an_icon.txt').write_text('z')

    monkeypatch.setattr(mod.GlobalConfig, 'ICONS_DIR', icons_dir)

    icons = mod.get_icons_list()
    assert set(icons) == {'apple', 'banana'}


def test_get_embeddings_single_and_list(monkeypatch: Any) -> None:
    """
    get_embeddings must return numpy arrays with the expected shapes for
    single string and list inputs.
    """
    emb_dim = 5
    mod = _reload_module_with_dummies(monkeypatch, emb_dim=emb_dim)

    # Single string -> shape (1, emb_dim)
    arr1 = mod.get_embeddings('hello')
    assert isinstance(arr1, np.ndarray)
    assert arr1.shape == (1, emb_dim)

    # List of strings -> shape (3, emb_dim)
    arr2 = mod.get_embeddings(['a', 'b', 'c'])
    assert arr2.shape == (3, emb_dim)

    # Verify determinism from our dummy model for the first row.
    # The dummy model fills values with a range; mean over axis=1 reduces
    # the seq_len dimension.
    expected_first_row = np.arange(3 * emb_dim).reshape((3, emb_dim)).mean(axis=0)
    assert np.allclose(arr2[0], expected_first_row)


def test_save_and_load_embeddings(tmp_path: Path, monkeypatch: Any) -> None:
    """
    save_icons_embeddings should write embeddings and file names to the
    configured paths and load_saved_embeddings should read them back.
    """
    emb_dim = 6
    mod = _reload_module_with_dummies(monkeypatch, emb_dim=emb_dim)

    # Create icons dir with files.
    icons_dir = tmp_path / 'icons2'
    icons_dir.mkdir()
    (icons_dir / 'one.png').write_text('1')
    (icons_dir / 'two.png').write_text('2')

    monkeypatch.setattr(mod.GlobalConfig, 'ICONS_DIR', icons_dir)
    emb_file = tmp_path / 'emb.npy'
    names_file = tmp_path / 'names.npy'
    monkeypatch.setattr(mod.GlobalConfig, 'EMBEDDINGS_FILE_NAME', str(emb_file))
    monkeypatch.setattr(mod.GlobalConfig, 'ICONS_FILE_NAME', str(names_file))

    # Run save which uses the dummy tokenizer/model to create embeddings.
    mod.save_icons_embeddings()

    assert emb_file.exists()
    assert names_file.exists()

    loaded_emb, loaded_names = mod.load_saved_embeddings()
    assert isinstance(loaded_emb, np.ndarray)
    assert isinstance(loaded_names, np.ndarray)
    assert loaded_emb.shape[0] == len(loaded_names)


def test_find_icons(monkeypatch: Any, tmp_path: Path) -> None:
    """
    find_icons should map keywords to the most similar icon filenames
    based on cosine similarity against pre-saved embeddings.
    """
    # Reload module with dummy model but we will monkeypatch get_embeddings
    # to control keyword embeddings precisely.
    mod = _reload_module_with_dummies(monkeypatch, emb_dim=3)

    # Prepare saved embeddings with two icons.
    emb = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    names = np.array(['a_icon', 'b_icon'])

    emb_file = tmp_path / 'emb_s.npy'
    names_file = tmp_path / 'names_s.npy'
    np.save(str(emb_file), emb)
    np.save(str(names_file), names)

    monkeypatch.setattr(mod.GlobalConfig, 'EMBEDDINGS_FILE_NAME', str(emb_file))
    monkeypatch.setattr(mod.GlobalConfig, 'ICONS_FILE_NAME', str(names_file))

    # Make keyword embeddings match each saved one.
    def fake_get_embeddings(keywords: list[str]) -> np.ndarray:
        out = []
        for kw in keywords:
            if kw == 'match_a':
                out.append([1.0, 0.0, 0.0])
            else:
                out.append([0.0, 1.0, 0.0])
        return np.array(out)

    monkeypatch.setattr(mod, 'get_embeddings', fake_get_embeddings)

    res = mod.find_icons(['match_a', 'other'])
    assert list(res) == ['a_icon', 'b_icon']


def test_main_calls_and_prints(monkeypatch: Any, capsys: Any) -> None:
    """
    main should call save_icons_embeddings and find_icons and print the
    zipped results. We monkeypatch the heavy functions to keep it fast.
    """
    mod = _reload_module_with_dummies(monkeypatch)
    called = {}

    def fake_save():
        called['saved'] = True


    def fake_find(keywords: list[str]) -> list[str]:
        called['found'] = True
        return ['x' for _ in keywords]


    monkeypatch.setattr(mod, 'save_icons_embeddings', fake_save)
    monkeypatch.setattr(mod, 'find_icons', fake_find)

    mod.main()

    captured = capsys.readouterr()
    assert 'The relevant icon files are' in captured.out
    assert called.get('saved') is True
    assert called.get('found') is True
