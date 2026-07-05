"""Build the combined 8-model PrimeVul report: the 5 valid non-reasoning models
from the first full run + the 3 reasoning models re-run in the fill run.

Run after the fill run completes:
    python -m harness.scripts.build_combined_report
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import pandas as pd

from harness.analysis.merge import merge_results, write_merged
from harness.report.report import build_report

VALID_FROM_FIRST = ["deepseek-v3.2", "gemma-3-4b", "gpt-5.1", "llama-3.3-70b", "qwen3-coder-30b"]
FROM_FILL = ["claude-sonnet-5", "glm-5", "gemini-3.1-pro"]
TIER = {
    "gpt-5.1": "frontier", "claude-sonnet-5": "frontier", "gemini-3.1-pro": "frontier",
    "gemma-3-4b": "open", "qwen3-coder-30b": "open", "llama-3.3-70b": "open",
    "deepseek-v3.2": "open", "glm-5": "open",
}


def main() -> int:
    first = sorted(glob.glob("harness/runs/primevul_full-*/"))[-1]
    fill = "harness/runs/primevul_fill_main"
    out = "harness/runs/primevul_combined"

    rows = merge_results([(first, VALID_FROM_FIRST), (fill, FROM_FILL)])
    write_merged(rows, out)
    # copy a lightweight provenance note
    Path(out, "PROVENANCE.txt").write_text(
        f"Combined report.\n5 valid models from: {first}\n3 reasoning models from: {fill}\n"
        "Caveat: fill models ran at max_output_tokens=256 vs 64 for the first-run 5; "
        "accuracy unaffected (verdict emitted first), efficiency axes carry that asterisk.\n",
        encoding="utf-8",
    )
    rep = build_report(out)
    m = rep["metrics"].copy()
    m["tier"] = m["model_id"].map(TIER)
    cols = ["model_id", "tier", "n_parsed", "parse_rate", "accuracy", "f1", "recall",
            "out_tok_mean", "usd_cost_mean", "energy_j_mean"]
    m = m[cols].sort_values("accuracy", ascending=False)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 20)
    print(f"Combined PrimeVul report -> {out}\n")
    print(m.to_string(index=False))
    print(f"\nrows: {len(rows)} | models: {m['model_id'].nunique()} | plots + metrics.csv in {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
