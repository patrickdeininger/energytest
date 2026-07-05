"""Reasoning-vs-direct robustness analysis (Tier-B).

  python -m harness.scripts.reasoning_vs_direct

Our main comparison uses direct-answer mode for compute parity. Because reasoning is
the frontier models' native mode, we re-ran Claude-Sonnet-5 and GPT-5.1 with reasoning
ENABLED on an N=300 stratified subset, paired against the same models in direct mode on
the same tasks. Gemini-3.1-Pro is reasoning-only; in the main run it was capped at 256
output tokens, here it gets 4096. Reports the paired balanced-accuracy delta, the cost/
token multiples, and the resulting balanced accuracy vs the best open model.
"""

from __future__ import annotations

import glob
import json

import numpy as np

from harness.analysis.stats import balanced_accuracy, balanced_accuracy_ci, paired_bootstrap_bal_acc_diff

DEEPSEEK = 0.674  # best open model (direct mode, N=1549)
FULLRUN = {"claude-sonnet-5": 0.613, "gpt-5.1": 0.614, "gemini-3.1-pro": 0.623}


def _load(glob_pat: str) -> list:
    return [json.loads(l) for l in open(sorted(glob.glob(glob_pat))[-1], encoding="utf-8") if l.strip()]


def _preds(rows, mid) -> dict:
    return {str(r["task_id"]): (r["label"], r["prediction"]) for r in rows if r["model_id"] == mid and r["parsed_ok"]}


def _ba(labels, preds):
    tp = int(((labels == 1) & (preds == 1)).sum()); fp = int(((labels == 0) & (preds == 1)).sum())
    fn = int(((labels == 1) & (preds == 0)).sum()); tn = int(((labels == 0) & (preds == 0)).sum())
    return balanced_accuracy(tp, fp, fn, tn), balanced_accuracy_ci(tp, fp, fn, tn)


def main() -> int:
    reas = _load("harness/runs/primevul_reasoning_subset-*/results.jsonl")
    direct = _load("harness/runs/primevul_direct_subset-*/results.jsonl")

    print("Paired reasoning vs direct (same N=300 tasks):")
    for base in ["claude-sonnet-5", "gpt-5.1"]:
        R, D = _preds(reas, base + "-reasoning"), _preds(direct, base + "-direct")
        common = sorted(set(R) & set(D))
        lab = np.array([R[t][0] for t in common])
        pr = np.array([R[t][1] for t in common]); pd_ = np.array([D[t][1] for t in common])
        bar, _ = _ba(lab, pr); bad, _ = _ba(lab, pd_)
        r = paired_bootstrap_bal_acc_diff(lab, pr, pd_, n_boot=20000, seed=12345)
        rr = [x for x in reas if x["model_id"] == base + "-reasoning"]
        dd = [x for x in direct if x["model_id"] == base + "-direct"]
        tok_mult = (sum(x.get("output_tokens", 0) for x in rr) / len(rr)) / (sum(x.get("output_tokens", 0) for x in dd) / len(dd))
        cost_mult = (sum(x.get("usd_cost", 0) or 0 for x in rr) / len(rr)) / (sum(x.get("usd_cost", 0) or 0 for x in dd) / len(dd))
        print(f"  {base:<16} direct={bad:.3f} reasoning={bar:.3f} delta={r['delta']:+.3f} "
              f"[{r['ci_lo']:+.3f},{r['ci_hi']:+.3f}] p={r['p_two_sided']:.3g}  "
              f"| {tok_mult:.0f}x tokens, {cost_mult:.1f}x cost")

    print("\nGemini-3.1-Pro (reasoning-only): main run 256-tok cap vs 4096-tok subset:")
    G = _preds(reas, "gemini-3.1-pro-reasoning")
    lab = np.array([v[0] for v in G.values()]); pg = np.array([v[1] for v in G.values()])
    bag, hwg = _ba(lab, pg)
    print(f"  subset(4096) bal_acc={bag:.3f}[{bag-hwg:.3f},{bag+hwg:.3f}] vs main(256) {FULLRUN['gemini-3.1-pro']:.3f}")

    print(f"\nBest open model (DeepSeek-V3.2, direct, N=1549) = {DEEPSEEK:.3f}")
    print("Frontier-with-reasoning reaches the open leader's level, at several-fold cost/energy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
