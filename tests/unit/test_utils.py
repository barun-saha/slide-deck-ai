"""
Common test utilities and mocks for unit tests.
"""
from unittest.mock import MagicMock


class MockBertTokenizer:
    """
    A mock for transformers.BertTokenizer for testing purposes.
    """
    def __init__(self, *args, **kwargs):
        """Initialize the mock tokenizer."""
        self.vocab = {"[PAD]": 0, "[UNK]": 1}
        self.model_max_length = 512

    def encode(self, text, add_special_tokens=True, truncation=True, max_length=None):
        """
        Mock encode method to convert text to token IDs.
        """
        # Return some dummy token IDs
        return [1, 2, 3]

    def decode(self, token_ids, skip_special_tokens=True):
        """
        Mock decode method to convert token IDs back to text.
        """
        # Return dummy text
        return 'decoded text'

    def __call__(self, text, padding=True, truncation=True, max_length=None, return_tensors=None):
        """
        Mock call method to simulate tokenization.
        """
        return {
            'input_ids': [[1, 2, 3]],
            'attention_mask': [[1, 1, 1]]
        }


def patch_bert_tokenizer():
    """
    Returns a mock for transformers.BertTokenizer
    """
    mock_tokenizer = MagicMock()
    mock_tokenizer.from_pretrained = MagicMock(return_value=MockBertTokenizer())
    return mock_tokenizer


def get_mock_llm_response():
    """
    Returns a mock LLM response for testing
    """
    return '''
    {
        "title": "Test Presentation",
        "slides": [
            {
                "title": "Test Slide 1",
                "content": "Test content",
                "layout": "text_only"
            }
        ]
    }
    '''


class MockStreamResponse:
    """
    A mock class to simulate streaming responses from an LLM.
    """
    def __init__(self, content):
        self.content = content

    def __iter__(self):
        yield self


def get_mock_llm():
    """
    Returns a mock LLM instance for testing
    """
    mock_llm = MagicMock()
    mock_llm.stream.return_value = [MockStreamResponse(get_mock_llm_response())]

    return mock_llm
