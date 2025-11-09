"""
Pytest configuration file.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from .test_utils import patch_bert_tokenizer

# Add the src directory to Python path for importing slidedeckai
src_path = Path(__file__).parent.parent.parent / 'src'
sys.path.insert(0, str(src_path))


@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock dependencies to prevent network calls during tests"""
    with patch(
            'transformers.BertTokenizer', new=patch_bert_tokenizer()
    ), patch('slidedeckai.core.pptx_helper', autospec=True):
        yield

@pytest.fixture(autouse=True)
def mock_env_vars():
    """Set environment variables for testing"""
    with patch.dict('os.environ', {'RUN_IN_OFFLINE_MODE': 'False'}):
        yield

@pytest.fixture
def mock_temp_file():
    """Create a mock temporary file"""
    mock_temp = MagicMock()
    mock_temp.name = 'test.pptx'
    with patch('tempfile.NamedTemporaryFile', return_value=mock_temp):
        yield mock_temp
