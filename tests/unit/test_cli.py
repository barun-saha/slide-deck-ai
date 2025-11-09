"""
Unit tests for the CLI of SlideDeck AI.
"""
import argparse
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Apply BertTokenizer patch before importing anything that might use it
from .test_utils import patch_bert_tokenizer

with patch('transformers.BertTokenizer', patch_bert_tokenizer()):
    from slidedeckai.cli import (
        group_models_by_provider,
        format_models_as_bullets,
        CustomArgumentParser,
        CustomHelpFormatter,
        format_models_list,
        format_model_help,
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

    # Test with empty list
    assert group_models_by_provider([]) == {}

    # Test with invalid format
    assert len(group_models_by_provider(['invalid-model'])) == 0


def test_format_models_as_bullets():
    test_models = [
        '[az]azure/open-ai',
        '[gg]gemini-2.0-flash',
        '[gg]gemini-2.0-flash-lite',
        '[to]deepseek-ai/DeepSeek-V3',
    ]

    result = format_models_as_bullets(test_models)

    assert 'anthropic:' not in result
    assert 'deepseek' in result
    assert '• [gg]gemini-2.0-flash-lite' in result

    # Test with empty list
    assert format_models_as_bullets([]) == ''

    # Test with single model
    single_result = format_models_as_bullets(['[az]model1'])
    assert '\naz:' in single_result
    assert '• [az]model1' in single_result


def test_custom_help_formatter_comprehensive():
    formatter = CustomHelpFormatter('prog')

    # Test _format_action_invocation for model argument
    action = argparse.Action(
        option_strings=['--model'],
        dest='model',
        nargs=None,
        choices=GlobalConfig.VALID_MODELS.keys()
    )
    result = formatter._format_action_invocation(action)
    assert result == '--model MODEL'

    # Test non-model argument
    other_action = argparse.Action(
        option_strings=['--topic'],
        dest='topic',
        nargs=None
    )
    other_result = formatter._format_action_invocation(other_action)
    assert 'MODEL' not in other_result

    # Test _split_lines for model choices
    text = 'Model choices:\n[az]model1\n[gg]model2'
    result = formatter._split_lines(text, 80)
    assert 'Available models:' in result
    assert '------------------------' in result
    assert any('az:' in line for line in result)

    # Test _split_lines for 'choose from' format
    choose_text = "choose from '[az]model1', '[gg]model2'"
    choose_result = formatter._split_lines(choose_text, 80)
    assert 'Available models:' in choose_result
    assert any('az:' in line for line in choose_result)

    # Test _split_lines for regular text
    regular_text = 'This is a regular text'
    regular_result = formatter._split_lines(regular_text, 80)
    assert regular_text in regular_result


def test_custom_argument_parser_error_handling():
    parser = CustomArgumentParser()
    parser.add_argument('--model', choices=['[az]model1', '[gg]model2'])

    # Test invalid model error
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.stderr'):  # Suppress stderr output
            parser.parse_args(['--model', 'invalid-model'])
    assert exc_info.value.code == 2

    # Test non-model argument error
    parser.add_argument('--topic', required=True)
    with pytest.raises(SystemExit):
        with patch('sys.stderr'):  # Suppress stderr output
            parser.parse_args(['--model', '[az]model1'])  # Missing required --topic

    # Test with no arguments
    with pytest.raises(SystemExit):
        with patch('sys.stderr'):
            parser.parse_args([])


def test_format_models_list():
    result = format_models_list()
    assert 'Supported SlideDeck AI models:' in result
    # Verify that at least one model from each provider is present
    for provider_code in ['az', 'gg']:  # Add more providers as needed
        assert any(f'[{provider_code}]' in line for line in result.split('\n'))

    # Verify structure
    lines = result.split('\n')
    assert len(lines) > 2  # Should have header and at least one model
    assert lines[0] == 'Supported SlideDeck AI models:'


def test_format_model_help():
    result = format_model_help()
    # Should have provider sections
    assert any('az:' in line for line in result.split('\n'))
    # Should contain actual model names
    assert any('[az]' in line for line in result.split('\n'))

    # Verify it uses the same format as format_models_as_bullets
    assert result == format_models_as_bullets(list(GlobalConfig.VALID_MODELS.keys()))


def test_main_no_args():
    # Test behavior when no arguments are provided
    with patch.object(sys, 'argv', ['slidedeckai']):
        with patch('argparse.ArgumentParser.print_help') as mock_print_help:
            main()
            mock_print_help.assert_called_once()

    # Test with empty args list by providing minimal argv
    with patch.object(sys, 'argv', ['script.py']):
        with patch('argparse.ArgumentParser.print_help') as mock_print_help:
            main()
            mock_print_help.assert_called_once()


def test_main_list_models():
    # Test --list-models flag
    with patch.object(sys, 'argv', ['script.py', '--list-models']):
        with patch('builtins.print') as mock_print:
            main()
            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            assert 'Supported SlideDeck AI models:' in output


@patch('slidedeckai.cli.SlideDeckAI')
@patch('shutil.move')
def test_main_generate_command(mock_move, mock_slidedeckai):
    # Mock the SlideDeckAI instance
    mock_instance = MagicMock()
    mock_instance.generate.return_value = Path('test_presentation.pptx')
    mock_slidedeckai.return_value = mock_instance

    # Test generate command
    test_args = [
        'script.py',
        'generate',
        '--model', next(iter(GlobalConfig.VALID_MODELS.keys())),
        '--topic', 'Test Topic'
    ]

    with patch.object(sys, 'argv', test_args):
        main()

    # Verify SlideDeckAI was called with correct parameters
    mock_slidedeckai.assert_called_once()
    mock_instance.generate.assert_called_once()
    mock_move.assert_not_called()  # No output path specified, no move needed


@patch('slidedeckai.cli.SlideDeckAI')
@patch('shutil.move')
def test_main_generate_with_all_options(mock_move, mock_slidedeckai):
    # Mock the SlideDeckAI instance
    mock_instance = MagicMock()
    output_path = Path('test_presentation.pptx')
    mock_instance.generate.return_value = output_path
    mock_slidedeckai.return_value = mock_instance

    test_args = [
        'script.py',
        'generate',
        '--model', next(iter(GlobalConfig.VALID_MODELS.keys())),
        '--topic', 'Test Topic',
        '--api-key', 'test-key',
        '--template-id', '1',
        '--output-path', 'output.pptx'
    ]

    with patch.object(sys, 'argv', test_args):
        main()

    # Verify SlideDeckAI was called with correct parameters
    mock_slidedeckai.assert_called_once_with(
        model=next(iter(GlobalConfig.VALID_MODELS.keys())),
        topic='Test Topic',
        api_key='test-key',
        template_idx=1
    )
    mock_instance.generate.assert_called_once_with()

    # Verify file was moved to specified output path
    mock_move.assert_called_once_with(str(output_path), 'output.pptx')


@patch('slidedeckai.cli.SlideDeckAI')
def test_main_generate_missing_required_args(mock_slidedeckai):
    # Test generate command without required arguments
    test_args = ['script.py', 'generate']

    with pytest.raises(SystemExit):
        with patch.object(sys, 'argv', test_args):
            with patch('sys.stderr'):  # Suppress stderr output
                main()

    # Verify SlideDeckAI was not called
    mock_slidedeckai.assert_not_called()

    # Test with only --model
    test_args = ['script.py', 'generate', '--model', next(iter(GlobalConfig.VALID_MODELS.keys()))]
    with pytest.raises(SystemExit):
        with patch.object(sys, 'argv', test_args):
            with patch('sys.stderr'):
                main()

    # Test with only --topic
    test_args = ['script.py', 'generate', '--topic', 'Test Topic']
    with pytest.raises(SystemExit):
        with patch.object(sys, 'argv', test_args):
            with patch('sys.stderr'):
                main()


@patch('slidedeckai.cli.SlideDeckAI')
def test_main_generate_invalid_template_id(mock_slidedeckai):
    # Mock the SlideDeckAI instance
    mock_instance = MagicMock()
    mock_slidedeckai.return_value = mock_instance
    mock_instance.generate.return_value = Path('test_presentation.pptx')

    # Test generate command with invalid template_id
    test_args = [
        'script.py',
        'generate',
        '--model', next(iter(GlobalConfig.VALID_MODELS.keys())),
        '--topic', 'Test Topic',
        '--template-id', '-1'  # Invalid template ID
    ]

    with patch.object(sys, 'argv', test_args):
        main()  # Should still work, as validation is handled by SlideDeckAI

    # Verify SlideDeckAI was called with the invalid template_id
    mock_slidedeckai.assert_called_once_with(
        model=next(iter(GlobalConfig.VALID_MODELS.keys())),
        topic='Test Topic',
        api_key=None,
        template_idx=-1
    )
    mock_instance.generate.assert_called_once_with()
