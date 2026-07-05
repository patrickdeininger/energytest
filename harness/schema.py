"""Core data models for the benchmark harness."""

from __future__ import annotations

from pydantic import BaseModel


class Response(BaseModel):
    """A single model generation result returned by a backend."""

    text: str
    input_tokens: int
    output_tokens: int
    ttft_ms: float | None = None  # time-to-first-token, if the backend reports it


class Task(BaseModel):
    """One vulnerability-detection instance."""

    id: str
    code: str
    label: int  # 1 = vulnerable, 0 = not vulnerable
    cwe: str | None = None
    source: str = "unknown"
    meta: dict = {}


class GenParams(BaseModel):
    """Generation parameters passed to a backend."""

    temperature: float = 0.0
    max_output_tokens: int = 128
    seed: int | None = None
