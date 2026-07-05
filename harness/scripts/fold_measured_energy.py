"""Fold measured (NVML) energy for the local open models into the combined report.

Run this the moment the RunPod measured-energy tables are back. It swaps the
FLOP estimate for the real measurement on the named models, writes a
measured-vs-estimated validation table, and (by default) regenerates the enriched
metrics + Pareto figures via build_final_analysis.

Two ways to supply each model's measurement (canonical model_id on the left):

  # (a) point at the model's local_energy run directory (reads its results.jsonl)
  python -m harness.scripts.fold_measured_energy \
      --from-dir qwen3-coder-30b=harness/runs/local_energy_qwen \
      --from-dir llama-3.3-70b=harness/runs/local_energy_llama

  # (b) paste the numbers directly: active_j,gross_j,mean_output_tokens
  python -m harness.scripts.fold_measured_energy \
      --set qwen3-coder-30b=88.9,130.8,25 \
      --set llama-3.3-70b=...

Writes into <combined>/: measured_energy.json (consumed by build_final_analysis),
energy_validation.md and energy_validation.csv. Pass --no-regen to skip figures.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from harness.analysis.merge import load_results
from harness.analysis.energy_validation import (
    aggregate_measured,
    energy_validation_table,
    format_validation_markdown,
)

DEFAULT_COMBINED = "harness/runs/primevul_combined"


def _measured_from_dir(run_dir: str) -> dict:
    agg = aggregate_measured(load_results(run_dir))
    return {
        "active_j": agg["mean_active_j"],
        "gross_j": agg["mean_gross_j"],
        "mean_output_tokens": agg["mean_output_tokens"],
        "n": agg["n"],
        "source": run_dir,
    }


def _measured_from_set(spec: str) -> dict:
    parts = [float(x) for x in spec.split(",")]
    if len(parts) < 2:
        raise SystemExit(f"--set needs active_j,gross_j[,mean_output_tokens], got '{spec}'")
    active, gross = parts[0], parts[1]
    mot = parts[2] if len(parts) > 2 else None
    return {"active_j": active, "gross_j": gross, "mean_output_tokens": mot, "source": "pasted"}


def _parse_kv(items, fn) -> dict:
    out = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"expected MODEL_ID=..., got '{item}'")
        model_id, val = item.split("=", 1)
        out[model_id.strip()] = fn(val.strip())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--combined", default=DEFAULT_COMBINED, help="combined run dir")
    ap.add_argument("--from-dir", action="append", metavar="MODEL_ID=RUNDIR",
                    help="read a model's measurement from a local_energy run dir")
    ap.add_argument("--set", dest="set_", action="append", metavar="MODEL_ID=active,gross[,tok]",
                    help="supply a model's measurement inline")
    ap.add_argument("--no-regen", action="store_true", help="skip regenerating figures/metrics")
    args = ap.parse_args()

    measured: dict = {}
    measured.update(_parse_kv(args.from_dir, _measured_from_dir))
    measured.update(_parse_kv(args.set_, _measured_from_set))
    if not measured:
        raise SystemExit("nothing to fold: pass at least one --from-dir or --set")

    combined = Path(args.combined)
    estimated_rows = load_results(combined)

    # measured_energy.json: consumed by build_final_analysis to swap estimated->measured
    (combined / "measured_energy.json").write_text(
        json.dumps(measured, indent=2), encoding="utf-8")

    table = energy_validation_table(estimated_rows, measured)
    md = format_validation_markdown(table)
    (combined / "energy_validation.md").write_text(md + "\n", encoding="utf-8")
    with (combined / "energy_validation.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0].keys()))
        w.writeheader()
        w.writerows(table)

    print(md)
    print(f"\nWrote {combined/'measured_energy.json'}, energy_validation.md, energy_validation.csv")

    if not args.no_regen:
        print("\nRegenerating enriched metrics + Pareto figures ...\n")
        from harness.scripts.build_final_analysis import main as build_main
        build_main()
    else:
        print("Skipped regen (--no-regen). Run: python -m harness.scripts.build_final_analysis")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
