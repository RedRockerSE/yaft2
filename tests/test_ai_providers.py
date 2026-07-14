"""
Tests for LLM provider implementations and the provider factory.

Tests OpenAICompatibleProvider (used for Ollama and other OpenAI-compatible
backends) with mocked HTTP calls, and build_provider()'s disabled/
not-implemented error paths.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from yaft.ai.exceptions import (
    AIFeatureDisabledError,
    AIProviderError,
    AIProviderNotImplementedError,
)
from yaft.ai.factory import build_provider
from yaft.ai.providers.base import LLMResult
from yaft.ai.providers.openai_compatible import OpenAICompatibleProvider
from yaft.core.ai_config import AIConfig


@pytest.fixture
def provider():
    """Create an OpenAICompatibleProvider for testing."""
    return OpenAICompatibleProvider(
        base_url="http://localhost:11434/v1",
        model="llama3.1:8b",
        timeout=10,
    )


@patch("yaft.ai.providers.openai_compatible.requests.get")
def test_is_available_true(mock_get, provider):
    """Test is_available returns True when the backend responds 200."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    assert provider.is_available() is True
    mock_get.assert_called_once_with("http://localhost:11434/v1/models", timeout=5)


@patch("yaft.ai.providers.openai_compatible.requests.get")
def test_is_available_false_on_bad_status(mock_get, provider):
    """Test is_available returns False on a non-200 status code."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_get.return_value = mock_response

    assert provider.is_available() is False


@patch("yaft.ai.providers.openai_compatible.requests.get")
def test_is_available_false_on_network_error(mock_get, provider):
    """Test is_available returns False when the request raises."""
    mock_get.side_effect = requests.ConnectionError("Connection refused")

    assert provider.is_available() is False


@patch("yaft.ai.providers.openai_compatible.requests.post")
def test_summarize_success(mock_post, provider, tmp_path, monkeypatch):
    """Test summarize returns an LLMResult on a successful call."""
    monkeypatch.chdir(tmp_path)

    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello, world!"}}]
    }
    mock_post.return_value = mock_response

    result = provider.summarize("say hello", system="be terse")

    assert isinstance(result, LLMResult)
    assert result.text == "Hello, world!"
    assert result.provider == "ollama"
    assert result.model == "llama3.1:8b"
    assert result.latency_ms >= 0

    # Audit log should contain no prompt/response content
    audit_log = tmp_path / ".ai_cache" / "audit.jsonl"
    assert audit_log.exists()
    contents = audit_log.read_text(encoding="utf-8")
    assert "say hello" not in contents
    assert "Hello, world!" not in contents
    assert '"success": true' in contents


@patch("yaft.ai.providers.openai_compatible.requests.post")
def test_summarize_network_error_raises(mock_post, provider, tmp_path, monkeypatch):
    """Test summarize raises AIProviderError on a network failure."""
    monkeypatch.chdir(tmp_path)
    mock_post.side_effect = requests.ConnectionError("Connection refused")

    with pytest.raises(AIProviderError):
        provider.summarize("say hello")


def test_build_provider_disabled_raises():
    """Test build_provider raises AIFeatureDisabledError when disabled."""
    cfg = AIConfig(enabled=False)

    with pytest.raises(AIFeatureDisabledError):
        build_provider(cfg)


def test_build_provider_ollama_returns_openai_compatible():
    """Test build_provider returns an OpenAICompatibleProvider for ollama."""
    cfg = AIConfig(enabled=True, default_provider="ollama")

    result = build_provider(cfg)

    assert isinstance(result, OpenAICompatibleProvider)
    assert result.model == cfg.ollama.model
    assert result.base_url == cfg.ollama.base_url.rstrip("/")


@pytest.mark.parametrize("provider_name", ["anthropic", "openai"])
def test_build_provider_not_implemented_providers_raise(provider_name):
    """Test build_provider raises AIProviderNotImplementedError for cloud providers."""
    cfg = AIConfig(enabled=True, default_provider=provider_name)

    with pytest.raises(AIProviderNotImplementedError):
        build_provider(cfg)
