"""Exceptions raised by the AI / LLM provider layer."""


class AIError(Exception):
    """Base class for AI-related errors."""


class AIFeatureDisabledError(AIError):
    """Raised when AI features are used while disabled in configuration."""


class AIProviderNotImplementedError(AIError):
    """Raised when a configured provider has no implementation yet."""


class AIProviderError(AIError):
    """Raised when a provider call fails (network error, bad response, etc.)."""
