"""Model backends: mock (pilot), api (OpenAI-compatible), local (later)."""

from harness.backends.base import Backend
from harness.backends.mock import MockBackend
from harness.backends.api import APIBackend, OpenAICompatibleClient, RawCompletion

__all__ = [
    "Backend",
    "MockBackend",
    "APIBackend",
    "OpenAICompatibleClient",
    "RawCompletion",
]
