"""Latency meter: wall-clock total, tokens/s, and pass-through TTFT.

The clock is injectable so tests are deterministic; production uses a real
monotonic clock. This is the one meter that legitimately reads the wall clock.
"""

from __future__ import annotations

import time
from typing import Callable

from harness.meters.base import Meter
from harness.schema import Response


class LatencyMeter(Meter):
    def __init__(self, clock: Callable[[], float] = time.perf_counter):
        self.clock = clock

    def measure(self, call: Callable[[], Response]) -> tuple[Response, dict]:
        t0 = self.clock()
        resp = call()
        t1 = self.clock()
        total_ms = (t1 - t0) * 1000.0
        seconds = total_ms / 1000.0
        tokens_per_s = resp.output_tokens / seconds if seconds > 0 else 0.0
        return resp, {
            "ttft_ms": resp.ttft_ms,
            "total_ms": total_ms,
            "tokens_per_s": tokens_per_s,
        }
