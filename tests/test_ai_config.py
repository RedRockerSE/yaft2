"""
Tests for AI / LLM provider configuration.

Tests the AIConfig pydantic model and CoreAPI._load_ai_config() including
defaults, TOML loading/merging, and validation of default_provider.
"""

import pytest

from yaft.core.ai_config import (
    AIConfig,
    AnthropicProviderConfig,
    OllamaProviderConfig,
    OpenAIProviderConfig,
)
from yaft.core.api import CoreAPI


def test_ai_config_defaults():
    """Test AIConfig default values."""
    cfg = AIConfig()

    assert cfg.enabled is False
    assert cfg.default_provider == "ollama"
    assert cfg.ollama.base_url == "http://localhost:11434/v1"
    assert cfg.ollama.model == "llama3.1:8b"
    assert cfg.ollama.timeout == 60
    assert cfg.anthropic.enabled is False
    assert cfg.openai.enabled is False


def test_ollama_provider_config_defaults():
    """Test OllamaProviderConfig default values."""
    cfg = OllamaProviderConfig()

    assert cfg.base_url == "http://localhost:11434/v1"
    assert cfg.model == "llama3.1:8b"
    assert cfg.timeout == 60


def test_ollama_provider_config_invalid_timeout():
    """Test OllamaProviderConfig rejects non-positive timeout."""
    with pytest.raises(ValueError):
        OllamaProviderConfig(timeout=0)


def test_anthropic_provider_config_is_placeholder():
    """Test AnthropicProviderConfig defaults to disabled."""
    cfg = AnthropicProviderConfig()

    assert cfg.enabled is False
    assert cfg.model == "claude-haiku-4-5"


def test_openai_provider_config_is_placeholder():
    """Test OpenAIProviderConfig defaults to disabled."""
    cfg = OpenAIProviderConfig()

    assert cfg.enabled is False
    assert cfg.model == "gpt-4o-mini"


def test_ai_config_invalid_default_provider():
    """Test AIConfig rejects unknown default_provider values."""
    with pytest.raises(ValueError):
        AIConfig(default_provider="bogus")


def test_ai_config_valid_providers():
    """Test AIConfig accepts all documented provider names."""
    for provider in ("ollama", "anthropic", "openai"):
        cfg = AIConfig(default_provider=provider)
        assert cfg.default_provider == provider


def test_load_ai_config_file_missing(tmp_path):
    """Test loading AI config returns defaults when file doesn't exist."""
    config_dir = tmp_path / "config"
    api = CoreAPI(config_dir=config_dir)

    assert isinstance(api._ai_config, AIConfig)
    assert api._ai_config.enabled is False
    assert api._ai_config.default_provider == "ollama"


def test_load_ai_config_from_toml(tmp_path):
    """Test loading AI config from a TOML file merges nested sections."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "ai.toml").write_text(
        """
[ai]
enabled = true
default_provider = "ollama"

[ai.providers.ollama]
base_url = "http://localhost:9999/v1"
model = "custom-model"
timeout = 90
""",
        encoding="utf-8",
    )

    api = CoreAPI(config_dir=config_dir)

    assert api._ai_config.enabled is True
    assert api._ai_config.default_provider == "ollama"
    assert api._ai_config.ollama.base_url == "http://localhost:9999/v1"
    assert api._ai_config.ollama.model == "custom-model"
    assert api._ai_config.ollama.timeout == 90


def test_load_ai_config_invalid_toml_falls_back_to_defaults(tmp_path):
    """Test that an invalid AI config file falls back to defaults with a warning."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "ai.toml").write_text(
        """
[ai]
default_provider = "not-a-real-provider"
""",
        encoding="utf-8",
    )

    api = CoreAPI(config_dir=config_dir)

    assert isinstance(api._ai_config, AIConfig)
    assert api._ai_config.default_provider == "ollama"
