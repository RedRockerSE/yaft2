"""
AI / LLM provider configuration for YAFT.

Defines the pydantic configuration models loaded from config/ai.toml. AI
features are disabled by default and default to a local, self-hosted
backend (Ollama or any OpenAI-compatible server) so that forensic case
data never has to leave the examiner's machine unless a cloud provider
is explicitly enabled.
"""

from pydantic import BaseModel, Field, field_validator


class OllamaProviderConfig(BaseModel):
    """Configuration for a local, OpenAI-compatible backend (Ollama, llama.cpp, LM Studio, etc.)."""

    base_url: str = Field(
        default="http://localhost:11434/v1",
        description="Base URL of the OpenAI-compatible server",
    )
    model: str = Field(default="llama3.1:8b", description="Model name to use")
    timeout: int = Field(default=60, description="Request timeout in seconds")

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout."""
        if v < 1:
            raise ValueError("timeout must be >= 1")
        return v


class AnthropicProviderConfig(BaseModel):
    """Placeholder configuration for the Anthropic provider (not yet implemented)."""

    enabled: bool = Field(default=False, description="Whether the Anthropic provider is enabled")
    model: str = Field(default="claude-haiku-4-5", description="Model name to use")


class OpenAIProviderConfig(BaseModel):
    """Placeholder configuration for the OpenAI provider (not yet implemented)."""

    enabled: bool = Field(default=False, description="Whether the OpenAI provider is enabled")
    model: str = Field(default="gpt-4o-mini", description="Model name to use")


class AIConfig(BaseModel):
    """AI / LLM provider configuration model."""

    enabled: bool = Field(default=False, description="Whether AI features are enabled")
    default_provider: str = Field(
        default="ollama", description="Default provider (ollama, anthropic, openai)"
    )
    ollama: OllamaProviderConfig = Field(default_factory=OllamaProviderConfig)
    anthropic: AnthropicProviderConfig = Field(default_factory=AnthropicProviderConfig)
    openai: OpenAIProviderConfig = Field(default_factory=OpenAIProviderConfig)

    @field_validator("default_provider")
    @classmethod
    def validate_default_provider(cls, v: str) -> str:
        """Validate default provider."""
        valid_providers = {"ollama", "anthropic", "openai"}
        v_lower = v.lower()
        if v_lower not in valid_providers:
            raise ValueError(
                f"Invalid default_provider: {v}. Must be one of {sorted(valid_providers)}"
            )
        return v_lower
