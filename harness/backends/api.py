"""API backend for OpenAI-compatible chat endpoints.

One client covers OpenAI, OpenRouter, and (later) a local vLLM server, since all
speak the OpenAI chat-completions format. The client is injectable so the mapping
logic is unit-tested without a network call; the real SDK is imported lazily so
importing this module never requires the `openai` package to be configured.
"""

from __future__ import annotations

from dataclasses import dataclass

from harness.backends.base import Backend
from harness.schema import GenParams, Response


@dataclass
class RawCompletion:
    text: str
    input_tokens: int
    output_tokens: int
    ttft_ms: float | None = None


class APIBackend(Backend):
    def __init__(self, model: str, client):
        self.model = model
        self.client = client

    def generate(self, prompt: str, params: GenParams) -> Response:
        raw = self.client.complete(self.model, prompt, params)
        return Response(
            text=raw.text,
            input_tokens=raw.input_tokens,
            output_tokens=raw.output_tokens,
            ttft_ms=raw.ttft_ms,
        )


class OpenAICompatibleClient:
    """Client for any OpenAI-compatible chat endpoint (OpenAI / OpenRouter / vLLM)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        sdk_client=None,
        extra_headers: dict | None = None,
        extra_body: dict | None = None,
    ):
        self._sdk = sdk_client if sdk_client is not None else self._make_sdk(api_key, base_url)
        self._extra_headers = extra_headers
        self._extra_body = extra_body  # e.g. {"reasoning": {"enabled": False}} for OpenRouter

    @staticmethod
    def _make_sdk(api_key: str | None, base_url: str | None):
        from openai import OpenAI  # lazy: importing this module must not require config

        return OpenAI(api_key=api_key or "MISSING", base_url=base_url)

    def complete(self, model: str, prompt: str, params: GenParams) -> RawCompletion:
        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": params.temperature,
            "max_tokens": params.max_output_tokens,
        }
        if self._extra_headers:
            kwargs["extra_headers"] = self._extra_headers
        if self._extra_body:
            kwargs["extra_body"] = self._extra_body
        resp = self._sdk.chat.completions.create(**kwargs)
        message = resp.choices[0].message
        content = message.content or ""
        # Reasoning models leave `content` empty and put the answer in `reasoning`;
        # fall back to it so the verdict is still recoverable.
        reasoning = getattr(message, "reasoning", None) or ""
        usage = resp.usage
        return RawCompletion(
            text=content or reasoning,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            ttft_ms=None,  # requires streaming; added later
        )
