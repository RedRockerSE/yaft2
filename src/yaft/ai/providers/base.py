"""Base types shared by all LLM providers."""

from typing import Protocol

from pydantic import BaseModel, Field


class LLMResult(BaseModel):
    """Result of a single LLM call."""

    text: str = Field(..., description="Generated text response")
    provider: str = Field(..., description="Name of the provider that produced this result")
    model: str = Field(..., description="Model name used")
    latency_ms: int = Field(..., description="Call latency in milliseconds")


class LLMProvider(Protocol):
    """Protocol implemented by all LLM providers."""

    def is_available(self) -> bool:
        """Check whether the provider's backend is reachable."""
        ...

    def summarize(self, prompt: str, *, system: str | None = None) -> LLMResult:
        """Send a prompt to the backend and return the generated response."""
        ...
