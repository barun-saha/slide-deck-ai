"""Unit tests for llm_helper module."""

from unittest.mock import MagicMock, patch

import pytest

from slidedeckai.global_config import GlobalConfig
from slidedeckai.helpers.llm_helper import (
    get_litellm_llm,
    get_litellm_model_name,
    get_provider_model,
    is_valid_azure_endpoint_url,
    is_valid_llm_provider_model,
    stream_litellm_completion,
)


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
            'https://test.services.ai.azure.com/openai/v1',
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
            False,
        ),
        (
            GlobalConfig.PROVIDER_AZURE_OPENAI,
            'gpt-4',
            'valid-key-12345',
            'http://127.0.0.1:9999/v1',
            'deployment1',
            '2024-02-01',
            False,
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
    'azure_endpoint_url, expected',
    [
        ('https://example.openai.azure.com/', True),
        ('https://example.services.ai.azure.com/openai/v1', True),
        ('https://example.cognitiveservices.azure.com/openai/v1', True),
        ('https://valid.azure.com', True),
        ('https://azure.com', True),
        ('http://example.openai.azure.com/', False),
        ('https://example.openai.azure.com.evil.test/', False),
        ('https://127.0.0.1:9999/v1', False),
        ('https://10.0.0.4/v1', False),
        ('https://169.254.169.254/latest/meta-data/', False),
        ('https://[::1]/v1', False),
        ('https://localhost/v1', False),
        ('https://user@example.openai.azure.com/', False),
        ('not-a-url', False),
        ('', False),
    ],
)
def test_is_valid_azure_endpoint_url(azure_endpoint_url, expected):
    """Test Azure endpoint URL validation blocks non-Azure destinations."""
    assert is_valid_azure_endpoint_url(azure_endpoint_url) is expected


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
    assert mock_litellm.completion.call_args.kwargs['api_base'] == 'https://test.azure.com'


@pytest.mark.parametrize(
    'azure_endpoint_url',
    [
        'http://127.0.0.1:9999/v1',
        'https://example.openai.azure.com.evil.test',
        'https://localhost/v1',
    ],
)
def test_stream_litellm_completion_rejects_invalid_azure_endpoint(azure_endpoint_url):
    """Test Azure calls reject endpoints that should not receive API keys."""
    messages = [{'role': 'user', 'content': 'Test'}]
    with pytest.raises(
        ValueError, match=r'Azure endpoint URL must be an HTTPS azure\.com endpoint'
    ):
        list(
            stream_litellm_completion(
                provider=GlobalConfig.PROVIDER_AZURE_OPENAI,
                model='gpt-4',
                messages=messages,
                max_tokens=100,
                api_key='valid-key-12345',
                azure_endpoint_url=azure_endpoint_url,
                azure_deployment_name='deployment1',
                azure_api_version='2024-02-01',
            )
        )


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
            list(
                stream_litellm_completion(
                    provider='co', model='command', messages=[], max_tokens=100, api_key='test-key'
                )
            )

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


def test_stream_litellm_completion_azure_missing_deployment():
    """Test that stream_litellm_completion raises ValueError when Azure deployment name is empty.

    This is the precise condition that caused the runtime error when Azure OpenAI was selected
    but credentials were not propagated through SlideDeckAI._initialize_llm().
    """
    messages = [{'role': 'user', 'content': 'Test'}]
    with pytest.raises(ValueError, match='Azure deployment name is required'):
        list(
            stream_litellm_completion(
                provider=GlobalConfig.PROVIDER_AZURE_OPENAI,
                model='gpt-4',
                messages=messages,
                max_tokens=100,
                api_key='valid-key-12345',
                azure_endpoint_url='https://test.openai.azure.com/',
                azure_deployment_name='',  # Empty — the missing credential
                azure_api_version='2024-05-01-preview',
            )
        )


@patch('slidedeckai.helpers.llm_helper.stream_litellm_completion')
def test_get_litellm_llm_azure_passes_credentials(mock_stream):
    """Test that get_litellm_llm forwards Azure credentials to stream_litellm_completion.

    Regression test: SlideDeckAI._initialize_llm() previously called get_litellm_llm()
    without Azure params, so LiteLLMWrapper was created with empty strings and the
    deployment-name check in stream_litellm_completion raised a ValueError at call time.
    """
    mock_stream.return_value = iter(['Azure response'])

    llm = get_litellm_llm(
        provider=GlobalConfig.PROVIDER_AZURE_OPENAI,
        model='gpt-4',
        max_new_tokens=100,
        api_key='valid-key-12345',
        azure_endpoint_url='https://test.openai.azure.com/',
        azure_deployment_name='my-deployment',
        azure_api_version='2024-05-01-preview',
    )

    result = list(llm.stream('Hello'))
    assert result == ['Azure response']

    mock_stream.assert_called_once_with(
        provider=GlobalConfig.PROVIDER_AZURE_OPENAI,
        model='gpt-4',
        messages=[{'role': 'user', 'content': 'Hello'}],
        max_tokens=100,
        api_key='valid-key-12345',
        azure_endpoint_url='https://test.openai.azure.com/',
        azure_deployment_name='my-deployment',
        azure_api_version='2024-05-01-preview',
    )
