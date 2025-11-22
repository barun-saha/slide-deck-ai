"""
Unit tests for the core module of SlideDeck AI.
"""
import os
from pathlib import Path
from unittest import mock
from unittest.mock import patch

import pytest

# Apply BertTokenizer patch before importing anything that might use it
from .test_utils import (
    get_mock_llm,
    get_mock_llm_response,
    MockStreamResponse,
    patch_bert_tokenizer
)

with patch('transformers.BertTokenizer', patch_bert_tokenizer()):
    from slidedeckai.core import SlideDeckAI, _process_llm_chunk, _stream_llm_response


@pytest.fixture
def mock_env():
    """Set environment variables for testing."""
    with mock.patch.dict(os.environ, {'RUN_IN_OFFLINE_MODE': 'False'}):
        yield


@pytest.fixture
def mock_temp_file():
    """Mock temporary file creation."""
    with mock.patch('slidedeckai.core.tempfile.NamedTemporaryFile') as mock_temp:
        mock_temp.return_value.name = 'temp.pptx'
        yield mock_temp


@pytest.fixture
def slide_deck_ai():
    """Fixture to create a SlideDeckAI instance."""
    return SlideDeckAI(
        model='[or]openai/gpt-3.5-turbo',
        topic='Test Topic',
        api_key='dummy-key'
    )


def test_process_llm_chunk_string():
    """Test processing string chunk."""
    chunk = 'test chunk'
    assert _process_llm_chunk(chunk) == 'test chunk'


def test_process_llm_chunk_object():
    """Test processing object chunk with content."""
    chunk = MockStreamResponse('test content')
    assert _process_llm_chunk(chunk) == 'test content'


@mock.patch('slidedeckai.core.llm_helper')
def test_stream_llm_response(mock_llm_helper):
    """Test streaming LLM response."""
    mock_llm = get_mock_llm()
    response = _stream_llm_response(mock_llm, 'test prompt')
    assert response == get_mock_llm_response()


@mock.patch('slidedeckai.core.llm_helper')
def test_stream_llm_response_with_callback(mock_llm_helper):
    """Test streaming LLM response with progress callback."""
    mock_llm = get_mock_llm()
    progress_values = []

    def progress_callback(value):
        progress_values.append(value)

    response = _stream_llm_response(mock_llm, 'test prompt', progress_callback)
    assert response == get_mock_llm_response()
    assert len(progress_values) > 0


def test_slide_deck_ai_init_invalid_model():
    """Test SlideDeckAI initialization with invalid model."""
    with pytest.raises(ValueError) as exc_info:
        SlideDeckAI(model='clearly-invalid-model-name', topic='test')
    assert 'Invalid model name' in str(exc_info.value)


def test_slide_deck_ai_init_valid(slide_deck_ai):
    """Test SlideDeckAI initialization with valid parameters."""
    assert slide_deck_ai.model == '[or]openai/gpt-3.5-turbo'
    assert slide_deck_ai.topic == 'Test Topic'
    assert slide_deck_ai.template_idx == 0


@mock.patch.dict(
    'slidedeckai.core.GlobalConfig.VALID_MODELS',
    {
        '[or]openai/gpt-3.5-turbo': ('openai', 'gpt-3.5-turbo'),
        'new-valid-model': ('openai', 'gpt-test')
    }
)
def test_set_model_valid_updates_model(slide_deck_ai) -> None:
    """Test that set_model updates the model name and keeps api_key when
    no new api_key is provided.

    This test patches GlobalConfig.VALID_MODELS to a small controlled set so
    model validation is deterministic.
    """
    original_api_key = slide_deck_ai.api_key

    slide_deck_ai.set_model('new-valid-model')

    assert slide_deck_ai.model == 'new-valid-model'
    assert slide_deck_ai.api_key == original_api_key


@mock.patch.dict(
    'slidedeckai.core.GlobalConfig.VALID_MODELS',
    {
        '[or]openai/gpt-3.5-turbo': ('openai', 'gpt-3.5-turbo'),
        'new-valid-model': ('openai', 'gpt-test')
    }
)
def test_set_model_valid_updates_api_key(slide_deck_ai) -> None:
    """Test that set_model updates both the model name and the api_key when
    an api_key is provided explicitly.
    """
    slide_deck_ai.set_model('new-valid-model', api_key='new-key')

    assert slide_deck_ai.model == 'new-valid-model'
    assert slide_deck_ai.api_key == 'new-key'


def test_set_model_invalid_raises(slide_deck_ai) -> None:
    """Test that set_model raises ValueError for an invalid model name."""
    with pytest.raises(ValueError) as exc_info:
        slide_deck_ai.set_model('clearly-invalid-model-name')
    assert 'Invalid model name' in str(exc_info.value)


@mock.patch('slidedeckai.core.llm_helper.get_provider_model')
@mock.patch('slidedeckai.core.llm_helper.get_litellm_llm')
def test_generate_slide_deck(mock_get_llm, mock_get_provider, mock_temp_file, slide_deck_ai):
    """Test generating a slide deck."""
    # Setup mocks
    mock_get_provider.return_value = ('openai', 'gpt-3.5-turbo')
    mock_get_llm.return_value = get_mock_llm()

    result = slide_deck_ai.generate()
    assert isinstance(result, Path)
    assert str(result).endswith('.pptx')


@mock.patch('slidedeckai.core.llm_helper.get_provider_model')
@mock.patch('slidedeckai.core.llm_helper.get_litellm_llm')
def test_slide_deck(mock_get_llm, mock_get_provider, mock_temp_file, slide_deck_ai):
    """Test revising a slide deck."""
    # Setup mocks
    mock_get_provider.return_value = ('openai', 'gpt-3.5-turbo')
    mock_get_llm.return_value = get_mock_llm()

    # First generate initial deck
    slide_deck_ai.generate()

    # Then test revision
    result = slide_deck_ai.revise('Make it better')
    assert isinstance(result, Path)
    assert str(result).endswith('.pptx')


def test_revise_without_generate(slide_deck_ai):
    """Test revising without generating first."""
    with pytest.raises(ValueError) as exc_info:
        slide_deck_ai.revise('Make it better')
    assert 'You must generate a slide deck before you can revise it' in str(exc_info.value)


def test_set_template(slide_deck_ai):
    """Test setting template index."""
    slide_deck_ai.set_template(1)
    assert slide_deck_ai.template_idx == 1
    # Test invalid index
    slide_deck_ai.set_template(999)
    assert slide_deck_ai.template_idx == 0


def test_reset(slide_deck_ai):
    """Test resetting the slide deck state."""
    slide_deck_ai.template_idx = 1
    slide_deck_ai.last_response = 'test'
    slide_deck_ai.reset()
    assert slide_deck_ai.template_idx == 0
    assert slide_deck_ai.last_response is None
    assert len(slide_deck_ai.chat_history.messages) == 0


@mock.patch('slidedeckai.core.llm_helper.get_provider_model')
@mock.patch('slidedeckai.core.llm_helper.get_litellm_llm')
def test_get_prompt_template(mock_get_llm, mock_get_provider, slide_deck_ai):
    """Test getting prompt templates."""
    initial_template = slide_deck_ai._get_prompt_template(is_refinement=False)
    refinement_template = slide_deck_ai._get_prompt_template(is_refinement=True)

    assert isinstance(initial_template, str)
    assert isinstance(refinement_template, str)
    assert initial_template != refinement_template


@mock.patch('slidedeckai.core.llm_helper.get_provider_model')
@mock.patch('slidedeckai.core.llm_helper.get_litellm_llm')
def test_generate_with_pdf(mock_get_llm, mock_get_provider, slide_deck_ai):
    """Test generating a slide deck with PDF input."""
    mock_get_provider.return_value = ('openai', 'gpt-3.5-turbo')
    mock_get_llm.return_value = get_mock_llm()

    with mock.patch('slidedeckai.core.filem.get_pdf_contents') as mock_pdf:
        mock_pdf.return_value = 'PDF content'
        slide_deck_ai.pdf_path_or_stream = 'test.pdf'
        with mock.patch('slidedeckai.core.tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.name = 'temp.pptx'
            result = slide_deck_ai.generate()
            assert isinstance(result, Path)
            mock_pdf.assert_called_once()


def test_chat_history_limit(slide_deck_ai):
    """Test chat history limit in revise method."""
    # Fill up chat history
    for i in range(8):
        slide_deck_ai.chat_history.add_user_message(f'User message {i}')
        slide_deck_ai.chat_history.add_ai_message(f'AI message {i}')

    slide_deck_ai.last_response = 'Previous response'

    with pytest.raises(ValueError) as exc_info:
        slide_deck_ai.revise('One more message')
    assert 'Chat history is full' in str(exc_info.value)


@mock.patch('slidedeckai.core.json5.loads')
def test_generate_slide_deck_json_error(mock_json_loads, slide_deck_ai):
    """Test _generate_slide_deck with JSON parsing error."""
    mock_json_loads.side_effect = [ValueError('Bad JSON'), {'slides': []}]

    with mock.patch('slidedeckai.core.tempfile.NamedTemporaryFile') as mock_temp:
        mock_temp.return_value.name = 'temp.pptx'
        result = slide_deck_ai._generate_slide_deck('{"bad": "json"}')
        assert result is not None
        assert mock_json_loads.call_count == 2


@mock.patch('slidedeckai.core.json5.loads')
def test_generate_slide_deck_unrecoverable_json_error(mock_json_loads, slide_deck_ai):
    """Test _generate_slide_deck with unrecoverable JSON error."""
    mock_json_loads.side_effect = ValueError('Bad JSON')

    result = slide_deck_ai._generate_slide_deck('{"bad": "json"}')
    assert result is None


@mock.patch('slidedeckai.core.pptx_helper.generate_powerpoint_presentation')
@mock.patch('slidedeckai.core.json5.loads')
def test_generate_slide_deck_pptx_error(mock_json_loads, mock_generate_pptx, slide_deck_ai):
    """Test _generate_slide_deck with PowerPoint generation error."""
    mock_json_loads.return_value = {'slides': []}
    mock_generate_pptx.side_effect = Exception('PowerPoint error')

    with mock.patch('slidedeckai.core.tempfile.NamedTemporaryFile') as mock_temp:
        mock_temp.return_value.name = 'temp.pptx'
        result = slide_deck_ai._generate_slide_deck('{"slides": []}')
        assert result is None


def test_stream_llm_response_error():
    """Test _stream_llm_response error handling."""
    mock_llm = mock.Mock()
    mock_llm.stream.side_effect = Exception('LLM error')

    with pytest.raises(RuntimeError) as exc_info:
        _stream_llm_response(mock_llm, 'test prompt')
    assert "Failed to get response from LLM" in str(exc_info.value)


@mock.patch('slidedeckai.core.llm_helper.get_provider_model')
@mock.patch('slidedeckai.core.llm_helper.get_litellm_llm')
def test_initialize_llm(mock_get_llm, mock_get_provider, slide_deck_ai):
    """Test _initialize_llm method."""
    mock_get_provider.return_value = ('openai', 'gpt-3.5-turbo')
    mock_get_llm.return_value = get_mock_llm()

    llm = slide_deck_ai._initialize_llm()
    assert llm is not None
    mock_get_provider.assert_called_once()
    mock_get_llm.assert_called_once()


def test_topic_reset(slide_deck_ai):
    """Test that topic is retained after reset."""
    slide_deck_ai.reset()
    assert slide_deck_ai.topic == ''
