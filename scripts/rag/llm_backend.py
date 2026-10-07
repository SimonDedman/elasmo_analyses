"""LLM backend seam for the RAG pipeline (spec component 5).

Selected by RAG_LLM_BACKEND in {ollama (default), anthropic, none}.
The Anthropic key is read ONLY from the ANTHROPIC_API_KEY environment
variable; it is never read from a file and never logged.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Protocol

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OLLAMA_HOST, OLLAMA_MODEL  # noqa: E402

# Cheapest current Claude model per the claude-api skill table (cached 2026-09-25).
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5"
ANTHROPIC_MAX_TOKENS = 600


class BackendError(RuntimeError):
    """Raised for configuration problems (missing key, unknown backend)."""


class Backend(Protocol):
    name: str

    def generate(self, system: str, prompt: str) -> str: ...
    def available(self) -> bool: ...


class OllamaBackend:
    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_MODEL):
        self.host, self.model = host, model
        self.name = f"ollama:{model}"

    def available(self) -> bool:
        try:
            return requests.get(f"{self.host}/api/tags", timeout=2).status_code == 200
        except requests.RequestException:
            return False

    def generate(self, system: str, prompt: str) -> str:
        try:
            r = requests.post(
                f"{self.host}/api/generate",
                json={"model": self.model, "prompt": prompt,
                      "system": system, "stream": False,
                      # Deterministic decoding: same question + same retrieved
                      # context -> identical answer (greedy, fixed seed).
                      "options": {"temperature": 0, "seed": 7}},
                timeout=120,
            )
            r.raise_for_status()
            return r.json()["response"].strip()
        except requests.RequestException as e:
            return f"[generation error: {e}]"


class AnthropicBackend:
    def __init__(self, model: str | None = None):
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise BackendError(
                "RAG_LLM_BACKEND=anthropic needs ANTHROPIC_API_KEY set in the "
                "environment (it is never read from a file).")
        import anthropic
        self.model = model or os.environ.get("RAG_LLM_MODEL") or DEFAULT_ANTHROPIC_MODEL
        self.name = f"anthropic:{self.model}"
        self._client = anthropic.Anthropic(api_key=key, timeout=120.0)

    def available(self) -> bool:
        return True  # no cheap free probe; failures surface from generate()

    def generate(self, system: str, prompt: str, max_tokens: int = ANTHROPIC_MAX_TOKENS) -> str:
        import anthropic
        try:
            msg = self._client.messages.create(
                model=self.model, max_tokens=max_tokens, temperature=0,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as e:
            # Message text only; the key is never part of an SDK error string.
            return f"[generation error: {type(e).__name__}: {e}]"
        return "".join(b.text for b in msg.content if b.type == "text").strip()


class NoBackend:
    name = "none"

    def available(self) -> bool:
        return False

    def generate(self, system: str, prompt: str) -> str:
        return ""


def get_backend() -> Backend:
    choice = (os.environ.get("RAG_LLM_BACKEND") or "ollama").strip().lower()
    if choice == "ollama":
        return OllamaBackend()
    if choice == "anthropic":
        return AnthropicBackend()
    if choice == "none":
        return NoBackend()
    raise BackendError(f"unknown RAG_LLM_BACKEND {choice!r}; use ollama, anthropic, or none")
