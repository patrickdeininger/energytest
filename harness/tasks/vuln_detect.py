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


PROMPT_TEMPLATE = """You are a security code reviewer. Analyze the following function for security vulnerabilities.

Answer with a single word first: "YES" if the code contains a vulnerability, or "NO" if it does not. You may then add a brief explanation.

Code:
```
{code}
```

Is this code vulnerable?"""


def build_prompt(task: Task, max_code_chars: int | None = None) -> str:
    code = task.code
    if max_code_chars is not None and len(code) > max_code_chars:
        code = code[:max_code_chars] + "\n/* ... truncated ... */"
    return PROMPT_TEMPLATE.format(code=code)


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


def parse(text: str) -> Prediction:
    raw = text if text is not None else ""
    if not raw.strip():
        return Prediction(label=0, raw=raw, parsed_ok=False)

    from_json = _from_json(raw)
    if from_json is not None:
        return Prediction(label=from_json, raw=raw, parsed_ok=True)

    leading = _leading_verdict(raw)
    if leading is not None:
        return Prediction(label=leading, raw=raw, parsed_ok=True)

    low = raw.lower()
    for marker in _NEG_MARKERS:
        if marker in low:
            return Prediction(label=0, raw=raw, parsed_ok=True)
    for marker in _POS_MARKERS:
        if marker in low:
            return Prediction(label=1, raw=raw, parsed_ok=True)
    if re.search(r"\byes\b", low):
        return Prediction(label=1, raw=raw, parsed_ok=True)
    if re.search(r"\bno\b", low):
        return Prediction(label=0, raw=raw, parsed_ok=True)

    return Prediction(label=0, raw=raw, parsed_ok=False)
