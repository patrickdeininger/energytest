"""Fold MEASURED (NVML) energy into the combined results and quantify how far the
FLOP-based estimate undershoots the real measurement (M3 validation).

The measured-energy run produces rows tagged energy_source="measured_nvml" with
energy_j=gross and active_energy_j=idle-subtracted. Because that run covers a
different task subset (N=300) than the API run (N=1549), we do not attach measured
energy per task; instead we report the measured MEAN active J/task per model and
overwrite the matching models' energy in the combined set, leaving accuracy and
cost untouched. The validation table then reports:

  - estimated_j        : mean FLOP-estimated J/task from the API run (the number the
                         paper currently reports for that model)
  - measured_active_j  : mean NVML energy minus idle baseline (comparable headline)
  - measured_gross_j   : mean NVML energy including idle
  - undershoot_ratio   : measured_active / estimated (headline: MoE undershoot ~2-3x)
  - j_per_output_token : sanity cross-check against the Samsi et al. ~3-4 J/token anchor
"""

from __future__ import annotations

from collections import defaultdict

# Samsi et al. (arXiv:2310.03003) report ~3-4 J per output token for LLM inference
# on datacenter GPUs; we use it as an external sanity band for our measurements.
SAMSI_ANCHOR_J_PER_TOKEN = (3.0, 4.0)


def _mean(vals) -> float:
    vals = list(vals)
    return sum(vals) / len(vals) if vals else float("nan")


def aggregate_measured(rows) -> dict:
    """Mean gross/active energy and output tokens over a measured run's rows."""
    rows = list(rows)
    n = len(rows)
    if n == 0:
        raise ValueError("no measured rows to aggregate")
    return {
        "mean_gross_j": _mean(r.get("energy_j", 0.0) or 0.0 for r in rows),
        "mean_active_j": _mean(r.get("active_energy_j", 0.0) or 0.0 for r in rows),
        "mean_output_tokens": _mean(r.get("output_tokens", 0) or 0 for r in rows),
        "n": n,
    }


def apply_measured_energy(rows, measured: dict) -> list[dict]:
    """Return a copy of `rows` with matched models' energy replaced by the measured
    mean active J/task. `measured` maps model_id -> {"active_j", "gross_j"}.

    Accuracy, cost, latency and token fields are preserved; only the energy fields
    and energy_source change, and the gross measurement is stashed in gross_energy_j.
    Input rows are not mutated.
    """
    out: list[dict] = []
    for r in rows:
        m = measured.get(r.get("model_id"))
        if m is None:
            out.append(r)
            continue
        r = dict(r)
        r["energy_j"] = m["active_j"]
        r["active_energy_j"] = m["active_j"]
        r["gross_energy_j"] = m.get("gross_j")
        r["energy_source"] = "measured_nvml"
        out.append(r)
    return out


def energy_validation_table(estimated_rows, measured: dict) -> list[dict]:
    """Measured-vs-estimated comparison, one row per measured model.

    `estimated_rows` are the API-run rows (carrying the FLOP estimate in energy_j);
    `measured` maps model_id -> {"active_j", "gross_j", "mean_output_tokens"}.
    """
    by = defaultdict(list)
    for r in estimated_rows:
        by[r.get("model_id")].append(r)

    lo, hi = SAMSI_ANCHOR_J_PER_TOKEN
    table: list[dict] = []
    for model_id, m in measured.items():
        est_rows = by.get(model_id, [])
        est_mean = _mean(r.get("energy_j", 0.0) or 0.0 for r in est_rows) if est_rows else float("nan")
        active = m["active_j"]
        mot = m.get("mean_output_tokens")
        jpt = active / mot if mot else None
        table.append({
            "model_id": model_id,
            "estimated_j": est_mean,
            "measured_active_j": active,
            "measured_gross_j": m.get("gross_j"),
            "undershoot_ratio": active / est_mean if est_mean else None,
            "mean_output_tokens": mot,
            "j_per_output_token": jpt,
            "within_samsi_anchor": jpt is not None and lo <= jpt <= hi,
        })
    return sorted(table, key=lambda d: d["model_id"])


def format_validation_markdown(table) -> str:
    """Render the validation table as GitHub-flavored markdown for notes/the paper."""
    header = (
        "| Model | Estimated J | Measured active J | Measured gross J | "
        "Undershoot x | J/output-tok | Within Samsi 3-4 |"
    )
    sep = "|" + "|".join(["---"] * 7) + "|"
    lines = [header, sep]
    for r in table:
        ratio = f"{r['undershoot_ratio']:.2f}" if r["undershoot_ratio"] is not None else "n/a"
        jpt = f"{r['j_per_output_token']:.2f}" if r["j_per_output_token"] is not None else "n/a"
        gross = f"{r['measured_gross_j']:.1f}" if r["measured_gross_j"] is not None else "n/a"
        lines.append(
            f"| {r['model_id']} | {r['estimated_j']:.1f} | {r['measured_active_j']:.1f} | "
            f"{gross} | {ratio} | {jpt} | {'yes' if r['within_samsi_anchor'] else 'no'} |"
        )
    return "\n".join(lines)
