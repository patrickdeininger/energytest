"""Monetary cost meter: USD from token counts and per-million pricing."""

from __future__ import annotations

from typing import Callable

from harness.meters.base import Meter
from harness.schema import Response


class CostMeter(Meter):
    def __init__(self, price_in: float, price_out: float):
        """price_in / price_out are USD per 1,000,000 tokens."""
        self.price_in = price_in
        self.price_out = price_out

    def measure(self, call: Callable[[], Response]) -> tuple[Response, dict]:
        resp = call()
        usd = resp.input_tokens / 1e6 * self.price_in + resp.output_tokens / 1e6 * self.price_out
        return resp, {
            "usd_cost": usd,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
        }
