import sys
import os
from unittest.mock import MagicMock, patch
import anthropic
import pytest

# Stub out src.config before the module under test loads it
_mock_config = MagicMock()
_mock_config.ANTHROPIC_API_KEY = "test-key"
sys.modules.setdefault("src.config", _mock_config)

# Prevent the real Anthropic client from being instantiated at import time
with patch("anthropic.Anthropic"):
    import src.claude_fallback as claude_fallback


def _make_message(text: str) -> MagicMock:
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


@patch.object(claude_fallback, "_client")
class TestExtractWithClaude:
    def test_valid_json_returns_float(self, mock_client):
        mock_client.messages.create.return_value = _make_message('{"amount": 123.45}')
        assert claude_fallback.extract_with_claude("some invoice text") == pytest.approx(123.45)

    def test_null_amount_returns_none(self, mock_client):
        mock_client.messages.create.return_value = _make_message('{"amount": null}')
        assert claude_fallback.extract_with_claude("some invoice text") is None

    def test_malformed_json_returns_none(self, mock_client):
        mock_client.messages.create.return_value = _make_message("not json at all")
        assert claude_fallback.extract_with_claude("some invoice text") is None

    def test_api_timeout_returns_none(self, mock_client):
        mock_client.messages.create.side_effect = anthropic.APITimeoutError(request=MagicMock())
        assert claude_fallback.extract_with_claude("some invoice text") is None
