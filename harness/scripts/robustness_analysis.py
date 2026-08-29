"""Robustness of the ranking to prompt, sample draw, and run-to-run variation (R2#6, R3#4).

  python -m harness.scripts.robustness_analysis

The headline table rests on one prompt template, one draw of the safe pool, and one
generation per item. The paired bootstrap bounds none of those: it resamples within
the sample we drew. This compares the anchor run against:

  prompt   two paraphrases, each altering exactly one property of the anchor prompt
           (v2 removes the expert persona, v3 reverses the order the two answers are
           offered in), so a shift is attributable rather than merely observed;

  draw     two further independent draws of the 1000 safe functions. PrimeVul's test
           split holds only 549 vulnerable functions, so every draw contains all of
           them and only the negatives vary -- which is precisely the quantity in
           question, and it leaves the positive set fixed as a control;

  rerun    because those positives ARE fixed, re-running them measures generation
           variance at temperature 0 under an unchanged configuration, at no extra
           cost. Reported on the positive subset only, where the comparison is paired
           item-for-item.

What matters is not whether individual scores move but whether the ORDERING does, so
the rank correlation between each variant and the anchor is reported alongside.
"""

from __future__ import annotations

import glob
import json
from collections import defaultdict

from harness.analysis.stats import balanced_accuracy, paired_bootstrap_bal_acc_diff

ANCHOR = "harness/runs/r2_anchor64-*/results.jsonl"
VARIANTS = {
    "prompt v2 (no persona)": "harness/runs/r2_prompt_v2-*/results.jsonl",
    "prompt v3 (order flipped)": "harness/runs/r2_prompt_v3-*/results.jsonl",
    "safe draw 2 (seed 999)": "harness/runs/r2_draw2-*/results.jsonl",
    "safe draw 3 (seed 4242)": "harness/runs/r2_draw3-*/results.jsonl",
}


def load(pattern):
    f = sorted(glob.glob(pattern))
    if not f:
        return None
    per = defaultdict(dict)
    for line in open(f[0], encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            per[r["model_id"]][str(r["task_id"])] = r
    return per


def bal_acc(rows):
    # The runner writes every negative before any positive, so a partial run has
    # no positives and yields a balanced accuracy near 0.5*specificity -- a number
    # that looks like collapse rather than an unfinished file. Refuse it.
    if not any(r["label"] == 1 for r in rows.values()):
        return float("nan"), 0
    p = [r for r in rows.values() if r.get("parsed_ok")]
    tp = sum(1 for r in p if r["label"] == 1 and r["prediction"] == 1)
    fn = sum(1 for r in p if r["label"] == 1 and r["prediction"] == 0)
    fp = sum(1 for r in p if r["label"] == 0 and r["prediction"] == 1)
    tn = sum(1 for r in p if r["label"] == 0 and r["prediction"] == 0)
    return balanced_accuracy(tp, fp, fn, tn), len(p)


def spearman(a, b):
    """Rank correlation without scipy; n is 8, so ties are handled by average rank."""
    def ranks(xs):
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        r = [0.0] * len(xs)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return num / den if den else float("nan")


def main() -> int:
    anchor = load(ANCHOR)
    if not anchor:
        raise SystemExit("anchor run not found")
    models = sorted(anchor)
    base = {m: bal_acc(anchor[m])[0] for m in models}

    print("Anchor (prompt v1, seed 12345, 64 tokens):")
    for m in sorted(models, key=lambda x: -base[x]):
        print(f"   {m:20s} {base[m]:.4f}")

    for label, pattern in VARIANTS.items():
        var = load(pattern)
        if not var:
            print(f"\n{label}: not yet available")
            continue
        done = all(len(var[m]) >= 1500 for m in models if m in var)
        tag = "" if done else "   [INCOMPLETE -- partial run, ordering only]"
        print(f"\n{label}{tag}")
        print(f"   {'model':20s} {'anchor':>8s} {'variant':>8s} {'delta':>8s} "
              f"{'p':>8s} {'n_common':>9s}")
        vals = []
        for m in models:
            if m not in var:
                continue
            bv, _ = bal_acc(var[m])
            if bv != bv:  # NaN: single-class partial run
                print(f"   {m:20s} {base[m]:8.4f} {'(partial)':>8s}")
                continue
            vals.append((m, bv))
            ids = sorted(t for t in anchor[m]
                         if t in var[m] and anchor[m][t].get("parsed_ok")
                         and var[m][t].get("parsed_ok"))
            if len(ids) < 100:
                print(f"   {m:20s} {base[m]:8.4f} {bv:8.4f} {'--':>8s} {'--':>8s} {len(ids):9d}")
                continue
            labels = [anchor[m][t]["label"] for t in ids]
            r = paired_bootstrap_bal_acc_diff(
                labels, [var[m][t]["prediction"] for t in ids],
                [anchor[m][t]["prediction"] for t in ids], n_boot=20000, seed=12345)
            star = "*" if r["p_two_sided"] < 0.05 else " "
            print(f"   {m:20s} {base[m]:8.4f} {bv:8.4f} {r['delta']:+8.4f} "
                  f"{r['p_two_sided']:8.4f}{star} {len(ids):8d}")
        if len(vals) >= 3:
            common = [m for m, _ in vals]
            rho = spearman([base[m] for m in common], [v for _, v in vals])
            worst = max(abs(v - base[m]) for m, v in vals)
            print(f"   -> Spearman rank correlation with the anchor: {rho:.3f}; "
                  f"largest absolute shift {worst:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
