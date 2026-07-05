#!/usr/bin/env bash
# One-shot measured-energy run for a single open model:
#   serve with vLLM -> wait until ready -> run the harness (concurrency=1) -> stop vLLM.
# Run on the GPU host after setup_gpu.sh. Usage:
#   bash harness/scripts/run_local_energy.sh <hf_model_id> <config.yaml> [extra vllm args...]
# Examples:
#   bash harness/scripts/run_local_energy.sh google/gemma-3-4b-it harness/configs/local_energy_gemma.yaml
#   # 24GB GPU, large model -> add quantization, e.g.:
#   bash harness/scripts/run_local_energy.sh Qwen/Qwen3-Coder-30B-A3B-Instruct harness/configs/local_energy_qwen.yaml --quantization awq --max-model-len 8192
set -euo pipefail

MODEL="$1"; CONFIG="$2"; shift 2 || true

echo ">> serving $MODEL on :8000 (vLLM)"
vllm serve "$MODEL" --port 8000 "$@" > "vllm_serve.log" 2>&1 &
VPID=$!
trap 'kill $VPID 2>/dev/null || true' EXIT

echo ">> waiting for vLLM to be ready ..."
for i in $(seq 1 180); do
  if curl -sf http://localhost:8000/v1/models >/dev/null 2>&1; then echo "   ready"; break; fi
  sleep 5
  if [ "$i" -eq 180 ]; then echo "   vLLM did not become ready; see vllm_serve.log"; exit 1; fi
done

echo ">> current GPU power (should be near idle before load):"
nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits || true

echo ">> running harness (concurrency=1) against local vLLM"
python -m harness.run --config "$CONFIG"

echo ">> done. Stopping vLLM."
