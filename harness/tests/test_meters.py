"""Tests for measurement meters (cost, latency, energy) and their composition.

Meters wrap a zero-arg `call` that returns a Response, invoke it exactly once,
and return (Response, metrics_dict). LatencyMeter takes an injectable clock so
timing is deterministic in tests.
"""

from pytest import approx

from harness.schema import Response
from harness.meters import (
    CostMeter,
    LatencyMeter,
    MockEnergyMeter,
    EstimatedEnergyMeter,
    ZeusEnergyMeter,
    compose,
)


class FakeEnergyReader:
    """Returns successive cumulative-energy readings (Joules)."""

    def __init__(self, readings):
        self._readings = list(readings)
        self._i = 0

    def total_energy_j(self):
        v = self._readings[self._i]
        self._i += 1
        return v


def fake_clock(values):
    it = iter(values)
    return lambda: next(it)


def make_call(resp, counter=None):
    def _call():
        if counter is not None:
            counter["n"] += 1
        return resp
    return _call


def test_cost_meter_tokens_times_price_per_million():
    resp = Response(text="x", input_tokens=1000, output_tokens=200, ttft_ms=None)
    _, m = CostMeter(price_in=5.0, price_out=25.0).measure(make_call(resp))
    # 1000/1e6*5 + 200/1e6*25 = 0.005 + 0.005
    assert m["usd_cost"] == approx(0.01)
    assert m["input_tokens"] == 1000
    assert m["output_tokens"] == 200


def test_latency_meter_uses_injected_clock():
    resp = Response(text="x", input_tokens=10, output_tokens=200, ttft_ms=120.0)
    meter = LatencyMeter(clock=fake_clock([1.0, 1.5]))  # 0.5 s elapsed
    _, m = meter.measure(make_call(resp))
    assert m["total_ms"] == 500.0
    assert m["tokens_per_s"] == 400.0  # 200 tokens / 0.5 s
    assert m["ttft_ms"] == 120.0  # passed through from the Response


def test_mock_energy_meter_is_deterministic_from_output_tokens():
    resp = Response(text="x", input_tokens=10, output_tokens=200, ttft_ms=None)
    _, m = MockEnergyMeter(joules_per_token=3.0).measure(make_call(resp))
    assert m["energy_j"] == 600.0
    assert m["active_energy_j"] == 600.0
    assert m["energy_source"] == "mock"


def test_estimated_energy_meter_is_flops_based_and_labeled():
    resp = Response(text="x", input_tokens=100, output_tokens=100, ttft_ms=None)
    _, m = EstimatedEnergyMeter(active_params_b=7, joules_per_flop=1e-11).measure(make_call(resp))
    # 2 * 7e9 params * (100+100) tokens * 1e-11 J/FLOP = 28.0 J
    assert m["energy_j"] == approx(28.0)
    assert m["energy_source"] == "estimated_flops"


def test_zeus_energy_meter_measures_counter_delta_and_subtracts_idle():
    resp = Response(text="x", input_tokens=10, output_tokens=50, ttft_ms=None)
    reader = FakeEnergyReader([1000.0, 1080.0])  # 80 J consumed across the call
    meter = ZeusEnergyMeter(reader=reader, clock=fake_clock([0.0, 2.0]), idle_power_w=10.0)
    _, m = meter.measure(make_call(resp))
    assert m["energy_j"] == 80.0  # gross counter delta
    assert m["active_energy_j"] == 60.0  # 80 - 10W * 2s idle
    assert m["energy_source"] == "measured_nvml"


def test_compose_calls_backend_once_and_merges_all_metrics():
    counter = {"n": 0}
    resp = Response(text="yes", input_tokens=100, output_tokens=50, ttft_ms=None)
    meters = [
        LatencyMeter(clock=fake_clock([0.0, 0.5])),  # 500 ms
        MockEnergyMeter(joules_per_token=2.0),
        CostMeter(price_in=1.0, price_out=2.0),
    ]
    out_resp, metrics = compose(meters).measure(make_call(resp, counter))
    assert counter["n"] == 1  # backend invoked exactly once
    assert out_resp.text == "yes"
    assert metrics["usd_cost"] == approx(100 / 1e6 * 1.0 + 50 / 1e6 * 2.0)
    assert metrics["energy_j"] == 100.0  # 50 * 2.0
    assert metrics["total_ms"] == 500.0
    assert metrics["tokens_per_s"] == 100.0  # 50 / 0.5 s
