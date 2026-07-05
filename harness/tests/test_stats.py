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
    balanced_accuracy_ci,
    precision_at_prevalence,
    holm_bonferroni,
    paired_bootstrap_bal_acc_diff,
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


def test_balanced_accuracy_ci_halfwidth():
    # DeepSeek-V3.2: tp=460, fp=489, fn=89, tn=511 (n_pos=549, n_neg=1000)
    # var = 0.25*(tpr(1-tpr)/n_pos + tnr(1-tnr)/n_neg); hw = 1.96*sqrt(var) ~= 0.0219
    hw = balanced_accuracy_ci(tp=460, fp=489, fn=89, tn=511)
    assert hw == approx(0.0219, abs=1e-3)
    # perfect classifier -> zero variance
    assert balanced_accuracy_ci(tp=549, fp=0, fn=0, tn=1000) == approx(0.0)
    assert balanced_accuracy_ci(tp=0, fp=0, fn=0, tn=0) == 0.0


def test_precision_at_prevalence():
    # perfect discrimination stays perfect at any prevalence
    assert precision_at_prevalence(tpr=1.0, tnr=1.0, prevalence=0.02) == approx(1.0)
    # balanced coin at balanced prevalence -> 0.5
    assert precision_at_prevalence(tpr=0.5, tnr=0.5, prevalence=0.5) == approx(0.5)
    # DeepSeek at PrimeVul natural prevalence 549/24788 -> ~3.7% precision
    prev = 549 / 24788
    assert precision_at_prevalence(tpr=460 / 549, tnr=511 / 1000, prevalence=prev) == approx(0.037, abs=3e-3)
    assert precision_at_prevalence(tpr=0.0, tnr=1.0, prevalence=0.02) == 0.0  # never flags -> undefined -> 0


def test_holm_bonferroni_adjusts_and_stays_monotone():
    # sorted ascending: 0.01, 0.03, 0.04 (m=3): 0.03, 0.06, 0.06 (cumulative max), mapped back to input order
    adj = holm_bonferroni([0.01, 0.04, 0.03])
    assert adj[0] == approx(0.03)
    assert adj[1] == approx(0.06)
    assert adj[2] == approx(0.06)
    # adjusted p-values are capped at 1.0
    assert all(0.0 <= p <= 1.0 for p in holm_bonferroni([0.5, 0.9, 0.8]))


def test_paired_bootstrap_bal_acc_diff():
    labels = [1, 1, 0, 0]
    perfect = [1, 1, 0, 0]   # bal_acc 1.0
    worst = [0, 0, 1, 1]     # bal_acc 0.0
    r = paired_bootstrap_bal_acc_diff(labels, perfect, worst, n_boot=500, seed=0)
    assert r["delta"] == approx(1.0)
    assert r["p_two_sided"] < 0.05
    # identical predictions -> zero difference, non-significant
    same = paired_bootstrap_bal_acc_diff(labels, perfect, perfect, n_boot=500, seed=0)
    assert same["delta"] == approx(0.0)
    assert same["p_two_sided"] == approx(1.0)
    # deterministic for a fixed seed
    a = paired_bootstrap_bal_acc_diff(labels, perfect, worst, n_boot=500, seed=7)
    b = paired_bootstrap_bal_acc_diff(labels, perfect, worst, n_boot=500, seed=7)
    assert a["p_two_sided"] == b["p_two_sided"] and a["ci_lo"] == b["ci_lo"]
