"""Tests for the vulnerability-detection scoring function.

Positive class = vulnerable (label 1). score() is a pure function over a list of
result rows, each a dict with integer `label`, integer `prediction` (0/1), and
boolean `parsed_ok`. How a parse failure maps to a prediction is the parser's
concern, not scoring's — scoring just computes the confusion matrix + rates.
"""

from harness.scoring.detection import score


def rows(specs):
    """specs: list of (true_label, prediction, parsed_ok) tuples."""
    return [
        {"label": lbl, "prediction": pred, "parsed_ok": ok}
        for (lbl, pred, ok) in specs
    ]


def test_perfect_predictions():
    s = score(rows([(1, 1, True), (1, 1, True), (0, 0, True), (0, 0, True)]))
    assert s["n"] == 4
    assert (s["tp"], s["fp"], s["fn"], s["tn"]) == (2, 0, 0, 2)
    assert s["accuracy"] == 1.0
    assert s["precision"] == 1.0
    assert s["recall"] == 1.0
    assert s["f1"] == 1.0
    assert s["parse_rate"] == 1.0


def test_mixed_confusion_and_f1():
    # tp=2, fp=1, fn=1, tn=1
    s = score(rows([(1, 1, True), (1, 1, True), (0, 1, True), (1, 0, True), (0, 0, True)]))
    assert (s["tp"], s["fp"], s["fn"], s["tn"]) == (2, 1, 1, 1)
    assert s["accuracy"] == 3 / 5
    assert s["precision"] == 2 / 3
    assert s["recall"] == 2 / 3
    assert abs(s["f1"] - 2 / 3) < 1e-9  # 2PR/(P+R) with P=R=2/3


def test_no_positive_predictions_gives_zero_precision_recall_f1():
    s = score(rows([(1, 0, True), (0, 0, True)]))
    assert s["precision"] == 0.0
    assert s["recall"] == 0.0
    assert s["f1"] == 0.0


def test_parse_rate_counts_parsed_ok_fraction():
    s = score(rows([(1, 1, True), (0, 0, False), (1, 0, False), (0, 0, True)]))
    assert s["parse_rate"] == 0.5


def test_empty_returns_zeros_without_crashing():
    s = score([])
    assert s["n"] == 0
    assert s["accuracy"] == 0.0
    assert s["f1"] == 0.0
    assert s["parse_rate"] == 0.0
