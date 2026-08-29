"""Tests for bounded retry/backoff on transient API failures.

The smoke run for the round-2 batch lost an entire model to a provider-side 429.
Without retries a transient rate limit is indistinguishable from a model that
cannot answer, which silently depresses parse rates and biases every downstream
metric. R3#3 asks for the retry procedure to be documented; this makes there be
one worth documenting.

No real sleeping: the sleep function is injected.
"""

import pytest

from harness.backends.api import OpenAICompatibleClient, RawCompletion
from harness.schema import GenParams


class _Err(Exception):
    def __init__(self, status):
        super().__init__(f"status {status}")
        self.status_code = status


class _SDK:
    """Fails with the given statuses in order, then succeeds."""

    def __init__(self, failures=(), content="YES"):
        self.failures = list(failures)
        self.content = content
        self.calls = 0
        self.chat = self

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        self.calls += 1
        if self.failures:
            raise _Err(self.failures.pop(0))

        class _U:
            prompt_tokens, completion_tokens = 10, 3

        class _M:
            content = self.content
            reasoning = None

        class _C:
            message = _M()

        class _R:
            choices = [_C()]
            usage = _U()
            provider = "P"

        return _R()


def _client(sdk, **kw):
    slept = []
    return OpenAICompatibleClient(
        sdk_client=sdk, sleep=slept.append, **kw
    ), slept


def test_retries_a_429_and_succeeds():
    sdk = _SDK(failures=[429])
    c, slept = _client(sdk)
    raw = c.complete("m", "p", GenParams())
    assert raw.text == "YES"
    assert sdk.calls == 2
    assert len(slept) == 1


def test_retries_5xx_and_timeouts():
    sdk = _SDK(failures=[500, 503])
    c, slept = _client(sdk)
    c.complete("m", "p", GenParams())
    assert sdk.calls == 3


def test_backoff_grows_between_attempts():
    sdk = _SDK(failures=[429, 429, 429])
    c, slept = _client(sdk, max_retries=5, backoff_base=1.0)
    c.complete("m", "p", GenParams())
    assert len(slept) == 3
    assert slept[0] < slept[1] < slept[2], slept


def test_gives_up_after_max_retries_and_reraises():
    sdk = _SDK(failures=[429] * 10)
    c, _ = _client(sdk, max_retries=2)
    with pytest.raises(_Err):
        c.complete("m", "p", GenParams())
    assert sdk.calls == 3  # initial + 2 retries


def test_does_not_retry_a_400():
    """A malformed request (e.g. reasoning cannot be disabled on this endpoint)
    will fail identically forever; retrying it only burns wall-clock."""
    sdk = _SDK(failures=[400] * 5)
    c, _ = _client(sdk)
    with pytest.raises(_Err):
        c.complete("m", "p", GenParams())
    assert sdk.calls == 1


def test_empty_content_is_retried_then_returned_empty():
    """An empty completion is a transient provider symptom often enough to be
    worth one retry, but it must not loop forever or fabricate a verdict."""
    sdk = _SDK(content="")
    c, _ = _client(sdk, max_retries=2)
    raw = c.complete("m", "p", GenParams())
    assert raw.text == ""
    assert sdk.calls == 3


def test_attempt_count_is_reported():
    sdk = _SDK(failures=[429, 500])
    c, _ = _client(sdk)
    raw = c.complete("m", "p", GenParams())
    assert isinstance(raw, RawCompletion)
    assert raw.attempts == 3


def test_no_retry_means_one_call_on_success():
    sdk = _SDK()
    c, slept = _client(sdk)
    raw = c.complete("m", "p", GenParams())
    assert sdk.calls == 1 and slept == [] and raw.attempts == 1
