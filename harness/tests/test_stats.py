"""Tests for statistics used in the results analysis: CIs, McNemar, baselines,
and imbalance-robust metrics (balanced accuracy, MCC)."""

import math

from pytest import approx

from harness.analysis.stats import (
    wilson_interval,
    ci95_halfwidth,
    mcnemar,
    majority_baseline_accuracy,
    balanced_accuracy,
    mcc,
)


def test_ci95_halfwidth_at_p_half():
    # 1.96*sqrt(0.25/1549) ~= 0.0249
    assert ci95_halfwidth(775, 1549) == approx(0.0249, abs=1e-3)
    assert ci95_halfwidth(0, 0) == 0.0


def test_wilson_interval_brackets_point_estimate():
    lo, hi = wilson_interval(627, 1000)
    assert lo < 0.627 < hi
    assert 0.0 <= lo < hi <= 1.0
    assert (hi - lo) == approx(0.06, abs=0.02)  # ~+-3pp


def test_mcnemar_continuity_corrected():
    # n10=30 (a right, b wrong), n01=10 -> stat=(|20|-1)^2/40 = 9.025
    correct_a = [True] * 30 + [False] * 10 + [True] * 5 + [False] * 5
    correct_b = [False] * 30 + [True] * 10 + [True] * 5 + [False] * 5
    r = mcnemar(correct_a, correct_b)
    assert r["n10"] == 30 and r["n01"] == 10
    assert r["statistic"] == approx(9.025, abs=1e-3)
    assert r["p_value"] < 0.05


def test_mcnemar_no_discordant_pairs():
    r = mcnemar([True, False], [True, False])
    assert r["n10"] == 0 and r["n01"] == 0
    assert r["p_value"] == 1.0


def test_majority_baseline_accuracy():
    assert majority_baseline_accuracy([1, 1, 1, 0, 0]) == approx(0.6)
    # 549 vuln + 1000 safe -> always-safe = 1000/1549
    labels = [1] * 549 + [0] * 1000
    assert majority_baseline_accuracy(labels) == approx(1000 / 1549, abs=1e-6)


def test_balanced_accuracy_is_half_for_trivial_classifiers():
    # always-safe: tp=0, fn=549, tn=1000, fp=0 -> (0 + 1)/2 = 0.5
    assert balanced_accuracy(tp=0, fp=0, fn=549, tn=1000) == approx(0.5)
    # perfect
    assert balanced_accuracy(tp=549, fp=0, fn=0, tn=1000) == approx(1.0)


def test_mcc_zero_for_trivial_and_defined_for_balanced():
    assert mcc(tp=0, fp=0, fn=549, tn=1000) == 0.0  # degenerate -> 0
    assert mcc(tp=549, fp=0, fn=0, tn=1000) == approx(1.0)
