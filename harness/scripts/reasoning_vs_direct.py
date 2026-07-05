"""Reasoning-vs-direct robustness analysis (Tier-B, full N=1549).

  python -m harness.scripts.reasoning_vs_direct

Our main comparison uses direct-answer mode for compute parity. Because reasoning is
the frontier models' native mode, we re-ran all three frontier models with reasoning
ENABLED on the full N=1549 (4096-token budget), paired against their direct-mode
predictions from the main run (Gemini is reasoning-only; its main run was capped at
256 tokens). Reports the paired balanced-accuracy delta and significance, and the
resulting balanced accuracy vs the best open model.
"""

from __future__ import annotations

import glob
import json

import numpy as np

from harness.analysis.stats import balanced_accuracy, balanced_accuracy_ci, paired_bootstrap_bal_acc_diff

DEEPSEEK = 0.676  # best open model (direct mode, N=1549)
GEMINI_MAIN = 0.623  # Gemini main-run score at the 256-token cap


def _load(glob_pat: str) -> list:
    return [json.loads(l) for l in open(sorted(glob.glob(glob_pat))[-1], encoding="utf-8") if l.strip()]


def _preds(rows, mid) -> dict:
    return {str(r["task_id"]): (r["label"], r["prediction"]) for r in rows if r["model_id"] == mid and r["parsed_ok"]}


def _ba(P: dict):
    lab = np.array([v[0] for v in P.values()]); p = np.array([v[1] for v in P.values()])
    tp = int(((lab == 1) & (p == 1)).sum()); fp = int(((lab == 0) & (p == 1)).sum())
    fn = int(((lab == 1) & (p == 0)).sum()); tn = int(((lab == 0) & (p == 0)).sum())
    return balanced_accuracy(tp, fp, fn, tn), balanced_accuracy_ci(tp, fp, fn, tn)


def main() -> int:
    reas = _load("harness/runs/primevul_reasoning_full-*/results.jsonl")
    direct = _load("harness/runs/primevul_combined/results.jsonl")

    print("Paired reasoning vs direct (full N=1549):")
    for base in ["claude-sonnet-5", "gpt-5.1"]:
        R = _preds(reas, base + "-reasoning"); D = _preds(direct, base)
        common = sorted(set(R) & set(D))
        lab = np.array([R[t][0] for t in common])
        pr = np.array([R[t][1] for t in common]); pd_ = np.array([D[t][1] for t in common])
        bar, hwr = _ba({t: R[t] for t in common}); bad, _ = _ba({t: D[t] for t in common})
        r = paired_bootstrap_bal_acc_diff(lab, pr, pd_, n_boot=20000, seed=12345)
        rr = [x for x in reas if x["model_id"] == base + "-reasoning"]
        dd = [x for x in direct if x["model_id"] == base]
        tok_mult = (sum(x.get("output_tokens", 0) for x in rr) / len(rr)) / (sum(x.get("output_tokens", 0) for x in dd) / len(dd))
        cost_mult = (sum(x.get("usd_cost", 0) or 0 for x in rr) / len(rr)) / (sum(x.get("usd_cost", 0) or 0 for x in dd) / len(dd))
        print(f"  {base:<16} direct={bad:.3f} reasoning={bar:.3f}[{bar-hwr:.3f},{bar+hwr:.3f}] "
              f"delta={r['delta']:+.3f}[{r['ci_lo']:+.3f},{r['ci_hi']:+.3f}] p={r['p_two_sided']:.3g}  "
              f"| {tok_mult:.0f}x tokens, {cost_mult:.1f}x cost")

    G = _preds(reas, "gemini-3.1-pro-reasoning")
    bag, hwg = _ba(G)
    print(f"\nGemini-3.1-Pro (reasoning-only): full reasoning bal_acc={bag:.3f}[{bag-hwg:.3f},{bag+hwg:.3f}] "
          f"vs main run at 256-tok cap {GEMINI_MAIN:.3f}")
    print(f"\nBest open model (DeepSeek-V3.2, direct) = {DEEPSEEK:.3f}: reasoning brings the frontier to parity at the top, not past it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
