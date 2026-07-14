"""LLM provider for any OpenAI-compatible chat completions server.

Covers Ollama, llama.cpp's llama-server, LM Studio, LocalAI, and vLLM with a
single implementation, since they all speak the same /v1/chat/completions
wire format.
"""

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

from yaft.ai.exceptions import AIProviderError
from yaft.ai.providers.base import LLMResult

AUDIT_LOG_PATH = Path(".ai_cache") / "audit.jsonl"


def _write_audit_log(provider: str, model: str, latency_ms: int, success: bool) -> None:
    """Append a minimal audit record. Never logs prompt/response content."""
    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "provider": provider,
            "model": model,
            "latency_ms": latency_ms,
            "success": success,
        }
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass


class OpenAICompatibleProvider:
    """LLM provider that speaks the OpenAI-compatible chat completions API."""

    def __init__(self, base_url: str, model: str, timeout: int = 60) -> None:
        """
        Initialize the provider.

        Args:
            base_url: Base URL of the OpenAI-compatible server (e.g. http://localhost:11434/v1)
            model: Model name to use
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        """Check whether the backend is reachable by querying /models."""
        try:
            resp = requests.get(f"{self.base_url}/models", timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def summarize(self, prompt: str, *, system: str | None = None) -> LLMResult:
        """Send a prompt to the backend and return the generated response."""
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]

        start = time.monotonic()
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json={"model": self.model, "messages": messages},
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            _write_audit_log("ollama", self.model, latency_ms, success=False)
            raise AIProviderError(f"OpenAI-compatible call failed: {e}") from e

        latency_ms = int((time.monotonic() - start) * 1000)
        text = resp.json()["choices"][0]["message"]["content"]
        _write_audit_log("ollama", self.model, latency_ms, success=True)

        return LLMResult(text=text, provider="ollama", model=self.model, latency_ms=latency_ms)
