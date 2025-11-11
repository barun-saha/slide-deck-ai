"""
Unit tests text helper.
"""
import importlib

# Now import the module under test
text_helper = importlib.import_module('slidedeckai.helpers.text_helper')


def test_is_valid_prompt_valid() -> None:
    """Test that a valid prompt returns True.

    A valid prompt must be at least 7 characters long and contain a space.
    """
    assert text_helper.is_valid_prompt('Hello world') is True


def test_is_valid_prompt_invalid_short() -> None:
    """Test that a too-short prompt returns False."""
    assert text_helper.is_valid_prompt('short') is False


def test_is_valid_prompt_invalid_no_space() -> None:
    """Test that a long prompt without a space returns False."""
    assert text_helper.is_valid_prompt('longwordwithnospaces') is False


def test_get_clean_json_with_backticks() -> None:
    """Test cleaning a JSON string wrapped in ```json ... ``` fences."""
    inp = '```json{"key":"value"}```'
    out = text_helper.get_clean_json(inp)
    assert out == '{"key":"value"}'


def test_get_clean_json_with_extra_text() -> None:
    """Test cleaning where extra text follows the closing fence."""
    inp = '```json{"k": 1}``` some extra text'
    out = text_helper.get_clean_json(inp)
    assert out == '{"k": 1}'


def test_get_clean_json_no_fences() -> None:
    """When no fences are present the original string should be returned."""
    inp = '{"plain": true}'
    out = text_helper.get_clean_json(inp)
    assert out == inp


def test_get_clean_json_irrelevant_fence() -> None:
    """If fences are present but not enclosing JSON the original should be preserved.
    """
    inp = 'some text ```not json``` more text'
    out = text_helper.get_clean_json(inp)
    assert out == inp


def test_fix_malformed_json_uses_json_repair() -> None:
    """Ensure fix_malformed_json delegates to json_repair.repair_json."""
    sample = '{bad: json}'
    repaired = text_helper.fix_malformed_json(sample)
    assert repaired == '{"bad": "json"}'
