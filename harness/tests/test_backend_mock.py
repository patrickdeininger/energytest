"""Tests for the deterministic mock backend used in the dry-run pilot."""

from harness.schema import GenParams
from harness.backends.mock import MockBackend
from harness.tasks.vuln_detect import parse

PARAMS = GenParams(temperature=0.0, max_output_tokens=64)


def test_always_vulnerable_behavior_predicts_positive():
    r = MockBackend(behavior="always_vulnerable").generate("any prompt", PARAMS)
    assert parse(r.text).label == 1


def test_always_safe_behavior_predicts_negative():
    r = MockBackend(behavior="always_safe").generate("any prompt", PARAMS)
    assert parse(r.text).label == 0


def test_deterministic_for_same_prompt_and_seed():
    a = MockBackend(behavior="balanced", seed=7).generate("prompt X", PARAMS)
    b = MockBackend(behavior="balanced", seed=7).generate("prompt X", PARAMS)
    assert a.text == b.text
    assert a.input_tokens == b.input_tokens
    assert a.output_tokens == b.output_tokens


def test_token_counts_are_positive():
    r = MockBackend(behavior="balanced").generate("some prompt with words", PARAMS)
    assert r.input_tokens > 0
    assert r.output_tokens > 0
