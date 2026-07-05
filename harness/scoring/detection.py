"""Binary vulnerability-detection scoring.

Positive class = vulnerable (label 1). Pure function over result rows.
"""

from __future__ import annotations

from typing import Iterable, Mapping


def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def score(results: Iterable[Mapping]) -> dict:
    """Compute detection metrics from result rows.

    Each row is a mapping with integer `label`, integer `prediction` (0/1),
    and boolean `parsed_ok`. Returns confusion counts, accuracy, precision,
    recall, F1, and parse_rate. Empty input returns zeros (no crash).
    """
    rows = list(results)
    n = len(rows)
    tp = fp = fn = tn = 0
    parsed = 0
    for r in rows:
        label = int(r["label"])
        pred = int(r["prediction"])
        if r.get("parsed_ok", True):
            parsed += 1
        if label == 1 and pred == 1:
            tp += 1
        elif label == 0 and pred == 1:
            fp += 1
        elif label == 1 and pred == 0:
            fn += 1
        else:  # label == 0 and pred == 0
            tn += 1

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    accuracy = _safe_div(tp + tn, n)
    parse_rate = _safe_div(parsed, n)

    return {
        "n": n,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "parse_rate": parse_rate,
    }
