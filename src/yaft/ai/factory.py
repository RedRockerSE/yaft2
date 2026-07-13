"""Factory for building the configured LLM provider."""

from yaft.ai.exceptions import AIFeatureDisabledError, AIProviderNotImplementedError
from yaft.ai.providers.base import LLMProvider
from yaft.ai.providers.openai_compatible import OpenAICompatibleProvider
from yaft.core.ai_config import AIConfig


def build_provider(cfg: AIConfig) -> LLMProvider:
    """
    Build the LLM provider configured in cfg.default_provider.

    Args:
        cfg: AI configuration

    Returns:
        LLMProvider instance for the configured default provider

    Raises:
        AIFeatureDisabledError: If cfg.enabled is False
        AIProviderNotImplementedError: If the configured provider has no implementation yet
    """
    if not cfg.enabled:
        raise AIFeatureDisabledError(
            "AI features are disabled. Run `yaft ai-configure --enable` to turn them on."
        )

    if cfg.default_provider == "ollama":
        return OpenAICompatibleProvider(
            base_url=cfg.ollama.base_url,
            model=cfg.ollama.model,
            timeout=cfg.ollama.timeout,
        )

    if cfg.default_provider in ("anthropic", "openai"):
        raise AIProviderNotImplementedError(
            f"Provider '{cfg.default_provider}' is not implemented yet. "
            "Use 'ollama' for a local, self-hosted backend."
        )

    raise AIProviderNotImplementedError(f"Unknown provider: {cfg.default_provider}")
