"""Tests for config-driven backend construction and the jsonl dataset source."""

import json
from pathlib import Path

import pytest

from harness.config import RunConfig, ModelSpec, make_backend
from harness.backends.api import APIBackend
from harness.backends.mock import MockBackend
from harness.runner import run


def test_make_backend_mock():
    spec = ModelSpec(id="m", backend="mock", params={"behavior": "balanced"})
    assert isinstance(make_backend(spec, seed=0), MockBackend)


def test_make_backend_api_returns_apibackend_with_resolved_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    spec = ModelSpec(
        id="claude",
        backend="api",
        params={"provider": "openrouter", "model": "anthropic/claude-sonnet"},
    )
    backend = make_backend(spec, seed=0)
    assert isinstance(backend, APIBackend)
    assert backend.model == "anthropic/claude-sonnet"


def test_make_backend_unknown_backend_raises():
    with pytest.raises(ValueError):
        make_backend(ModelSpec(id="x", backend="nope"), seed=0)


def test_make_backend_unknown_provider_raises():
    spec = ModelSpec(id="x", backend="api", params={"provider": "no-such-provider"})
    with pytest.raises(ValueError):
        make_backend(spec, seed=0)


def _mock_cfg(tmp_path, concurrency):
    return RunConfig(
        run_name="c",
        seed=1,
        dataset={"source": "fixture", "path": "harness/data/fixtures/primevul_mini.jsonl"},
        models=[
            {"id": "a", "backend": "mock", "params": {"behavior": "always_vulnerable"}},
            {"id": "b", "backend": "mock", "params": {"behavior": "balanced"}},
        ],
        meters=["cost", "latency", "energy_mock"],
        reps=2,
        concurrency=concurrency,
        output_dir=str(tmp_path / "runs"),
    )


def _pred_key(run_dir):
    rows = [
        json.loads(l)
        for l in (Path(run_dir) / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    return sorted((r["model_id"], r["task_id"], r["rep"], r["prediction"]) for r in rows)


def test_concurrency_produces_same_results_as_serial(tmp_path):
    serial = run(_mock_cfg(tmp_path, 1), run_id="serial", timestamp="t")
    parallel = run(_mock_cfg(tmp_path, 4), run_id="parallel", timestamp="t")
    assert _pred_key(serial) == _pred_key(parallel)


def test_manifest_records_concurrency(tmp_path):
    d = run(_mock_cfg(tmp_path, 3), run_id="m", timestamp="t")
    manifest = json.loads((Path(d) / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["config"]["concurrency"] == 3


def test_resume_keeps_completed_rows_and_skips_recomputation(tmp_path):
    cfg = _mock_cfg(tmp_path, 1)  # models a,b x fixture tasks x 2 reps
    run_dir = Path(cfg.output_dir) / "r"
    run_dir.mkdir(parents=True)
    # Pre-seed 3 completed rows with a distinctive marker.
    preseed = [("a", "v1", 0), ("a", "v2", 0), ("b", "v1", 0)]
    with (run_dir / "results.jsonl").open("w", encoding="utf-8") as f:
        for (m, t, rp) in preseed:
            f.write(json.dumps({
                "model_id": m, "task_id": t, "rep": rp, "label": 1,
                "prediction": 1, "parsed_ok": True, "preseeded": True,
            }) + "\n")

    run(cfg, run_id="r", timestamp="t")

    rows = [
        json.loads(l)
        for l in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    # Resume kept the pre-seeded rows (did NOT recompute them).
    assert sum(1 for r in rows if r.get("preseeded")) == 3
    # No duplicate (model, task, rep) keys.
    keys = [(r["model_id"], r["task_id"], r["rep"]) for r in rows]
    assert len(keys) == len(set(keys))


def test_runner_records_call_errors_without_aborting(tmp_path):
    cfg = RunConfig(
        run_name="e",
        seed=1,
        dataset={"source": "fixture", "path": "harness/data/fixtures/primevul_mini.jsonl", "n": 4, "stratify_by": "label"},
        models=[
            {"id": "ok", "backend": "mock", "params": {"behavior": "always_vulnerable"}},
            {"id": "bad", "backend": "mock", "params": {"behavior": "error"}},
        ],
        meters=["cost", "latency", "energy_mock"],
        reps=1,
        output_dir=str(tmp_path / "runs"),
    )
    run_dir = run(cfg, run_id="e", timestamp="t")
    rows = [
        json.loads(l)
        for l in (Path(run_dir) / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    assert len(rows) == 8  # 4 tasks x 2 models — nothing dropped
    ok = [r for r in rows if r["model_id"] == "ok"]
    bad = [r for r in rows if r["model_id"] == "bad"]
    assert all(r.get("error") is None for r in ok)
    assert all(r["parsed_ok"] is False and r.get("error") for r in bad)


def test_runner_supports_jsonl_source_with_field_mapping(tmp_path):
    pv = tmp_path / "pv.jsonl"
    pv.write_text(
        "\n".join(
            json.dumps(r)
            for r in [
                {"idx": "a", "func": "void f(){char b[8];gets(b);}", "target": 1},
                {"idx": "b", "func": "int add(int a,int b){return a+b;}", "target": 0},
            ]
        ),
        encoding="utf-8",
    )
    cfg = RunConfig(
        run_name="t",
        seed=1,
        dataset={
            "source": "jsonl",
            "path": str(pv),
            "code_field": "func",
            "label_field": "target",
            "id_field": "idx",
        },
        models=[{"id": "mock", "backend": "mock", "params": {"behavior": "always_vulnerable"}}],
        meters=["cost", "latency", "energy_mock"],
        reps=1,
        output_dir=str(tmp_path / "runs"),
    )
    run_dir = run(cfg, run_id="r", timestamp="t")
    rows = [
        json.loads(l)
        for l in (Path(run_dir) / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    assert len(rows) == 2
    assert {r["task_id"] for r in rows} == {"a", "b"}
