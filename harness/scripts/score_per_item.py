"""Threshold-free scoring for any per-item score file.

  python -m harness.scripts.score_per_item <per_item.jsonl> [--prevalence 0.02214]

Reads JSONL rows of {label, score} and reports ROC-AUC, PR-AUC, the
best-balanced-accuracy operating point, and the operating points a deployer
would actually care about at the natural base rate.

This exists because argmax hides ranking. Our first PrimeVul fine-tune produced
recall 0 and balanced accuracy exactly 0.5, which looks like a model that learned
nothing; the scores underneath told a different story. Any conclusion drawn from
a single fixed threshold on an imbalanced problem should be checked here first.

Works on the LLM confidence-elicitation runs too, where `score` is the elicited
P(vulnerable) -- that is what supplies the PR curves and VD-Score that a binary
verdict cannot.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PREVALENCE = 549 / 24788


def load(path: Path):
    ys, ss = [], []
    for line in open(path, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("score") is None:
            continue
        ys.append(int(r["label"]))
        ss.append(float(r["score"]))
    return ys, ss


def confusion(ys, ss, thr):
    tp = sum(1 for y, s in zip(ys, ss) if s >= thr and y == 1)
    fp = sum(1 for y, s in zip(ys, ss) if s >= thr and y == 0)
    fn = sum(1 for y, s in zip(ys, ss) if s < thr and y == 1)
    tn = sum(1 for y, s in zip(ys, ss) if s < thr and y == 0)
    return tp, fp, fn, tn


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--prevalence", type=float, default=PREVALENCE)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    ys, ss = load(Path(args.path))
    n_pos, n_neg = sum(ys), len(ys) - sum(ys)
    print(f"{len(ys)} scored items: {n_pos} vulnerable, {n_neg} safe")
    print(f"score range [{min(ss):.4f}, {max(ss):.4f}]")
    if max(ss) < 0.5:
        print("NOTE: every score is below 0.5, so an argmax/0.5 cut predicts "
              "'safe' for everything. That is a thresholding artifact, not an "
              "absence of signal -- read the AUC below.")

    from harness.analysis.stats import average_precision, roc_auc

    auc = roc_auc(ys, ss)
    ap_score = average_precision(ys, ss)
    print(f"\nROC-AUC {auc:.4f}   (0.5 = no ranking signal)")
    print(f"PR-AUC  {ap_score:.4f}   (baseline = positive rate {n_pos/len(ys):.4f})")

    best = None
    for thr in sorted({round(s, 4) for s in ss}):
        tp, fp, fn, tn = confusion(ys, ss, thr)
        tpr = tp / max(tp + fn, 1)
        tnr = tn / max(tn + fp, 1)
        ba = 0.5 * (tpr + tnr)
        if best is None or ba > best["bal_acc"]:
            best = {"threshold": thr, "bal_acc": ba, "recall": tpr, "specificity": tnr,
                    "tp": tp, "fp": fp}
    print(f"\nbest balanced accuracy {best['bal_acc']:.4f} at threshold "
          f"{best['threshold']:.4f}  (recall {best['recall']:.3f}, "
          f"specificity {best['specificity']:.3f}, tp={best['tp']}, fp={best['fp']})")

    # What a deployer sees at the natural base rate, across the sweep.
    pi = args.prevalence
    print(f"\noperating points at prevalence {pi:.5f} (1 in {1/pi:.0f}):")
    print(f"{'thr':>8s} {'recall':>7s} {'FPR':>7s} {'prec%':>7s} {'FP/TP':>8s} {'bal_acc':>8s}")
    for q in (0.50, 0.80, 0.90, 0.95, 0.99):
        thr = sorted(ss)[min(int(q * len(ss)), len(ss) - 1)]
        tp, fp, fn, tn = confusion(ys, ss, thr)
        tpr = tp / max(tp + fn, 1)
        fpr = fp / max(fp + tn, 1)
        denom = tpr * pi + fpr * (1 - pi)
        prec = (tpr * pi / denom) if denom else 0.0
        print(f"{thr:8.4f} {tpr:7.3f} {fpr:7.3f} {prec*100:7.2f} "
              f"{((1-prec)/prec if prec else float('inf')):8.1f} "
              f"{0.5*(tpr+(1-fpr)):8.4f}")

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"n": len(ys), "roc_auc": auc, "pr_auc": ap_score, "best": best},
            indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
