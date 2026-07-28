"""Final analysis: enriched per-model metrics (balanced accuracy, MCC, F1, CIs),
trivial baselines, McNemar significance tests, and publication Pareto figures.

    python -m harness.scripts.build_final_analysis
Writes: harness/runs/primevul_combined/enriched_metrics.csv and figures/*.pdf/png.
"""

from __future__ import annotations

import json
import math
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
from harness.analysis.energy_validation import apply_measured_energy  # noqa: E402

COMBINED = "harness/runs/primevul_combined/results.jsonl"
# Optional override written by fold_measured_energy.py: {model_id: {active_j, gross_j, ...}}.
# When present, the listed models' energy is swapped estimated -> measured before analysis.
MEASURED_OVERRIDE = "harness/runs/primevul_combined/measured_energy.json"
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
    override_path = Path(MEASURED_OVERRIDE)
    if override_path.exists():
        measured = json.loads(override_path.read_text(encoding="utf-8"))
        rows = apply_measured_energy(rows, measured)
        print(f"Applied measured energy override for: {', '.join(sorted(measured))}\n")
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
            "energy_source": rs[0].get("energy_source", "estimated_flops"),
        })
    return pd.DataFrame(recs).sort_values("bal_acc", ascending=False).reset_index(drop=True)


def pareto_fig(df, xcol, xlabel, fname):
    """Balanced-accuracy vs efficiency scatter, log x.

    No embedded title: the LaTeX \\caption carries it, and an in-figure title wide
    enough to describe the energy axis gets clipped at both ends by tight_layout.
    Point labels are placed on the side that keeps them inside the axes -- a fixed
    up-and-right offset ran the rightmost model names off the panel.
    """
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    colors = {"open": "#1f77b4", "frontier": "#d62728"}
    for tier in ("open", "frontier"):
        sub = df[df["tier"] == tier]
        ax.scatter(sub[xcol], sub["bal_acc"], c=colors[tier], label=tier, s=60, zorder=3)

    ax.set_xscale("log")
    # Pad the log x-range so labels have room inside the panel.
    lo, hi = df[xcol].min(), df[xcol].max()
    pad = (hi / lo) ** 0.10
    x0, x1 = lo / pad, hi * pad
    ax.set_xlim(x0, x1)

    def xfrac(x):  # position within the padded log range, 0..1
        return math.log10(x / x0) / math.log10(x1 / x0)

    # Three frontier models sit within ~0.01 balanced accuracy of each other, so a
    # single above/below flip is not enough -- step through vertical slots until one
    # is free of every label already placed nearby on the same side.
    SLOTS = (4, -11, -22, 15)
    placed = []  # (on_right, y, xfrac, dy) for labels already positioned
    for _, r in df.iterrows():
        xf = xfrac(r[xcol])
        on_right = xf > 0.60
        dx, ha = (-8, "right") if on_right else (8, "left")
        taken = {dy for prev_right, prev_y, prev_xf, dy in placed
                 if prev_right == on_right
                 and abs(r["bal_acc"] - prev_y) < 0.012
                 and abs(xf - prev_xf) < 0.30}
        dy = next((s for s in SLOTS if s not in taken), SLOTS[0])
        ax.annotate(r["model"], (r[xcol], r["bal_acc"]), textcoords="offset points",
                    xytext=(dx, dy), fontsize=7.5, ha=ha,
                    va="bottom" if dy > 0 else "top")
        placed.append((on_right, r["bal_acc"], xf, dy))

    ax.axhline(0.5, ls="--", c="grey", lw=1, zorder=1)
    # Autoscale only sees the markers, so the label above the top-scoring model
    # (DeepSeek-V3.2) lands on the top spine. Reserve a line's worth of headroom.
    ylo, yhi = ax.get_ylim()
    ax.set_ylim(ylo, yhi + 0.09 * (yhi - ylo))
    # Right-aligned: the left end of the baseline collides with the lowest model.
    ax.text(0.99, 0.012, "trivial baseline (0.5)", fontsize=7, color="grey",
            ha="right", va="bottom", transform=ax.transAxes)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Balanced accuracy")
    ax.legend(frameon=False, loc="lower right", bbox_to_anchor=(1.0, 0.06))
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

    any_measured = (df["energy_source"] == "measured_nvml").any()
    energy_label = ("Energy per task, J (log; measured for local open models)"
                    if any_measured else "Estimated energy per task, J (log)")
    pareto_fig(df, "usd_task", "USD per task (log)", "pareto_balacc_cost")
    pareto_fig(df, "energy_j", energy_label, "pareto_balacc_energy")
    print(f"\nWrote {out_csv} and figures/pareto_*.pdf/png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
