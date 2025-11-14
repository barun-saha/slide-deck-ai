"""
Unit tests for llm_helper module.
"""
from unittest.mock import patch, MagicMock

import pytest

from slidedeckai.helpers.llm_helper import (
    get_provider_model,
    is_valid_llm_provider_model,
    get_litellm_model_name,
    stream_litellm_completion,
    get_litellm_llm,
)
from slidedeckai.global_config import GlobalConfig


@pytest.mark.parametrize(
    'provider_model, use_ollama, expected',
    [
        ('[co]command', False, ('co', 'command')),
        ('[gg]gemini-pro', False, ('gg', 'gemini-pro')),
        ('[or]gpt-4', False, ('or', 'gpt-4')),
        ('mistral', True, (GlobalConfig.PROVIDER_OLLAMA, 'mistral')),
        ('llama2', True, (GlobalConfig.PROVIDER_OLLAMA, 'llama2')),
        ('invalid[]model', False, ('', '')),
        ('', False, ('', '')),
        ('[invalid]model', False, ('', '')),
    ],
)
def test_get_provider_model(provider_model, use_ollama, expected):
    """Test get_provider_model with various inputs."""
    result = get_provider_model(provider_model, use_ollama)
    assert result == expected


@pytest.mark.parametrize(
    (
            'provider, model, api_key, azure_endpoint_url,'
            ' azure_deployment_name, azure_api_version, expected'
    ),
    [
        # Valid non-Azure cases
        ('co', 'command', 'valid-key-12345', '', '', '', True),
        ('gg', 'gemini-pro', 'valid-key-12345', '', '', '', True),
        ('or', 'gpt-4', 'valid-key-12345', '', '', '', True),
        # Invalid cases
        ('', 'model', 'key', '', '', '', False),
        ('invalid', 'model', 'key', '', '', '', False),
        ('co', '', 'key', '', '', '', False),
        ('co', 'model', '', '', '', '', False),
        ('co', 'model', 'short', '', '', '', False),
        # Ollama cases (no API key needed)
        (GlobalConfig.PROVIDER_OLLAMA, 'llama2', '', '', '', '', True),
        # Azure cases
        (
            GlobalConfig.PROVIDER_AZURE_OPENAI,
            'gpt-4',
            'valid-key-12345',
            'https://valid.azure.com',
            'deployment1',
            '2024-02-01',
            True,
        ),
        (
            GlobalConfig.PROVIDER_AZURE_OPENAI,
            'gpt-4',
            'valid-key-12345',
            'https://invalid-url',
            'deployment1',
            '2024-02-01',
            True,  # URL validation is not done
        ),
        (
            GlobalConfig.PROVIDER_AZURE_OPENAI,
            'gpt-4',
            'valid-key-12345',
            'https://valid.azure.com',
            '',
            '2024-02-01',
            False,
        ),
    ],
)
def test_is_valid_llm_provider_model(
    provider,
    model,
    api_key,
    azure_endpoint_url,
    azure_deployment_name,
    azure_api_version,
    expected,
):
    """Test is_valid_llm_provider_model with various inputs."""
    result = is_valid_llm_provider_model(
        provider,
        model,
        api_key,
        azure_endpoint_url,
        azure_deployment_name,
        azure_api_version,
    )
    assert result == expected


@pytest.mark.parametrize(
    'provider, model, expected',
    [
        (GlobalConfig.PROVIDER_GOOGLE_GEMINI, 'gemini-pro', 'gemini/gemini-pro'),
        (GlobalConfig.PROVIDER_OPENROUTER, 'openai/gpt-4', 'openrouter/openai/gpt-4'),
        (GlobalConfig.PROVIDER_COHERE, 'command', 'cohere/command'),
        (GlobalConfig.PROVIDER_TOGETHER_AI, 'llama2', 'together_ai/llama2'),
        (GlobalConfig.PROVIDER_OLLAMA, 'mistral', 'ollama/mistral'),
        ('invalid', 'model', None),
    ],
)
def test_get_litellm_model_name(provider, model, expected):
    """Test get_litellm_model_name with various providers and models."""
    result = get_litellm_model_name(provider, model)
    assert result == expected


@patch('slidedeckai.helpers.llm_helper.litellm')
def test_stream_litellm_completion_success(mock_litellm):
    """Test successful streaming completion."""
    # Mock response chunks
    mock_chunk1 = MagicMock()
    mock_chunk1.choices = [
        MagicMock(delta=MagicMock(content='Hello')),
    ]
    mock_chunk2 = MagicMock()
    mock_chunk2.choices = [
        MagicMock(delta=MagicMock(content=' world')),
    ]
    mock_litellm.completion.return_value = [mock_chunk1, mock_chunk2]

    messages = [{'role': 'user', 'content': 'Say hello'}]
    result = list(
        stream_litellm_completion(
            provider='gg',
            model='gemini-2.5-flash-lite',
            messages=messages,
            max_tokens=100,
            api_key='test-key',
        )
    )

    assert result == ['Hello', ' world']
    mock_litellm.completion.assert_called_once()


@patch('slidedeckai.helpers.llm_helper.litellm')
def test_stream_litellm_completion_azure(mock_litellm):
    """Test streaming completion with Azure OpenAI."""
    mock_chunk = MagicMock()
    mock_chunk.choices = [
        MagicMock(delta=MagicMock(content='Response')),
    ]
    mock_litellm.completion.return_value = [mock_chunk]

    messages = [{'role': 'user', 'content': 'Test'}]
    result = list(
        stream_litellm_completion(
            provider=GlobalConfig.PROVIDER_AZURE_OPENAI,
            model='gpt-4',
            messages=messages,
            max_tokens=100,
            api_key='test-key',
            azure_endpoint_url='https://test.azure.com',
            azure_deployment_name='deployment1',
            azure_api_version='2024-02-01',
        )
    )

    assert result == ['Response']
    mock_litellm.completion.assert_called_once()


@patch('slidedeckai.helpers.llm_helper.litellm')
def test_stream_litellm_completion_error(mock_litellm):
    """Test error handling in streaming completion."""
    mock_litellm.completion.side_effect = Exception('API Error')

    messages = [{'role': 'user', 'content': 'Test'}]
    with pytest.raises(Exception) as exc_info:
        list(
            stream_litellm_completion(
                provider='gg',
                model='gemini-2.5-flash-lite',
                messages=messages,
                max_tokens=100,
                api_key='test-key',
            )
        )
    assert str(exc_info.value) == 'API Error'


@patch('slidedeckai.helpers.llm_helper.stream_litellm_completion')
def test_get_litellm_llm(mock_stream):
    """Test LiteLLM wrapper creation and streaming."""
    mock_stream.return_value = iter(['Hello', ' world'])

    llm = get_litellm_llm(
        provider='gg',
        model='gemini-2.5-flash-lite',
        max_new_tokens=100,
        api_key='test-key',
    )

    result = list(llm.stream('Say hello'))
    assert result == ['Hello', ' world']
    mock_stream.assert_called_once()


def test_litellm_not_installed():
    """Test behavior when LiteLLM is not installed."""
    with patch('slidedeckai.helpers.llm_helper.litellm', None) as mock_litellm:
        from slidedeckai.helpers.llm_helper import stream_litellm_completion

        with pytest.raises(ImportError) as exc_info:
            # Try to use stream_litellm_completion which requires LiteLLM
            list(stream_litellm_completion(
                provider='co',
                model='command',
                messages=[],
                max_tokens=100,
                api_key='test-key'
            ))

    assert 'LiteLLM is not installed' in str(exc_info.value)


@patch('slidedeckai.helpers.llm_helper.litellm')
def test_stream_litellm_completion_message_format(mock_litellm):
    """Test handling different message format in streaming response."""
    # Test message format instead of delta format
    mock_chunk = MagicMock()
    mock_delta = MagicMock()
    mock_delta.content = None  # First chunk has no content
    mock_choices = [MagicMock(delta=mock_delta)]
    mock_chunk.choices = mock_choices

    # Second chunk with content
    mock_chunk2 = MagicMock()
    mock_delta2 = MagicMock()
    mock_delta2.content = 'Alternative format'
    mock_choices2 = [MagicMock(delta=mock_delta2)]
    mock_chunk2.choices = mock_choices2

    mock_litellm.completion.return_value = [mock_chunk, mock_chunk2]

    messages = [{'role': 'user', 'content': 'Test'}]
    result = list(
        stream_litellm_completion(
            provider='gg',
            model='gemini-2.5-flash-lite',
            messages=messages,
            max_tokens=100,
            api_key='test-key',
        )
    )

    assert result == ['Alternative format']
    mock_litellm.completion.assert_called_once()
