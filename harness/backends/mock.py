"""Deterministic mock backend for the dry-run pilot (no API, no GPU).

Behaviors let a config declare fake "models" with known answer tendencies so the
dry-run produces a non-trivial confusion matrix:
  - always_vulnerable / always_safe: constant verdict (clean test anchors)
  - high_recall: ~80% "vulnerable"
  - balanced: ~50/50
Verdicts are a deterministic function of (seed, prompt) via SHA-256, so runs are
reproducible across processes (unlike Python's salted built-in hash()).
"""

from __future__ import annotations

import hashlib

from harness.backends.base import Backend
from harness.schema import GenParams, Response


class MockBackend(Backend):
    def __init__(self, behavior: str = "balanced", seed: int = 0):
        self.behavior = behavior
        self.seed = seed

    def _pseudo_unit(self, prompt: str) -> float:
        digest = hashlib.sha256(f"{self.seed}:{prompt}".encode("utf-8")).hexdigest()
        return (int(digest, 16) % 1_000_000) / 1_000_000.0

    def _decide_vulnerable(self, prompt: str) -> bool:
        if self.behavior == "always_vulnerable":
            return True
        if self.behavior == "always_safe":
            return False
        r = self._pseudo_unit(prompt)
        if self.behavior == "high_recall":
            return r < 0.8
        return r < 0.5  # balanced (default)

    def generate(self, prompt: str, params: GenParams) -> Response:
        if self.behavior == "error":  # for testing runner error handling
            raise RuntimeError("simulated backend error")
        vulnerable = self._decide_vulnerable(prompt)
        text = (
            "YES, the code is vulnerable."
            if vulnerable
            else "NO, the code is not vulnerable."
        )
        input_tokens = max(1, len(prompt.split()))
        output_tokens = max(1, len(text.split()))
        return Response(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            ttft_ms=None,
        )
