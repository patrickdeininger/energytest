"""Tests for the vuln-detection prompt builder and output parser."""

import pytest

from harness.schema import Task
from harness.tasks.vuln_detect import build_prompt, parse


def _task(code="int f(){char b[8];gets(b);return 0;}"):
    return Task(id="t1", code=code, label=1, cwe="CWE-120", source="fixture")


def test_build_prompt_includes_code_and_asks_for_verdict():
    p = build_prompt(_task(code="MARKER_CODE_123"))
    assert "MARKER_CODE_123" in p
    assert "vulnerab" in p.lower()  # asks about vulnerability


def test_build_prompt_truncates_long_code():
    p = build_prompt(_task(code="A" * 5000), max_code_chars=100)
    assert "truncat" in p.lower()
    assert p.count("A") <= 120  # kept ~max_code_chars, not all 5000


def test_build_prompt_keeps_short_code_intact():
    p = build_prompt(_task(code="SHORT_CODE"), max_code_chars=100)
    assert "SHORT_CODE" in p
    assert "truncat" not in p.lower()


@pytest.mark.parametrize(
    "text,expected",
    [
        ("yes", 1),
        ("no", 0),
        ("YES, this code is vulnerable", 1),
        ("No.", 0),
        ('{"vulnerable": true}', 1),
        ('{"vulnerable": false}', 0),
        ('{"label": 1}', 1),
        ('{"label": 0}', 0),
        ("After analysis, the function is NOT vulnerable.", 0),
        ("The code contains a buffer overflow; it is vulnerable.", 1),
        ("No vulnerability was found in this snippet.", 0),
        # Reasoning-mode outputs: verdict comes first (possibly bold), then verbose
        # analysis that mentions marker words. The leading verdict must win.
        ("**NO**\n\nThe code path that would be vulnerable is unreachable here.", 0),
        ("**YES**\n\nThe buffer copy has no bounds check.", 1),
        ("NO. This function only performs arithmetic and is exploitable by nothing.", 0),
    ],
)
def test_parse_extracts_label(text, expected):
    pred = parse(text)
    assert pred.parsed_ok is True
    assert pred.label == expected


@pytest.mark.parametrize("text", ["banana", "I cannot determine this.", ""])
def test_parse_marks_unparseable_as_failed_defaulting_to_zero(text):
    pred = parse(text)
    assert pred.parsed_ok is False
    assert pred.label == 0
    assert pred.raw == text
