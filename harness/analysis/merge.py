"""Merge results across runs.

Used to combine still-valid models from one run with re-run models from another
(e.g. the 5 non-reasoning models from the first PrimeVul run + the 3 reasoning
models from the fill run) into one results set for a combined report.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_results(run_dir) -> list[dict]:
    path = Path(run_dir) / "results.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def merge_results(sources: list[tuple]) -> list[dict]:
    """sources: list of (run_dir, model_ids_to_keep). model_ids=None keeps all.

    Later sources win only in the sense that each source contributes its own
    selected model rows; callers should not list the same model in two sources.
    """
    merged: list[dict] = []
    for run_dir, model_ids in sources:
        rows = load_results(run_dir)
        if model_ids is not None:
            keep = set(model_ids)
            rows = [r for r in rows if r.get("model_id") in keep]
        merged.extend(rows)
    return merged


def write_merged(rows: list[dict], out_dir) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "results.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return out_dir
