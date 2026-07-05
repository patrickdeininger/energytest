#!/usr/bin/env bash
# M3 — measured open-side energy on a rented cloud GPU (RunPod / Vast.ai / Lambda).
# Run this ON the GPU host (Linux + CUDA + a DEDICATED NVIDIA GPU, Volta or newer
# so the NVML energy counter exists). Then run the harness against the local vLLM
# server. See harness/configs/primevul_local_energy.yaml.
set -euo pipefail

# 1. Install deps (harness core + vLLM serving + NVML reader)
pip install -r harness/requirements.txt
pip install vllm pynvml

# 2. Verify the NVML energy counter is readable (prints cumulative millijoules)
python - <<'PY'
import pynvml
pynvml.nvmlInit()
h = pynvml.nvmlDeviceGetHandleByIndex(0)
print("NVML energy counter OK, mJ =", pynvml.nvmlDeviceGetTotalEnergyConsumption(h))
print("current power W =", pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0)
PY

# 3. Measure IDLE GPU power (nothing else running) and put it in the config's
#    idle_power_w so active energy = gross - idle*duration.
echo "Idle GPU power (W) — copy into primevul_local_energy.yaml idle_power_w:"
nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits

# 4. (Optional) fix the power cap so energy/token is reproducible, and record it:
# nvidia-smi -pl 300

# 5. Serve ONE model at a time via vLLM (OpenAI-compatible on :8000), then run the
#    harness (concurrency=1). Repeat per model, editing the config's model id.
#    Example:
#
#    vllm serve Qwen/Qwen3-Coder-30B-A3B-Instruct --port 8000 &
#    # wait for "Uvicorn running on ...", then:
#    python -m harness.run --config harness/configs/primevul_local_energy.yaml
#
# Sanity check after a run: energy per output token should land near the
# Samsi et al. ~3-4 J/token anchor for a model of this class.

echo "Setup complete. Serve a model with vLLM, then run the local-energy config."
