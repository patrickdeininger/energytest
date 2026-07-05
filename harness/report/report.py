"""Aggregate a run into a per-model metrics table + accuracy-vs-efficiency
Pareto plots. Uses a headless matplotlib backend so it runs anywhere.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from harness.scoring.detection import score  # noqa: E402

_PARETO = [
    ("usd_cost", "pareto_accuracy_vs_cost.png", "Mean USD / task"),
    ("total_ms", "pareto_accuracy_vs_latency.png", "Mean latency (ms)"),
    ("energy_j", "pareto_accuracy_vs_energy.png", "Mean energy (J)"),
]


def _load_rows(run_dir: Path) -> list[dict]:
    text = (run_dir / "results.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _col_mean(group, col: str) -> float:
    """Mean of a column, or NaN if the meter that produces it wasn't used
    (e.g. usd_cost is absent on local energy-only runs)."""
    return float(group[col].mean()) if col in group.columns else float("nan")


def build_report(run_dir) -> dict:
    run_dir = Path(run_dir)
    df = pd.DataFrame(_load_rows(run_dir))

    records = []
    for model_id, group in df.groupby("model_id"):
        all_rows = group.to_dict("records")
        parsed_rows = [r for r in all_rows if r.get("parsed_ok")]
        # Accuracy metrics over PARSED predictions only; a parse failure is a
        # reliability problem, reported separately via parse_rate/error_rate.
        s = score(parsed_rows)
        n_all = len(all_rows)
        error_rate = float(group["error"].notna().mean()) if "error" in group.columns else 0.0
        out_tok = float(group["output_tokens"].mean()) if "output_tokens" in group.columns else 0.0
        energy_source = group["energy_source"].iloc[0] if "energy_source" in group.columns else "unknown"
        records.append(
            {
                "model_id": model_id,
                "n": n_all,
                "n_parsed": len(parsed_rows),
                "parse_rate": (len(parsed_rows) / n_all if n_all else 0.0),
                "error_rate": error_rate,
                "accuracy": s["accuracy"],
                "precision": s["precision"],
                "recall": s["recall"],
                "f1": s["f1"],
                "out_tok_mean": out_tok,
                "usd_cost_mean": _col_mean(group, "usd_cost"),
                "total_ms_mean": _col_mean(group, "total_ms"),
                "energy_j_mean": _col_mean(group, "energy_j"),
                "active_energy_j_mean": _col_mean(group, "active_energy_j"),
                "energy_source": energy_source,
            }
        )
    metrics = pd.DataFrame(records).sort_values("model_id").reset_index(drop=True)
    metrics_csv = run_dir / "metrics.csv"
    metrics.to_csv(metrics_csv, index=False)

    plots = []
    for base_col, fname, xlabel in _PARETO:
        xcol = f"{base_col}_mean"
        if xcol not in metrics.columns or metrics[xcol].isna().all():
            continue  # skip axes whose meter wasn't used in this run
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.scatter(metrics[xcol], metrics["accuracy"])
        for _, r in metrics.iterrows():
            ax.annotate(r["model_id"], (r[xcol], r["accuracy"]),
                        textcoords="offset points", xytext=(4, 4), fontsize=8)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Accuracy")
        ax.set_title(f"Accuracy vs {xlabel}")
        fig.tight_layout()
        out = run_dir / fname
        fig.savefig(out, dpi=100)
        plt.close(fig)
        plots.append(out)

    return {"metrics_csv": metrics_csv, "plots": plots, "metrics": metrics}
