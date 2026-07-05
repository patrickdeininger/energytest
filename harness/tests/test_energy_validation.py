"""Tests for folding MEASURED (NVML) energy into the combined results and for the
measured-vs-estimated validation table (M3).

The measured-energy run (harness/scripts/run_local_energy.sh) produces rows tagged
energy_source="measured_nvml" with energy_j=gross and active_energy_j=idle-subtracted.
These helpers (a) overwrite the matching models' energy in the API-run combined set
with the measured mean, keeping accuracy/cost intact, and (b) quantify how far the
FLOP estimate undershoots the real measurement, cross-checked against the Samsi
~3-4 J/output-token anchor.
"""

from pytest import approx

from harness.analysis.energy_validation import (
    aggregate_measured,
    apply_measured_energy,
    energy_validation_table,
    format_validation_markdown,
    SAMSI_ANCHOR_J_PER_TOKEN,
)


def test_aggregate_measured_computes_means():
    rows = [
        {"energy_j": 120.0, "active_energy_j": 80.0, "output_tokens": 40},
        {"energy_j": 140.0, "active_energy_j": 100.0, "output_tokens": 20},
    ]
    agg = aggregate_measured(rows)
    assert agg["mean_gross_j"] == approx(130.0)
    assert agg["mean_active_j"] == approx(90.0)
    assert agg["mean_output_tokens"] == approx(30.0)
    assert agg["n"] == 2


def test_apply_measured_energy_overwrites_only_matched_model():
    rows = [
        {"model_id": "qwen3-coder-30b", "energy_j": 40.0, "active_energy_j": 40.0,
         "energy_source": "estimated_flops", "correct": True, "usd_cost": 6e-5, "output_tokens": 57},
        {"model_id": "deepseek-v3.2", "energy_j": 263.0, "active_energy_j": 263.0,
         "energy_source": "estimated_flops", "correct": False, "usd_cost": 8e-5, "output_tokens": 57},
    ]
    out = apply_measured_energy(rows, {"qwen3-coder-30b": {"active_j": 88.9, "gross_j": 130.8}})
    qwen = next(r for r in out if r["model_id"] == "qwen3-coder-30b")
    deepseek = next(r for r in out if r["model_id"] == "deepseek-v3.2")
    # matched model: energy replaced by measured active, gross stashed, source flipped
    assert qwen["energy_j"] == approx(88.9)
    assert qwen["active_energy_j"] == approx(88.9)
    assert qwen["gross_energy_j"] == approx(130.8)
    assert qwen["energy_source"] == "measured_nvml"
    # accuracy/cost fields preserved for the matched model
    assert qwen["correct"] is True and qwen["usd_cost"] == 6e-5
    # unmatched model untouched
    assert deepseek["energy_j"] == approx(263.0)
    assert deepseek["energy_source"] == "estimated_flops"
    assert "gross_energy_j" not in deepseek


def test_apply_measured_energy_does_not_mutate_input_rows():
    rows = [{"model_id": "qwen3-coder-30b", "energy_j": 40.0}]
    apply_measured_energy(rows, {"qwen3-coder-30b": {"active_j": 88.9, "gross_j": 130.8}})
    assert rows[0]["energy_j"] == approx(40.0)  # original untouched


def test_energy_validation_table_computes_undershoot_and_j_per_token():
    estimated = [
        {"model_id": "qwen3-coder-30b", "energy_j": 40.0},
        {"model_id": "qwen3-coder-30b", "energy_j": 40.0},
    ]
    measured = {"qwen3-coder-30b": {"active_j": 88.9, "gross_j": 130.8, "mean_output_tokens": 25.0}}
    table = energy_validation_table(estimated, measured)
    row = table[0]
    assert row["model_id"] == "qwen3-coder-30b"
    assert row["estimated_j"] == approx(40.0)
    assert row["measured_active_j"] == approx(88.9)
    assert row["undershoot_ratio"] == approx(88.9 / 40.0)  # ~2.22x
    assert row["j_per_output_token"] == approx(88.9 / 25.0)  # ~3.56


def test_energy_validation_table_flags_samsi_anchor_membership():
    lo, hi = SAMSI_ANCHOR_J_PER_TOKEN
    assert (lo, hi) == (3.0, 4.0)
    # 90 active / 25 tok = 3.6 J/tok -> within [3,4]
    within = energy_validation_table(
        [{"model_id": "m", "energy_j": 40.0}],
        {"m": {"active_j": 90.0, "gross_j": 130.0, "mean_output_tokens": 25.0}},
    )[0]
    assert within["within_samsi_anchor"] is True
    # 200 active / 25 tok = 8 J/tok -> outside
    outside = energy_validation_table(
        [{"model_id": "m", "energy_j": 40.0}],
        {"m": {"active_j": 200.0, "gross_j": 260.0, "mean_output_tokens": 25.0}},
    )[0]
    assert outside["within_samsi_anchor"] is False


def test_energy_validation_table_sorted_by_model_id():
    est = [{"model_id": "qwen3-coder-30b", "energy_j": 40.0}, {"model_id": "llama-3.3-70b", "energy_j": 900.0}]
    measured = {
        "qwen3-coder-30b": {"active_j": 88.9, "gross_j": 130.8, "mean_output_tokens": 25.0},
        "llama-3.3-70b": {"active_j": 700.0, "gross_j": 800.0, "mean_output_tokens": 30.0},
    }
    table = energy_validation_table(est, measured)
    assert [r["model_id"] for r in table] == ["llama-3.3-70b", "qwen3-coder-30b"]


def test_format_validation_markdown_contains_models_and_ratio():
    est = [{"model_id": "qwen3-coder-30b", "energy_j": 40.0}]
    measured = {"qwen3-coder-30b": {"active_j": 88.9, "gross_j": 130.8, "mean_output_tokens": 25.0}}
    md = format_validation_markdown(energy_validation_table(est, measured))
    assert "qwen3-coder-30b" in md
    assert "|" in md  # is a markdown table
    assert "2.2" in md  # undershoot ratio rendered
