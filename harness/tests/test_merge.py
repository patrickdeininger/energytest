"""Tests for merging results across runs (e.g. valid models from one run +
re-run models from another)."""

import json
from pathlib import Path

from harness.analysis.merge import merge_results, write_merged


def _mk(tmp_path, name, rows):
    d = tmp_path / name
    d.mkdir()
    (d / "results.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return str(d)


def test_merge_selects_specified_models_from_each_source(tmp_path):
    d1 = _mk(tmp_path, "run1", [{"model_id": "a", "x": 1}, {"model_id": "b", "x": 2}, {"model_id": "c", "x": 3}])
    d2 = _mk(tmp_path, "run2", [{"model_id": "c", "x": 9}, {"model_id": "d", "x": 4}])
    merged = merge_results([(d1, ["a", "b"]), (d2, ["c", "d"])])
    assert sorted(r["model_id"] for r in merged) == ["a", "b", "c", "d"]
    # 'c' must come from d2 (the re-run), not d1
    assert next(r["x"] for r in merged if r["model_id"] == "c") == 9


def test_merge_none_keeps_all_models(tmp_path):
    d1 = _mk(tmp_path, "r", [{"model_id": "a"}, {"model_id": "b"}])
    assert len(merge_results([(d1, None)])) == 2


def test_write_merged_creates_results_jsonl(tmp_path):
    rows = [{"model_id": "a", "x": 1}, {"model_id": "b", "x": 2}]
    out = tmp_path / "merged"
    write_merged(rows, out)
    written = [json.loads(l) for l in (Path(out) / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert written == rows
