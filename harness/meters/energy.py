"""Energy meters.

Every energy meter tags its output with `energy_source` so the paper can keep
measured and estimated energy strictly distinct:
  - MockEnergyMeter        -> "mock"            (pilot placeholder)
  - EstimatedEnergyMeter   -> "estimated_flops" (API/frontier: cannot measure)
  - ZeusEnergyMeter (M3)   -> "measured_zeus"   (local open-weight: real J)
"""

from __future__ import annotations

import time
from typing import Callable

from harness.meters.base import Meter
from harness.schema import Response


class MockEnergyMeter(Meter):
    """Deterministic placeholder energy from output tokens (default 3 J/token,
    the Samsi et al. anchor). Used for the dry-run only."""

    def __init__(self, joules_per_token: float = 3.0):
        self.joules_per_token = joules_per_token

    def measure(self, call: Callable[[], Response]) -> tuple[Response, dict]:
        resp = call()
        energy_j = resp.output_tokens * self.joules_per_token
        return resp, {"energy_j": energy_j, "active_energy_j": energy_j, "energy_source": "mock"}


class EstimatedEnergyMeter(Meter):
    """FLOP-based inference-energy ESTIMATE for API-served models (not a measurement).

    energy ~= 2 * N_active_params * total_tokens * J/FLOP  (the Epoch/Jegham method).
    Open models: N_active_params is known -> grounded estimate. Frontier: N is a
    bounded assumption -> report the estimate with its parameters + a sensitivity
    range in the paper. `joules_per_flop` is a system-level constant (includes
    utilization/overhead); default ~1e-11 J/FLOP reproduces Epoch's ~0.3 Wh/GPT-4o
    query at ~100B active params / 500 output tokens.
    """

    def __init__(self, active_params_b: float, joules_per_flop: float = 1.0e-11):
        self.active_params_b = active_params_b
        self.joules_per_flop = joules_per_flop

    def measure(self, call: Callable[[], Response]) -> tuple[Response, dict]:
        resp = call()
        total_tokens = resp.input_tokens + resp.output_tokens
        flops = 2.0 * self.active_params_b * 1e9 * total_tokens
        energy_j = flops * self.joules_per_flop
        return resp, {
            "energy_j": energy_j,
            "active_energy_j": energy_j,
            "energy_source": "estimated_flops",
        }


class ZeusEnergyMeter(Meter):
    """MEASURED GPU energy for locally-served open-weight models (M3).

    Reads the NVIDIA NVML cumulative energy counter (via an injected `reader`)
    before and after the call; the delta is the GPU-board energy consumed during
    that call. `active_energy_j` subtracts an idle baseline (idle_power_w x
    duration). Requires a dedicated GPU and concurrency=1 for clean attribution.
    The reader is injected so this logic is unit-tested without a GPU.
    """

    def __init__(self, reader, clock: Callable[[], float] = time.perf_counter, idle_power_w: float = 0.0):
        self.reader = reader
        self.clock = clock
        self.idle_power_w = idle_power_w

    def measure(self, call: Callable[[], Response]) -> tuple[Response, dict]:
        t0 = self.clock()
        e0 = self.reader.total_energy_j()
        resp = call()
        e1 = self.reader.total_energy_j()
        t1 = self.clock()
        gross = e1 - e0
        active = gross - self.idle_power_w * (t1 - t0)
        return resp, {
            "energy_j": gross,
            "active_energy_j": active,
            "energy_source": "measured_nvml",
        }


class NvmlEnergyReader:
    """Reads the NVML cumulative energy counter (Joules). Constructed only on the
    GPU box; pynvml is imported lazily so this module imports fine without a GPU.
    `nvmlDeviceGetTotalEnergyConsumption` returns millijoules (Volta+)."""

    def __init__(self, gpu_index: int = 0):
        import pynvml  # lazy: only available/needed on the GPU host

        pynvml.nvmlInit()
        self._pynvml = pynvml
        self._handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)

    def total_energy_j(self) -> float:
        return self._pynvml.nvmlDeviceGetTotalEnergyConsumption(self._handle) / 1000.0

    def power_w(self) -> float:
        return self._pynvml.nvmlDeviceGetPowerUsage(self._handle) / 1000.0
