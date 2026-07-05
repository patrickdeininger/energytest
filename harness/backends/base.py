"""Backend interface. Implementations return a Response for a prompt."""

from __future__ import annotations

from abc import ABC, abstractmethod

from harness.schema import GenParams, Response


class Backend(ABC):
    @abstractmethod
    def generate(self, prompt: str, params: GenParams) -> Response:
        ...
