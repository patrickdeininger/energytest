"""Tests for report aggregation.

Key correctness rule: accuracy/precision/recall/F1 are computed over PARSED
predictions only (a parse failure is a reliability problem, not a wrong 'safe'
prediction). parse_rate / error_rate are reported alongside as caveats.
"""

import json
from pathlib import Path

from harness.report.report import build_report


def _write_run(tmp_path, rows):
    d = tmp_path / "run"
    d.mkdir()
    (d / "results.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return d


def _row(model, label, pred, parsed, error=None, out_tok=50):
    return {
        "model_id": model, "label": label, "prediction": pred, "parsed_ok": parsed,
        "error": error, "output_tokens": out_tok, "usd_cost": 0.1, "total_ms": 10.0,
        "energy_j": 5.0, "energy_source": "estimated_flops",
    }


def test_accuracy_is_computed_over_parsed_rows_only(tmp_path):
    # 2 parsed & correct, 1 parse-failure. Accuracy over parsed = 1.0, not 2/3.
    rows = [
        _row("m", 1, 1, True),
        _row("m", 0, 0, True),
        _row("m", 1, 0, False, error=None, out_tok=0),
    ]
    rep = build_report(_write_run(tmp_path, rows))
    r = rep["metrics"].iloc[0]
    assert r["accuracy"] == 1.0
    assert r["n"] == 3
    assert r["n_parsed"] == 2
    assert abs(r["parse_rate"] - 2 / 3) < 1e-9


def test_report_includes_error_rate_and_energy_source(tmp_path):
    rows = [
        _row("m", 1, 1, True, error=None),
        _row("m", 0, 0, False, error="Timeout", out_tok=0),
    ]
    rep = build_report(_write_run(tmp_path, rows))
    r = rep["metrics"].iloc[0]
    assert abs(r["error_rate"] - 0.5) < 1e-9
    assert r["energy_source"] == "estimated_flops"
    assert "out_tok_mean" in rep["metrics"].columns
