"""Deployment utility at realistic prevalence (paper Section 4.5).

The balanced 549:1000 evaluation sample answers "which model is least
miscalibrated". It does not answer "what happens if I point this at a codebase",
because precision depends on prevalence and PrimeVul's real test split is 1:44.
Reviewers 1 and 2 both asked for this to be elevated out of the discussion and
expanded, so this script computes, from the per-item predictions we already hold:

  * precision, false positives per true positive, and alert volume at the natural
    base rate, against the always-flag baseline on the same axes;
  * cost and energy per true positive found -- the paper's own efficiency axes
    applied to the deployment question;
  * a prevalence sweep for the figure;
  * the human review workload implied by each model's achieved recall.

TPR and FPR are prevalence-invariant, so they transfer from the balanced sample
to any base rate; only the mix changes. That is the whole trick, and it is why
these numbers need no new inference.

Usage: python -m harness.scripts.prevalence_analysis [--run DIR] [--json OUT]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

# PrimeVul test split as loaded by the harness: 549 vulnerable of 24,788.
N_TEST_TOTAL = 24_788
N_TEST_VULN = 549
NATURAL_PREVALENCE = N_TEST_VULN / N_TEST_TOTAL  # 0.02214 -> about 1:44

DEFAULT_RUN = Path("harness/runs/primevul_combined")
TIERS = {
    "deepseek-v3.2": "open", "gemma-3-4b": "open", "glm-5": "open",
    "llama-3.3-70b": "open", "qwen3-coder-30b": "open",
    "claude-sonnet-5": "frontier", "gpt-5.1": "frontier", "gemini-3.1-pro": "frontier",
}
DISPLAY = {
    "deepseek-v3.2": "DeepSeek-V3.2", "gemma-3-4b": "Gemma-3-4B", "glm-5": "GLM-5",
    "gemini-3.1-pro": "Gemini-3.1-Pro", "gpt-5.1": "GPT-5.1",
    "claude-sonnet-5": "Claude-Sonnet-5", "llama-3.3-70b": "Llama-3.3-70B",
    "qwen3-coder-30b": "Qwen3-Coder-30B",
}


def load_rows(run_dir: Path):
    per = defaultdict(list)
    with (run_dir / "results.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                per[r["model_id"]].append(r)
    return per


def rates(rows):
    """TPR/FPR over parsed predictions only; parse failures are excluded, never
    silently counted as 'safe' (which would inflate specificity).

    Guards against reading an in-flight run. The runner emits every negative
    before any positive, so a partial results.jsonl has no positives at all and
    yields recall 0.000 and a meaningless balanced accuracy -- a number that looks
    like a catastrophic model failure rather than an incomplete file."""
    if not any(r["label"] == 1 for r in rows) or not any(r["label"] == 0 for r in rows):
        raise ValueError(
            f"run contains only one class ({len(rows)} rows) -- it is still in "
            "flight. Metrics from a partial run are not interpretable because the "
            "runner writes all negatives before any positive."
        )
    parsed = [r for r in rows if r.get("parsed_ok")]
    tp = sum(1 for r in parsed if r["label"] == 1 and r["prediction"] == 1)
    fn = sum(1 for r in parsed if r["label"] == 1 and r["prediction"] == 0)
    fp = sum(1 for r in parsed if r["label"] == 0 and r["prediction"] == 1)
    tn = sum(1 for r in parsed if r["label"] == 0 and r["prediction"] == 0)
    return {
        "n_parsed": len(parsed),
        "tpr": tp / (tp + fn) if tp + fn else 0.0,
        "fpr": fp / (fp + tn) if fp + tn else 0.0,
        "usd_task": sum(r.get("usd_cost") or 0 for r in parsed) / max(len(parsed), 1),
        "energy_j": sum(r.get("energy_j") or 0 for r in parsed) / max(len(parsed), 1),
    }


def deployment(tpr: float, fpr: float, prevalence: float, per_n: int = 1000) -> dict:
    """Confusion counts and derived quantities per `per_n` scanned functions."""
    tp = per_n * prevalence * tpr
    fp = per_n * (1 - prevalence) * fpr
    fn = per_n * prevalence * (1 - tpr)
    alerts = tp + fp
    precision = tp / alerts if alerts else 0.0
    return {
        "precision": precision,
        "fp_per_tp": (fp / tp) if tp else float("inf"),
        "alerts_per_1k": alerts,
        "tp_per_1k": tp,
        "missed_per_1k": fn,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(DEFAULT_RUN))
    ap.add_argument("--prevalence", type=float, default=NATURAL_PREVALENCE)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    per = load_rows(Path(args.run))
    pi = args.prevalence
    out = {"prevalence": pi, "models": {}}

    print(f"Natural prevalence {pi:.5f}  (1 vulnerable in {1/pi:.0f})")
    print(f"Always-flag baseline precision = {pi*100:.2f}%\n")

    hdr = (f"{'Model':22s} {'tier':9s} {'TPR':>6s} {'FPR':>6s} {'Prec%':>7s} "
           f"{'FP/TP':>7s} {'Alerts/1k':>10s} {'TP/1k':>6s} {'USD/TP':>9s} {'kJ/TP':>8s}")
    print(hdr)
    print("-" * len(hdr))

    rows_out = []
    for mid, rows in per.items():
        r = rates(rows)
        d = deployment(r["tpr"], r["fpr"], pi)
        # Cost/energy per TRUE POSITIVE FOUND: what one real finding actually costs,
        # which is the deployment-relevant version of the paper's efficiency axes.
        usd_per_tp = r["usd_task"] / (pi * r["tpr"]) if r["tpr"] else float("inf")
        kj_per_tp = (r["energy_j"] / (pi * r["tpr"])) / 1000 if r["tpr"] else float("inf")
        rec = {
            "model": DISPLAY.get(mid, mid), "tier": TIERS.get(mid, "?"),
            **r, **d, "usd_per_tp": usd_per_tp, "kj_per_tp": kj_per_tp,
        }
        rows_out.append(rec)
        out["models"][mid] = rec

    for rec in sorted(rows_out, key=lambda x: -x["precision"]):
        print(f"{rec['model']:22s} {rec['tier']:9s} {rec['tpr']:6.3f} {rec['fpr']:6.3f} "
              f"{rec['precision']*100:7.2f} {rec['fp_per_tp']:7.1f} "
              f"{rec['alerts_per_1k']:10.1f} {rec['tp_per_1k']:6.2f} "
              f"{rec['usd_per_tp']:9.3f} {rec['kj_per_tp']:8.1f}")

    # Flawfinder, which unlike the LLMs exposes a sweepable threshold (risk level).
    ff_path = Path("harness/runs/flawfinder_baseline/flawfinder_scores.json")
    if ff_path.exists():
        print("\nFlawfinder (static analysis) across its risk-level thresholds:")
        print(f"{'thr':>4s} {'TPR':>6s} {'FPR':>6s} {'Prec%':>7s} {'FP/TP':>7s} {'bal_acc':>8s}")
        ff_out = []
        for e in json.load(ff_path.open(encoding="utf-8")):
            tpr = e["recall"]; fpr = 1 - e["specificity"]
            d = deployment(tpr, fpr, pi)
            print(f"{e['threshold']:>4d} {tpr:6.3f} {fpr:6.3f} {d['precision']*100:7.2f} "
                  f"{d['fp_per_tp']:7.1f} {e['bal_acc']:8.3f}")
            ff_out.append({"threshold": e["threshold"], "tpr": tpr, "fpr": fpr,
                           "bal_acc": e["bal_acc"], **d})
        out["flawfinder"] = ff_out

    # Prevalence sweep for the figure.
    sweep = {}
    for mid, rows in per.items():
        r = rates(rows)
        sweep[DISPLAY.get(mid, mid)] = [
            {"prevalence": p, "precision": deployment(r["tpr"], r["fpr"], p)["precision"]}
            for p in (0.10, 0.05, 0.02214, 0.01, 0.005, 0.002)
        ]
    out["sweep"] = sweep

    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
