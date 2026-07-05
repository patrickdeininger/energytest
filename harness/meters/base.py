"""Meter interface and composition.

A Meter wraps a zero-arg `call` that returns a Response. It MUST invoke `call`
exactly once and return (Response, metrics_dict). `compose` nests meters so the
underlying backend is still invoked exactly once while every meter observes it;
the last meter in the list wraps the real call (innermost) and the first wraps
everything (outermost), so put the latency meter first.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from harness.schema import Response


class Meter(ABC):
    @abstractmethod
    def measure(self, call: Callable[[], Response]) -> tuple[Response, dict]:
        ...


class _Composed(Meter):
    def __init__(self, meters):
        self._meters = list(meters)

    def measure(self, call: Callable[[], Response]) -> tuple[Response, dict]:
        metrics: dict = {}

        def make_wrapped(meter: Meter, inner: Callable[[], Response]):
            def wrapped() -> Response:
                resp, m = meter.measure(inner)
                metrics.update(m)
                return resp

            return wrapped

        chain = call
        for meter in reversed(self._meters):
            chain = make_wrapped(meter, chain)
        resp = chain()
        return resp, metrics


def compose(meters) -> Meter:
    """Compose meters so the backend is invoked once and all metrics merge."""
    return _Composed(meters)
