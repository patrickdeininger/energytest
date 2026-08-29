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


def balanced_accuracy_ci(tp: int, fp: int, fn: int, tn: int, z: float = 1.96) -> float:
    """Normal-approximation 95% CI half-width for balanced accuracy.

    bal_acc = 0.5*(TPR + TNR) with TPR ~ Binomial over the n_pos positives and TNR
    ~ Binomial over the n_neg negatives (independent), so
    Var(bal_acc) = 0.25*(Var(TPR) + Var(TNR)). This is the interval that belongs on
    the *primary* metric (the raw-accuracy CI does not describe the ranking).
    """
    n_pos, n_neg = tp + fn, tn + fp
    if n_pos == 0 or n_neg == 0:
        return 0.0
    tpr, tnr = tp / n_pos, tn / n_neg
    var = 0.25 * (tpr * (1 - tpr) / n_pos + tnr * (1 - tnr) / n_neg)
    return z * math.sqrt(var)


def precision_at_prevalence(tpr: float, tnr: float, prevalence: float) -> float:
    """Precision (PPV) a model with these operating-point rates would achieve at a
    given base rate: PPV = TPR*p / (TPR*p + (1-TNR)*(1-p)). Lets us translate a
    balanced-sample result to the deployment prevalence without re-running anything.
    """
    fpr = 1 - tnr
    denom = tpr * prevalence + fpr * (1 - prevalence)
    return tpr * prevalence / denom if denom > 0 else 0.0


def holm_bonferroni(pvalues) -> list:
    """Holm-Bonferroni step-down adjusted p-values, returned in the input order.

    Controls the family-wise error rate across the pairwise comparisons without the
    conservatism of plain Bonferroni.
    """
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        val = min(1.0, (m - rank) * pvalues[idx])
        running = max(running, val)  # enforce monotonic non-decreasing
        adjusted[idx] = running
    return adjusted


def _bal_acc_from_arrays(labels, preds) -> float:
    import numpy as np

    pos = labels == 1
    neg = ~pos
    tpr = preds[pos].mean() if pos.any() else 0.0
    tnr = (1 - preds[neg]).mean() if neg.any() else 0.0
    return 0.5 * (tpr + tnr)


def paired_bootstrap_bal_acc_diff(labels, preds_a, preds_b, n_boot: int = 10000, seed: int = 0) -> dict:
    """Stratified paired bootstrap of the balanced-accuracy difference (A - B).

    Positives and negatives are resampled independently (preserving the 549:1000
    design), and the same resampled task indices are applied to both models so the
    comparison stays paired. Returns the observed delta, a percentile 95% CI, and a
    two-sided bootstrap p-value for H0: delta = 0. This is the test that matches the
    ranking metric (balanced accuracy) -- unlike McNemar on raw correctness.
    """
    import numpy as np

    labels = np.asarray(labels)
    a = np.asarray(preds_a)
    b = np.asarray(preds_b)
    pos_idx = np.flatnonzero(labels == 1)
    neg_idx = np.flatnonzero(labels == 0)
    delta_obs = _bal_acc_from_arrays(labels, a) - _bal_acc_from_arrays(labels, b)

    rng = np.random.default_rng(seed)
    deltas = np.empty(n_boot)
    for i in range(n_boot):
        rp = rng.choice(pos_idx, size=pos_idx.size, replace=True)
        rn = rng.choice(neg_idx, size=neg_idx.size, replace=True)
        idx = np.concatenate([rp, rn])
        lab = labels[idx]
        deltas[i] = _bal_acc_from_arrays(lab, a[idx]) - _bal_acc_from_arrays(lab, b[idx])

    ci_lo, ci_hi = np.percentile(deltas, [2.5, 97.5])
    p = 2.0 * min((deltas <= 0).mean(), (deltas >= 0).mean())
    return {
        "delta": float(delta_obs),
        "ci_lo": float(ci_lo),
        "ci_hi": float(ci_hi),
        "p_two_sided": float(min(1.0, p)),
    }


def roc_auc(labels, scores) -> float:
    """Area under the ROC curve, computed from ranks (Mann-Whitney U).

    Dependency-free on purpose: the reproduction package must run on a bare GPU
    pod, and pulling scikit-learn (and scipy, and numpy) in for one closed-form
    statistic is not worth it.

    Ties contribute exactly one half, matching scikit-learn, via average ranks.
    """
    pairs = sorted(zip(scores, labels))
    n = len(pairs)
    n_pos = sum(int(y) for _, y in pairs)
    n_neg = n - n_pos
    if n_pos == 0 or n_neg == 0:
        raise ValueError("ROC-AUC is undefined unless both classes are present")

    # Average ranks within groups of equal score, so ties split evenly.
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # ranks are 1-based
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1

    rank_sum = sum(r for r, (_, y) in zip(ranks, pairs) if int(y) == 1)
    return (rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def average_precision(labels, scores) -> float:
    """Average precision, the step-wise sum used by scikit-learn:
    AP = sum_k (R_k - R_{k-1}) * P_k over thresholds, descending by score.

    Unlike ROC-AUC its no-signal floor is the positive rate, not 0.5, which is
    why it is the more informative of the two on an imbalanced problem.
    """
    pairs = sorted(zip(scores, labels), key=lambda t: -t[0])
    n_pos = sum(int(y) for _, y in pairs)
    if n_pos == 0:
        return 0.0

    ap = 0.0
    tp = fp = 0
    prev_recall = 0.0
    i = 0
    while i < len(pairs):
        # Consume the whole tie group before measuring: a threshold cannot
        # separate items that share a score.
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        for k in range(i, j + 1):
            if int(pairs[k][1]) == 1:
                tp += 1
            else:
                fp += 1
        recall = tp / n_pos
        precision = tp / (tp + fp)
        ap += (recall - prev_recall) * precision
        prev_recall = recall
        i = j + 1
    return ap
