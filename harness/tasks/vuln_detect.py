"""Binary vulnerability-detection task: prompt construction and output parsing.

Positive class = vulnerable (label 1). The parser is intentionally lenient: real
models answer in many shapes (bare yes/no, JSON, verbose chain-of-thought). It
tries JSON, then negative markers (checked BEFORE positive ones, since "not
vulnerable" contains "vulnerable"), then positive markers, then bare yes/no.
Anything it cannot resolve is parsed_ok=False, defaulting label to 0.
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel

from harness.schema import Task


class Prediction(BaseModel):
    label: int
    raw: str
    parsed_ok: bool
    # P(vulnerable) in [0,1], only present when the prompt elicited it (variant "conf").
    # A continuous score is what PR curves, VD-Score and calibration need; a binary
    # verdict cannot be threshold-swept.
    confidence: float | None = None


PROMPT_TEMPLATE = """You are a security code reviewer. Analyze the following function for security vulnerabilities.

Answer with a single word first: "YES" if the code contains a vulnerability, or "NO" if it does not. You may then add a brief explanation.

Code:
```
{code}
```

Is this code vulnerable?"""

# Prompt variants for the sensitivity analysis. "v1" is the anchor and MUST stay
# byte-identical to the template used in the original runs. Each other variant
# changes exactly one interpretable thing relative to v1, so a shift in results
# can be attributed:
#   v2  -- drops the expert persona (tests role-prompt dependence)
#   v3  -- keeps the persona but offers "NO" before "YES" (tests option-order bias)
#   conf -- v1 plus an elicited P(vulnerable), for threshold-swept metrics
_V2 = """Does the following C/C++ function contain a security vulnerability?

Reply with a single word first: "YES" if it does, or "NO" if it does not. A brief explanation may follow.

Code:
```
{code}
```

Is this code vulnerable?"""

_V3 = """You are a security code reviewer. Analyze the following function for security vulnerabilities.

Answer with a single word first: "NO" if the code is free of vulnerabilities, or "YES" if it contains one. You may then add a brief explanation.

Code:
```
{code}
```

Is this code vulnerable?"""

_CONF = """You are a security code reviewer. Analyze the following function for security vulnerabilities.

Answer in exactly this format on the first two lines:
VERDICT: YES or NO
CONFIDENCE: an integer from 0 to 100

VERDICT is "YES" if the code contains a vulnerability, "NO" if it does not. CONFIDENCE is the probability, in percent, that the code contains a vulnerability: 0 means certainly safe, 100 means certainly vulnerable. You may then add a brief explanation.

Code:
```
{code}
```

Is this code vulnerable?"""

PROMPT_TEMPLATES: dict[str, str] = {
    "v1": PROMPT_TEMPLATE,
    "v2": _V2,
    "v3": _V3,
    "conf": _CONF,
}


def build_prompt(
    task: Task, max_code_chars: int | None = None, variant: str = "v1"
) -> str:
    template = PROMPT_TEMPLATES[variant]  # KeyError on typos, before any spending
    code = task.code
    if max_code_chars is not None and len(code) > max_code_chars:
        code = code[:max_code_chars] + "\n/* ... truncated ... */"
    return template.format(code=code)


_NEG_MARKERS = (
    "not vulnerable",
    "no vulnerability",
    "not exploitable",
    "is safe",
    "isn't vulnerable",
    "is not vulnerable",
)
_POS_MARKERS = ("vulnerable", "exploitable")


def _coerce(value) -> int | None:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if int(value) == 1 else 0
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("1", "true", "yes", "vulnerable"):
            return 1
        if s in ("0", "false", "no", "not vulnerable", "safe"):
            return 0
    return None


def _leading_verdict(text: str) -> int | None:
    """The prompt asks the model to answer YES/NO first. Honor that leading token
    (possibly wrapped in markdown emphasis/quotes) before scanning the body, so that
    verbose reasoning outputs---which mention 'vulnerable'/'yes'/'no' throughout their
    analysis---are not misread. Returns 1 (YES), 0 (NO), or None if no leading verdict.
    """
    s = re.sub(r"^[\s*_#>\-\"'`.:]+", "", text)  # strip leading markdown/punctuation/space
    m = re.match(r"(yes|no)\b", s, re.IGNORECASE)
    if m:
        return 1 if m.group(1).lower() == "yes" else 0
    return None


def _from_json(text: str) -> int | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except (ValueError, TypeError):
        return None
    if not isinstance(obj, dict):
        return None
    for key in ("vulnerable", "is_vulnerable", "label", "answer"):
        if key in obj:
            return _coerce(obj[key])
    return None


_VERDICT_RE = re.compile(r"^[\s*_#>\-\"'`]*VERDICT\s*:\s*\**\s*(yes|no)\b", re.IGNORECASE | re.MULTILINE)
_CONF_RE = re.compile(r"^[\s*_#>\-\"'`]*CONFIDENCE\s*:\s*\**\s*(-?[0-9]*\.?[0-9]+)\s*%?", re.IGNORECASE | re.MULTILINE)


def _labelled_verdict(text: str) -> int | None:
    """The "conf" variant asks for `VERDICT: YES|NO` on its own line. Read that
    explicitly: the explanation that follows nearly always contains the word
    "vulnerable", which the marker scan below would otherwise pick up."""
    m = _VERDICT_RE.search(text)
    if m:
        return 1 if m.group(1).lower() == "yes" else 0
    return None


def _confidence(text: str) -> float | None:
    """P(vulnerable) as a 0-1 float. Accepts `85`, `85%` and `0.85`; values above
    1 are read as percentages, and everything is clamped to [0,1] because models
    do occasionally answer 120."""
    m = _CONF_RE.search(text)
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    if v > 1.0:
        v /= 100.0
    return max(0.0, min(1.0, v))


def parse(text: str) -> Prediction:
    raw = text if text is not None else ""
    if not raw.strip():
        return Prediction(label=0, raw=raw, parsed_ok=False)

    conf = _confidence(raw)

    labelled = _labelled_verdict(raw)
    if labelled is not None:
        return Prediction(label=labelled, raw=raw, parsed_ok=True, confidence=conf)

    from_json = _from_json(raw)
    if from_json is not None:
        return Prediction(label=from_json, raw=raw, parsed_ok=True, confidence=conf)

    leading = _leading_verdict(raw)
    if leading is not None:
        return Prediction(label=leading, raw=raw, parsed_ok=True, confidence=conf)

    low = raw.lower()
    for marker in _NEG_MARKERS:
        if marker in low:
            return Prediction(label=0, raw=raw, parsed_ok=True, confidence=conf)
    for marker in _POS_MARKERS:
        if marker in low:
            return Prediction(label=1, raw=raw, parsed_ok=True, confidence=conf)
    if re.search(r"\byes\b", low):
        return Prediction(label=1, raw=raw, parsed_ok=True, confidence=conf)
    if re.search(r"\bno\b", low):
        return Prediction(label=0, raw=raw, parsed_ok=True, confidence=conf)

    return Prediction(label=0, raw=raw, parsed_ok=False, confidence=conf)
