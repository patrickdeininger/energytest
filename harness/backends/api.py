"""API backend for OpenAI-compatible chat endpoints.

One client covers OpenAI, OpenRouter, and (later) a local vLLM server, since all
speak the OpenAI chat-completions format. The client is injectable so the mapping
logic is unit-tested without a network call; the real SDK is imported lazily so
importing this module never requires the `openai` package to be configured.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from harness.backends.base import Backend
from harness.schema import GenParams, Response


@dataclass
class RawCompletion:
    text: str
    input_tokens: int
    output_tokens: int
    ttft_ms: float | None = None
    # Which upstream actually served the request. For open-weight models a gateway
    # may route across a dozen providers whose prices span ~7x, so the configured
    # price is only the price paid if the provider is known (and pinned).
    provider: str | None = None
    attempts: int = 1  # 1 = succeeded first try; >1 means transient failures were retried


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
            provider=raw.provider,
            attempts=raw.attempts,
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
        provider_order: list[str] | None = None,
        max_retries: int = 4,
        backoff_base: float = 1.5,
        sleep=None,
    ):
        self._sdk = sdk_client if sdk_client is not None else self._make_sdk(api_key, base_url)
        self._extra_headers = extra_headers
        self._extra_body = extra_body  # e.g. {"reasoning": {"enabled": False}} for OpenRouter
        # Pin routing to named providers with fallbacks off, so the run is reproducible
        # and the configured per-token price is the price actually charged.
        self._provider_order = provider_order
        # Transient provider failures (429/5xx/timeouts) and empty completions are
        # retried with exponential backoff + jitter. Without this a rate limit is
        # indistinguishable from a model that cannot answer, which silently
        # depresses parse rates and biases every downstream metric.
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._sleep = sleep if sleep is not None else time.sleep

    @staticmethod
    def _make_sdk(api_key: str | None, base_url: str | None):
        from openai import OpenAI  # lazy: importing this module must not require config

        return OpenAI(api_key=api_key or "MISSING", base_url=base_url)

    @staticmethod
    def _status_of(exc) -> int | None:
        for attr in ("status_code", "http_status", "code"):
            v = getattr(exc, attr, None)
            if isinstance(v, int):
                return v
        resp = getattr(exc, "response", None)
        v = getattr(resp, "status_code", None)
        return v if isinstance(v, int) else None

    @classmethod
    def _is_transient(cls, exc) -> bool:
        status = cls._status_of(exc)
        if status is None:
            # Network/timeout errors carry no status; those are worth retrying.
            return isinstance(exc, (TimeoutError, ConnectionError))
        return status == 408 or status == 429 or status >= 500

    def _backoff(self, attempt: int) -> float:
        # Full jitter over an exponentially growing window; the +attempt keeps the
        # sequence strictly increasing even when jitter is unlucky.
        window = self._backoff_base ** attempt
        return attempt + random.random() * window

    def complete(self, model: str, prompt: str, params: GenParams) -> RawCompletion:
        last = None
        for attempt in range(self._max_retries + 1):
            try:
                raw = self._complete_once(model, prompt, params)
            except Exception as exc:
                if attempt >= self._max_retries or not self._is_transient(exc):
                    raise
                last = exc
                self._sleep(self._backoff(attempt + 1))
                continue
            # An empty completion is usually a transient provider symptom, but it
            # can also be a real budget exhaustion (a reasoning model that spent
            # every token thinking). Retry it, then accept whatever comes back --
            # never fabricate a verdict.
            if not raw.text.strip() and attempt < self._max_retries:
                self._sleep(self._backoff(attempt + 1))
                continue
            raw.attempts = attempt + 1
            return raw
        raise last  # unreachable: the loop either returns or raises

    def _complete_once(self, model: str, prompt: str, params: GenParams) -> RawCompletion:
        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": params.temperature,
            "max_tokens": params.max_output_tokens,
        }
        if self._extra_headers:
            kwargs["extra_headers"] = self._extra_headers
        extra_body = dict(self._extra_body) if self._extra_body else {}
        if self._provider_order:
            extra_body["provider"] = {
                "order": list(self._provider_order),
                "allow_fallbacks": False,
            }
        if extra_body:
            kwargs["extra_body"] = extra_body
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
            provider=getattr(resp, "provider", None),
        )
