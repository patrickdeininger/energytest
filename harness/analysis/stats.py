"""Statistics for results analysis.

Imbalance-robust metrics (balanced accuracy, MCC) and baselines matter here:
on a 549:1000 set an always-safe classifier scores 0.646 accuracy, so raw
accuracy is dominated by a trivial baseline and must not be the headline metric.
"""

from __future__ import annotations

import math


def ci95_halfwidth(k: int, n: int, z: float = 1.96) -> float:
    """Normal-approximation 95% CI half-width for a proportion k/n."""
    if n == 0:
        return 0.0
    p = k / n
    return z * math.sqrt(p * (1 - p) / n)


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion (better than normal approx at extremes)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (center - half, center + half)


def _chi2_df1_sf(x: float) -> float:
    """Survival function of chi-square with 1 dof: P(X > x) = erfc(sqrt(x/2))."""
    if x <= 0:
        return 1.0
    return math.erfc(math.sqrt(x / 2.0))


def mcnemar(correct_a, correct_b) -> dict:
    """Continuity-corrected McNemar test on two paired boolean sequences."""
    n10 = sum(1 for a, b in zip(correct_a, correct_b) if a and not b)
    n01 = sum(1 for a, b in zip(correct_a, correct_b) if b and not a)
    disc = n10 + n01
    if disc == 0:
        return {"n10": 0, "n01": 0, "statistic": 0.0, "p_value": 1.0}
    stat = (abs(n10 - n01) - 1) ** 2 / disc if abs(n10 - n01) >= 1 else 0.0
    return {"n10": n10, "n01": n01, "statistic": stat, "p_value": _chi2_df1_sf(stat)}


def majority_baseline_accuracy(labels) -> float:
    labels = list(labels)
    n = len(labels)
    if n == 0:
        return 0.0
    ones = sum(int(x) for x in labels)
    return max(ones, n - ones) / n


def balanced_accuracy(tp: int, fp: int, fn: int, tn: int) -> float:
    tpr = tp / (tp + fn) if (tp + fn) else 0.0
    tnr = tn / (tn + fp) if (tn + fp) else 0.0
    return 0.5 * (tpr + tnr)


def mcc(tp: int, fp: int, fn: int, tn: int) -> float:
    denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    if denom == 0:
        return 0.0
    return (tp * tn - fp * fn) / denom
