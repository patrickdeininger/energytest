"""Final analysis: enriched per-model metrics (balanced accuracy, MCC, F1, CIs),
trivial baselines, McNemar significance tests, and publication Pareto figures.

    python -m harness.scripts.build_final_analysis
Writes: harness/runs/primevul_combined/enriched_metrics.csv and figures/*.pdf/png.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from harness.scoring.detection import score  # noqa: E402
from harness.analysis.stats import (  # noqa: E402
    ci95_halfwidth, balanced_accuracy, mcc, mcnemar, majority_baseline_accuracy,
)

COMBINED = "harness/runs/primevul_combined/results.jsonl"
FIGDIR = Path("figures")
TIER = {
    "gpt-5.1": "frontier", "claude-sonnet-5": "frontier", "gemini-3.1-pro": "frontier",
    "gemma-3-4b": "open", "qwen3-coder-30b": "open", "llama-3.3-70b": "open",
    "deepseek-v3.2": "open", "glm-5": "open",
}
LABEL = {
    "gpt-5.1": "GPT-5.1", "claude-sonnet-5": "Claude-Sonnet-5", "gemini-3.1-pro": "Gemini-3.1-Pro",
    "gemma-3-4b": "Gemma-3-4B", "qwen3-coder-30b": "Qwen3-Coder-30B", "llama-3.3-70b": "Llama-3.3-70B",
    "deepseek-v3.2": "DeepSeek-V3.2", "glm-5": "GLM-5",
}


def load_by_model():
    rows = [json.loads(l) for l in open(COMBINED, encoding="utf-8") if l.strip()]
    by = defaultdict(list)
    for r in rows:
        by[r["model_id"]].append(r)
    return by


def enriched(by) -> pd.DataFrame:
    recs = []
    for m, rs in by.items():
        parsed = [r for r in rs if r["parsed_ok"]]
        s = score(parsed)
        recs.append({
            "model": LABEL[m], "tier": TIER[m],
            "bal_acc": balanced_accuracy(s["tp"], s["fp"], s["fn"], s["tn"]),
            "mcc": mcc(s["tp"], s["fp"], s["fn"], s["tn"]),
            "f1": s["f1"], "accuracy": s["accuracy"],
            "acc_ci95": ci95_halfwidth(round(s["accuracy"] * s["n"]), s["n"]),
            "recall": s["recall"],
            "specificity": s["tn"] / (s["tn"] + s["fp"]) if (s["tn"] + s["fp"]) else 0.0,
            "usd_task": sum(r.get("usd_cost", 0) or 0 for r in rs) / len(rs),
            "energy_j": sum(r.get("energy_j", 0) or 0 for r in rs) / len(rs),
        })
    return pd.DataFrame(recs).sort_values("bal_acc", ascending=False).reset_index(drop=True)


def pareto_fig(df, xcol, xlabel, fname):
    fig, ax = plt.subplots(figsize=(6, 4.2))
    colors = {"open": "#1f77b4", "frontier": "#d62728"}
    for tier in ("open", "frontier"):
        sub = df[df["tier"] == tier]
        ax.scatter(sub[xcol], sub["bal_acc"], c=colors[tier], label=tier, s=60, zorder=3)
    for _, r in df.iterrows():
        ax.annotate(r["model"], (r[xcol], r["bal_acc"]),
                    textcoords="offset points", xytext=(5, 4), fontsize=7.5)
    ax.axhline(0.5, ls="--", c="grey", lw=1, zorder=1)
    ax.text(df[xcol].min(), 0.505, "trivial baseline (0.5)", fontsize=7, color="grey")
    ax.set_xscale("log")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Balanced accuracy")
    ax.set_title(f"Detection quality vs {xlabel}")
    ax.legend(frameon=False)
    fig.tight_layout()
    FIGDIR.mkdir(exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(FIGDIR / f"{fname}.{ext}", dpi=150)
    plt.close(fig)


def main() -> int:
    by = load_by_model()
    labels = [r["label"] for r in next(iter(by.values()))]
    df = enriched(by)
    out_csv = Path("harness/runs/primevul_combined/enriched_metrics.csv")
    df.to_csv(out_csv, index=False)

    pd.set_option("display.width", 200)
    print("Baselines: always-safe acc=%.3f | always-vuln acc=%.3f | trivial balanced-acc=0.500"
          % (labels.count(0) / len(labels), labels.count(1) / len(labels)))
    print(f"(N={len(labels)}, majority={majority_baseline_accuracy(labels):.3f})\n")
    print(df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    def corr(m):
        return {r["task_id"]: r["correct"] for r in by[m] if r["parsed_ok"]}
    print("\nMcNemar (paired):")
    for a, b in [("deepseek-v3.2", "gpt-5.1"), ("gemma-3-4b", "claude-sonnet-5")]:
        da, db = corr(a), corr(b)
        common = sorted(set(da) & set(db))
        r = mcnemar([da[t] for t in common], [db[t] for t in common])
        print(f"  {LABEL[a]} vs {LABEL[b]}: n={len(common)}, chi2={r['statistic']:.2f}, p={r['p_value']:.2e}")

    pareto_fig(df, "usd_task", "USD per task (log)", "pareto_balacc_cost")
    pareto_fig(df, "energy_j", "Estimated energy per task, J (log)", "pareto_balacc_energy")
    print(f"\nWrote {out_csv} and figures/pareto_*.pdf/png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
