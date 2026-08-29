"""Configuration-matched families A, B and C, all within one measurement epoch.

  python -m harness.scripts.families_analysis

Reviewer 1 asked for three comparisons by name -- the same token budget, the
models' normal configuration, and their best-performing configuration -- and
Reviewers 2 and 3 asked for the same thing in other words. This builds all three
from the August epoch so no comparison crosses the seven-week service drift.

  A  budget-matched direct: every model at 64 output tokens, reasoning disabled
     wherever the provider permits it
  B  native: each reasoning-capable model with reasoning enabled at a 4096-token
     budget; the others as in A, which IS their native configuration
  C  best observed: each model's highest score across every configuration we ran

The DeepSeek reasoning arm is read from a corrective run: the provider originally
pinned for it accepted reasoning:{enabled:true} and silently ignored it (131 mean
output tokens against 1771 in the earlier epoch), so that arm measured direct
answering under a reasoning label. Preferring the corrective run here is not
cherry-picking -- the discarded arm did not run the configuration it claimed.
"""

from __future__ import annotations

import glob
import json
from collections import defaultdict

from harness.analysis.stats import balanced_accuracy, paired_bootstrap_bal_acc_diff

DIRECT = "harness/runs/r2_anchor64-*/results.jsonl"
REASON = "harness/runs/r2_reasoning-*/results.jsonl"
REASON_FIX = "harness/runs/r2_reasoning_deepseek_fix-*/results.jsonl"

DISPLAY = {
    "deepseek-v3.2": "DeepSeek-V3.2", "gemma-3-4b": "Gemma-3-4B", "glm-5": "GLM-5",
    "gemini-3.1-pro": "Gemini-3.1-Pro", "gpt-5.1": "GPT-5.1",
    "claude-sonnet-5": "Claude-Sonnet-5", "llama-3.3-70b": "Llama-3.3-70B",
    "qwen3-coder-30b": "Qwen3-Coder-30B",
}
TIER = {
    "deepseek-v3.2": "open", "gemma-3-4b": "open", "glm-5": "open",
    "llama-3.3-70b": "open", "qwen3-coder-30b": "open",
    "claude-sonnet-5": "frontier", "gpt-5.1": "frontier", "gemini-3.1-pro": "frontier",
}


def load(pattern):
    f = sorted(glob.glob(pattern))
    if not f:
        return {}
    per = defaultdict(dict)
    for line in open(f[0], encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            per[r["model_id"]][str(r["task_id"])] = r
    return per


def stats(rows):
    p = [r for r in rows.values() if r.get("parsed_ok")]
    tp = sum(1 for r in p if r["label"] == 1 and r["prediction"] == 1)
    fn = sum(1 for r in p if r["label"] == 1 and r["prediction"] == 0)
    fp = sum(1 for r in p if r["label"] == 0 and r["prediction"] == 1)
    tn = sum(1 for r in p if r["label"] == 0 and r["prediction"] == 0)
    return {
        "ba": balanced_accuracy(tp, fp, fn, tn),
        "parse": len(p) / max(len(rows), 1),
        "usd": sum((r.get("usd_cost") or 0) for r in rows.values()) / max(len(rows), 1),
        "out": sum((r.get("output_tokens") or 0) for r in rows.values()) / max(len(rows), 1),
        "n": len(rows),
    }


def main() -> int:
    direct = load(DIRECT)
    reason = load(REASON)
    fix = load(REASON_FIX)

    # Prefer the corrective DeepSeek arm when it is complete.
    if fix.get("deepseek-v3.2-reasoning") and len(fix["deepseek-v3.2-reasoning"]) >= 1500:
        reason["deepseek-v3.2-reasoning"] = fix["deepseek-v3.2-reasoning"]
        print("using the corrective DeepSeek reasoning arm (StreamLake)\n")
    elif fix.get("deepseek-v3.2-reasoning"):
        print(f"NOTE: corrective DeepSeek arm incomplete "
              f"({len(fix['deepseek-v3.2-reasoning'])}/1549); excluding it\n")
        reason.pop("deepseek-v3.2-reasoning", None)

    print(f"{'Model':18s} {'tier':9s} {'A direct':>9s} {'B native':>9s} "
          f"{'delta':>8s} {'p':>8s} {'C best':>8s} {'A $/task':>9s} {'B $/task':>9s} {'B/A $':>7s}")
    print("-" * 106)
    rows = []
    for m in sorted(direct, key=lambda x: -stats(direct[x])["ba"]):
        d = stats(direct[m])
        rk = f"{m}-reasoning"
        if rk not in reason:
            best = d["ba"]
            print(f"{DISPLAY[m]:18s} {TIER[m]:9s} {d['ba']:9.3f} {'--':>9s} {'--':>8s} "
                  f"{'--':>8s} {best:8.3f} {d['usd']:9.5f} {'--':>9s} {'--':>7s}")
            rows.append((m, d["ba"], None, best))
            continue
        r = stats(reason[rk])
        ids = sorted(t for t in direct[m]
                     if t in reason[rk] and direct[m][t].get("parsed_ok")
                     and reason[rk][t].get("parsed_ok"))
        labels = [direct[m][t]["label"] for t in ids]
        bs = paired_bootstrap_bal_acc_diff(
            labels, [reason[rk][t]["prediction"] for t in ids],
            [direct[m][t]["prediction"] for t in ids], n_boot=20000, seed=12345)
        star = "*" if bs["p_two_sided"] < 0.05 else " "
        best = max(d["ba"], r["ba"])
        ratio = r["usd"] / d["usd"] if d["usd"] else float("nan")
        print(f"{DISPLAY[m]:18s} {TIER[m]:9s} {d['ba']:9.3f} {r['ba']:9.3f} "
              f"{bs['delta']:+8.4f} {bs['p_two_sided']:7.4f}{star} {best:8.3f} "
              f"{d['usd']:9.5f} {r['usd']:9.5f} {ratio:6.1f}x")
        rows.append((m, d["ba"], r["ba"], best))

    print("\nFamily C (best observed) ranking:")
    for m, a, b, best in sorted(rows, key=lambda x: -x[3]):
        src = "reasoning" if b is not None and b > a else "direct"
        print(f"   {DISPLAY[m]:18s} {best:.3f}  ({src})")

    open_best = max((b for m, _, _, b in rows if TIER[m] == "open"), default=0)
    front_best = max((b for m, _, _, b in rows if TIER[m] == "frontier"), default=0)
    print(f"\n   best open {open_best:.3f} vs best frontier {front_best:.3f} "
          f"-> gap {open_best - front_best:+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
