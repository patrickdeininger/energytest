#!/usr/bin/env bash
# M3 setup on a CUDA-12.8 GPU host (e.g. RunPod H200, driver 12.8).
# Installs a 12.8-MATCHED torch + vLLM (the default `pip install vllm` pulls a
# newer-CUDA torch and fails with "driver too old"), verifies the NVML energy
# counter, and prints idle power.
set -euo pipefail

echo ">> installing harness deps"
pip install -q -r harness/requirements.txt pynvml accelerate

# hf_transfer: several RunPod images export HF_HUB_ENABLE_HF_TRANSFER=1 without shipping
# the package, which makes every model download die with a ValueError before a single byte
# is fetched. It is also genuinely faster on the 60-70 GB checkpoints, so install rather
# than unset the flag.
pip install -q hf_transfer

# transformers 4.55.2 is the ONLY window that satisfies both ends of the stack:
#   >= 4.50  Gemma-3's config parses (below this vLLM raises ValidationError for ModelConfig)
#   <  4.56  all_special_tokens_extended still exists, which vLLM 0.10.2 calls
# Verified on an H200 pod 2026-08-29. Do not "upgrade" this.
pip install -q "transformers==4.55.2"

echo ">> installing CUDA 12.8-matched torch (cu128)"
pip install -q "torch==2.8.0" --index-url https://download.pytorch.org/whl/cu128

echo ">> installing vLLM compatible with torch 2.8 (keeps torch pinned to cu128)"
pip install -q "vllm<0.11" --extra-index-url https://download.pytorch.org/whl/cu128 \
  --constraint <(printf 'torch==2.8.0\n')

echo ">> verifying torch sees the GPU (must say CUDA OK)"
python - <<'PY'
import torch
assert torch.cuda.is_available(), "CUDA NOT available -- torch/driver mismatch. Re-run the pinned install."
print("   torch", torch.__version__, "| cuda", torch.version.cuda, "| GPU:", torch.cuda.get_device_name(0), "-> CUDA OK")
PY

echo ">> verifying NVML energy counter (Volta+)"
python - <<'PY'
import pynvml
pynvml.nvmlInit()
h = pynvml.nvmlDeviceGetHandleByIndex(0)
print("   NVML energy counter OK, mJ =", pynvml.nvmlDeviceGetTotalEnergyConsumption(h))
print("   current power W =", pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0)
PY

echo ">> idle GPU power (W) -- copy into idle_power_w in the local_energy_*.yaml configs:"
nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits

echo ">> pinned stack:"
python - <<'PY2'
import importlib.metadata as m
for pkg in ("torch", "vllm", "transformers", "hf_transfer", "compressed-tensors"):
    try:
        print(f"   {pkg:20s} {m.version(pkg)}")
    except m.PackageNotFoundError:
        print(f"   {pkg:20s} (not installed)")
PY2

echo ">> setup complete. Record the versions above in the paper's reproducibility appendix."
