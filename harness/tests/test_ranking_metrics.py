"""Tests for dependency-free ROC-AUC and average precision.

Validated against scikit-learn's values, but the implementations must not
depend on it: the reproduction package should run on a bare GPU pod, and a
lean environment is worth more than the convenience of importing sklearn for
two closed-form statistics.
"""

import pytest

from harness.analysis.stats import average_precision, roc_auc


def test_perfect_separation():
    assert roc_auc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == pytest.approx(1.0)


def test_perfectly_inverted():
    assert roc_auc([0, 0, 1, 1], [0.9, 0.8, 0.2, 0.1]) == pytest.approx(0.0)


def test_no_signal_is_one_half():
    # All scores identical: every pair is a tie, which counts as half.
    assert roc_auc([0, 1, 0, 1], [0.5] * 4) == pytest.approx(0.5)


def test_ties_are_credited_as_half():
    # sklearn: roc_auc_score([0,1], [0.5,0.5]) == 0.5
    assert roc_auc([0, 1], [0.5, 0.5]) == pytest.approx(0.5)
    # 3 clean concordant pairs + 1 tied pair counted as half -> 3.5/4
    assert roc_auc([0, 0, 1, 1], [0.1, 0.5, 0.5, 0.9]) == pytest.approx(0.875)


def test_known_value_matches_sklearn():
    y = [0, 0, 1, 1, 0, 1, 0, 1, 1, 0]
    s = [0.1, 0.4, 0.35, 0.8, 0.2, 0.6, 0.15, 0.7, 0.55, 0.3]
    # sklearn.metrics.roc_auc_score(y, s) == 0.96
    assert roc_auc(y, s) == pytest.approx(0.96, abs=1e-9)


def test_roc_auc_is_scale_and_shift_invariant():
    y = [0, 1, 0, 1, 1]
    s = [0.1, 0.9, 0.3, 0.7, 0.5]
    assert roc_auc(y, s) == pytest.approx(roc_auc(y, [3 * x + 10 for x in s]))


def test_roc_auc_undefined_without_both_classes():
    with pytest.raises(ValueError):
        roc_auc([1, 1, 1], [0.1, 0.2, 0.3])


def test_average_precision_perfect():
    assert average_precision([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == pytest.approx(1.0)


def test_average_precision_matches_sklearn():
    y = [0, 0, 1, 1]
    s = [0.1, 0.4, 0.35, 0.8]
    # sklearn.metrics.average_precision_score(y, s) == 0.8333333333333333
    assert average_precision(y, s) == pytest.approx(0.8333333333333333, abs=1e-9)


def test_average_precision_all_positive_is_one():
    assert average_precision([1, 1, 1], [0.2, 0.5, 0.9]) == pytest.approx(1.0)


def test_average_precision_floor_is_the_positive_rate():
    """With no signal, AP tends to the base rate rather than 0.5."""
    y = [1] + [0] * 9
    ap = average_precision(y, [0.5] * 10)
    assert ap == pytest.approx(0.1, abs=1e-9)


def test_scores_below_a_half_still_rank():
    """The case that motivated this: a collapsed classifier whose every score is
    under 0.5 but whose ranking is still perfect."""
    y = [0, 0, 1, 1]
    s = [0.002, 0.004, 0.30, 0.37]
    assert roc_auc(y, s) == pytest.approx(1.0)
    assert average_precision(y, s) == pytest.approx(1.0)
