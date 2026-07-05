"""Revision statistics (Tier-A): the numbers the peer-review panel asked for.

  python -m harness.scripts.revision_stats

Produces, from harness/runs/primevul_combined/results.jsonl:
  1. Per-model balanced-accuracy 95% CI, MCC 95% CI (bootstrap), specificity, and
     precision at PrimeVul's natural 1:44 prevalence.
  2. The full 3x3 open-vs-frontier paired balanced-accuracy bootstrap matrix with
     Holm-corrected p-values (replaces the 2 cherry-picked McNemar-on-correctness tests).
  3. Frontier-energy sensitivity band over the assumed active-parameter count.
  4. Illustrative carbon numbers (energy -> gCO2eq) with explicit grid/PUE assumptions.
"""

from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from harness.analysis.stats import (
    balanced_accuracy, mcc, balanced_accuracy_ci, precision_at_prevalence,
    holm_bonferroni, paired_bootstrap_bal_acc_diff,
)

COMBINED = "harness/runs/primevul_combined/results.jsonl"
PREVALENCE = 549 / 24788               # PrimeVul test-split natural base rate (~1:44)
N_BOOT = 20000
SEED = 12345
OPEN = ["deepseek-v3.2", "gemma-3-4b", "glm-5"]          # the three top open models
FRONTIER = ["gemini-3.1-pro", "gpt-5.1", "claude-sonnet-5"]
LABEL = {
    "deepseek-v3.2": "DeepSeek-V3.2", "gemma-3-4b": "Gemma-3-4B", "glm-5": "GLM-5",
    "gemini-3.1-pro": "Gemini-3.1-Pro", "gpt-5.1": "GPT-5.1", "claude-sonnet-5": "Claude-Sonnet-5",
    "llama-3.3-70b": "Llama-3.3-70B", "qwen3-coder-30b": "Qwen3-Coder-30B",
}


def load():
    rows = [json.loads(l) for l in open(COMBINED, encoding="utf-8") if l.strip()]
    by = defaultdict(dict)   # model -> {task_id: (label, prediction)}
    for r in rows:
        if r["parsed_ok"]:
            by[r["model_id"]][r["task_id"]] = (r["label"], r["prediction"])
    return by


def confusion(pairs):
    tp = fp = fn = tn = 0
    for lab, pred in pairs.values():
        if lab == 1 and pred == 1: tp += 1
        elif lab == 0 and pred == 1: fp += 1
        elif lab == 1 and pred == 0: fn += 1
        else: tn += 1
    return tp, fp, fn, tn


def mcc_ci(pairs, seed=SEED, n_boot=N_BOOT):
    labels = np.array([lab for lab, _ in pairs.values()])
    preds = np.array([pred for _, pred in pairs.values()])
    pos, neg = np.flatnonzero(labels == 1), np.flatnonzero(labels == 0)
    rng = np.random.default_rng(seed)
    vals = np.empty(n_boot)
    for i in range(n_boot):
        idx = np.concatenate([rng.choice(pos, pos.size, True), rng.choice(neg, neg.size, True)])
        l, p = labels[idx], preds[idx]
        tp = int(((l == 1) & (p == 1)).sum()); fp = int(((l == 0) & (p == 1)).sum())
        fn = int(((l == 1) & (p == 0)).sum()); tn = int(((l == 0) & (p == 0)).sum())
        vals[i] = mcc(tp, fp, fn, tn)
    return tuple(np.percentile(vals, [2.5, 97.5]))


def main():
    by = load()

    print("=" * 78)
    print("1. PER-MODEL: balanced accuracy (95% CI), MCC (95% CI), specificity, precision@1:44")
    print("=" * 78)
    print(f"{'model':<18}{'bal_acc [95% CI]':<26}{'MCC [95% CI]':<24}{'spec':<7}{'prec@1:44':<10}")
    for m in OPEN + FRONTIER + ["llama-3.3-70b", "qwen3-coder-30b"]:
        tp, fp, fn, tn = confusion(by[m])
        ba = balanced_accuracy(tp, fp, fn, tn)
        hw = balanced_accuracy_ci(tp, fp, fn, tn)
        mlo, mhi = mcc_ci(by[m])
        spec = tn / (tn + fp)
        tpr = tp / (tp + fn)
        prec = precision_at_prevalence(tpr, spec, PREVALENCE)
        print(f"{LABEL[m]:<18}{ba:.3f} [{ba-hw:.3f},{ba+hw:.3f}]      "
              f"{mcc(tp,fp,fn,tn):.3f} [{mlo:.3f},{mhi:.3f}]   {spec:.3f}  {prec*100:.1f}%")

    print("\n" + "=" * 78)
    print("2. OPEN vs FRONTIER: paired balanced-accuracy bootstrap (delta, 95% CI, Holm p)")
    print("=" * 78)
    pairs, raw_p = [], []
    for o in OPEN:
        for f in FRONTIER:
            common = sorted(set(by[o]) & set(by[f]))
            labels = np.array([by[o][t][0] for t in common])
            po = np.array([by[o][t][1] for t in common])
            pf = np.array([by[f][t][1] for t in common])
            r = paired_bootstrap_bal_acc_diff(labels, po, pf, n_boot=N_BOOT, seed=SEED)
            pairs.append((o, f, r))
            raw_p.append(r["p_two_sided"])
    holm = holm_bonferroni(raw_p)
    for (o, f, r), hp in zip(pairs, holm):
        sig = "***" if hp < 1e-3 else "**" if hp < 1e-2 else "*" if hp < 0.05 else "n.s."
        print(f"  {LABEL[o]:<16} vs {LABEL[f]:<16} d={r['delta']:+.3f} "
              f"[{r['ci_lo']:+.3f},{r['ci_hi']:+.3f}]  p_raw={r['p_two_sided']:.3g}  p_Holm={hp:.3g}  {sig}")

    print("\n" + "=" * 78)
    print("3. FRONTIER ENERGY SENSITIVITY (energy is proportional to assumed active params)")
    print("=" * 78)
    # current estimate assumes ~100B active; Gemma-3-4B measured/known small
    gemma_j = 64.0
    for fm, base_j in [("Claude-Sonnet-5", 2489.0), ("GPT-5.1", 1332.0), ("Gemini-3.1-Pro", 1966.0)]:
        print(f"  {fm} (est. {base_j:.0f} J at 100B assumed):")
        for nb in (25, 100, 400):
            scaled = base_j * nb / 100
            print(f"     at {nb:>3}B active -> {scaled:7.0f} J  = {scaled/gemma_j:5.1f}x Gemma-3-4B ({gemma_j:.0f} J)")

    print("\n" + "=" * 78)
    print("4. ILLUSTRATIVE CARBON (operational GPU energy -> gCO2eq; PUE=1.2)")
    print("=" * 78)
    for intensity, region in [(0.25, "EU-ish grid"), (0.475, "world avg")]:
        print(f"  grid {intensity*1000:.0f} gCO2/kWh ({region}), PUE 1.2:")
        for m, j, src in [("Gemma-3-4B", 64.0, "est"), ("Qwen3-Coder-30B", 88.0, "measured"),
                          ("Claude-Sonnet-5", 2489.0, "est")]:
            kwh = j / 3.6e6
            g_task = kwh * 1.2 * intensity * 1000   # grams CO2 per task
            kg_million = g_task * 1000              # grams/task * 1e6 functions / 1000 g/kg
            print(f"     {m:<18}({src:<8}) {g_task*1000:7.2f} mgCO2/task  ->  {kg_million:7.1f} kg / 1M functions")


if __name__ == "__main__":
    main()
