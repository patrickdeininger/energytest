"""End-to-end dry-run: config -> runner -> results -> report, no spend, no GPU."""

import json
from pathlib import Path

from harness.config import RunConfig
from harness.runner import run
from harness.report.report import build_report

FIXTURE = "harness/data/fixtures/primevul_mini.jsonl"


def make_cfg(tmp_path) -> RunConfig:
    return RunConfig(
        run_name="pilot_dryrun",
        seed=123,
        dataset={"source": "fixture", "path": FIXTURE, "n": 8, "stratify_by": "label"},
        task="vuln_detect_binary",
        models=[
            {"id": "mock-allvuln", "backend": "mock", "params": {"behavior": "always_vulnerable"}, "price": {"in": 0.5, "out": 1.5}},
            {"id": "mock-balanced", "backend": "mock", "params": {"behavior": "balanced"}, "price": {"in": 5.0, "out": 25.0}},
        ],
        meters=["cost", "latency", "energy_mock"],
        reps=2,
        gen={"temperature": 0.0, "max_output_tokens": 64},
        output_dir=str(tmp_path / "runs"),
    )


def test_e2e_dryrun_end_to_end(tmp_path):
    cfg = make_cfg(tmp_path)
    run_dir = run(cfg, run_id="testrun", timestamp="2026-07-04T00:00:00Z", git_sha="deadbeef")

    results = Path(run_dir) / "results.jsonl"
    assert results.exists()
    rows = [json.loads(l) for l in results.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) == 8 * 2 * 2  # tasks x models x reps
    assert (Path(run_dir) / "manifest.json").exists()

    for r in rows:
        assert r["usd_cost"] >= 0
        assert r["energy_j"] >= 0
        assert r["total_ms"] >= 0
        assert r["prediction"] in (0, 1)
        assert isinstance(r["correct"], bool)
        assert isinstance(r.get("raw_output"), str)

    allvuln = [r for r in rows if r["model_id"] == "mock-allvuln"]
    assert allvuln and all(r["prediction"] == 1 for r in allvuln)

    build_report(run_dir)
    assert (Path(run_dir) / "metrics.csv").exists()
    assert len(list(Path(run_dir).glob("pareto_*.png"))) >= 1


def test_run_is_reproducible(tmp_path):
    cfg = make_cfg(tmp_path)
    d1 = run(cfg, run_id="r1", timestamp="t", git_sha="x")
    d2 = run(cfg, run_id="r2", timestamp="t", git_sha="x")

    def preds(d):
        rows = [json.loads(l) for l in (Path(d) / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        return sorted((r["model_id"], r["task_id"], r["rep"], r["prediction"]) for r in rows)

    assert preds(d1) == preds(d2)
