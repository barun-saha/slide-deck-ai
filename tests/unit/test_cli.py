"""
Unit tests for the cli module.
"""
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

import pytest

from slidedeckai.cli import (
    group_models_by_provider,
    format_models_as_bullets,
    CustomArgumentParser,
    main
)
from slidedeckai.global_config import GlobalConfig


def test_group_models_by_provider():
    # Test with sample model names
    test_models = [
        '[az]azure/open-ai',
        '[gg]gemini-2.0-flash',
        '[gg]gemini-2.0-flash-lite',
        '[to]deepseek-ai/DeepSeek-V3',
    ]

    result = group_models_by_provider(test_models)

    assert 'an' not in result
    assert 'az' in result
    assert len(result['gg']) == 2


def test_format_models_as_bullets():
    test_models = [
        '[az]azure/open-ai',
        '[gg]gemini-2.0-flash',
        '[gg]gemini-2.0-flash-lite',
        '[to]deepseek-ai/DeepSeek-V3',
    ]

    result = format_models_as_bullets(test_models)
    print(result)

    assert 'anthropic:' not in result
    assert 'deepseek' in result
    assert '• [gg]gemini-2.0-flash-lite' in result


def test_argument_parser_model_validation():
    parser = CustomArgumentParser()
    parser.add_argument(
        '--model',
        choices=GlobalConfig.VALID_MODELS.keys()
    )

    # Test valid model
    valid_model = next(iter(GlobalConfig.VALID_MODELS.keys()))
    args = parser.parse_args(['--model', valid_model])
    assert args.model == valid_model

    # Test invalid model
    with pytest.raises(SystemExit):
        parser.parse_args(['--model', 'invalid-model'])


@patch('slidedeckai.cli.SlideDeckAI')
def test_main_generate_command(mock_slidedeckai):
    # Mock the SlideDeckAI instance
    mock_instance = MagicMock()
    mock_instance.generate.return_value = Path("test_presentation.pptx")
    mock_slidedeckai.return_value = mock_instance

    # Test generate command
    test_args = [
        'generate',
        '--model', next(iter(GlobalConfig.VALID_MODELS.keys())),
        '--topic', 'Test Topic'
    ]

    with patch.object(sys, 'argv', ['slidedeckai'] + test_args):
        main()

    # Verify SlideDeckAI was called with correct parameters
    mock_slidedeckai.assert_called_once()
    mock_instance.generate.assert_called_once()


def test_main_list_models():
    # Test --list-models flag
    with patch.object(sys, 'argv', ['slidedeckai', '--list-models']):
        with patch('builtins.print') as mock_print:
            main()
            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            assert "Supported SlideDeck AI models:" in output
