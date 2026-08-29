#!/usr/bin/env bash
# G1: measured energy AND throughput across concurrency levels for one open model.
#
#   bash harness/scripts/run_concurrency_sweep.sh <hf_model_id> <sweep_config.yaml> <tag> [extra vllm args...]
#
# Examples:
#   bash harness/scripts/run_concurrency_sweep.sh google/gemma-3-4b-it \
#        harness/configs/sweep_gemma.yaml gemma
#   bash harness/scripts/run_concurrency_sweep.sh Qwen/Qwen3-Coder-30B-A3B-Instruct \
#        harness/configs/sweep_qwen.yaml qwen
#   bash harness/scripts/run_concurrency_sweep.sh RedHatAI/Llama-3.3-70B-Instruct-FP8-dynamic \
#        harness/configs/sweep_llama.yaml llama
#
# Differs from run_local_energy.sh in one important way: vLLM is started ONCE and
# held up across every concurrency level, so the levels differ only in in-flight
# request count and nothing else. Energy is attributed at the run level by
# concurrency_sweep.py (NVML counter read before/after each level), because
# per-request energy windows overlap once concurrency exceeds one.
#
# Idle power is measured on this pod rather than taken from a config placeholder.
set -euo pipefail

MODEL="$1"; CONFIG="$2"; TAG="$3"; shift 3 || true
LEVELS="${LEVELS:-1,8,32,64}"
# 4096 is ample (prompts are capped at 8000 chars, roughly 2500 tokens, plus 64 out)
# and leaves far more VRAM for KV cache, which is what high concurrency needs.
MAXLEN="${MAXLEN:-4096}"

echo ">> serving $MODEL on :8000 (vLLM, max-model-len=$MAXLEN)"
vllm serve "$MODEL" --port 8000 --max-model-len "$MAXLEN" "$@" > "vllm_${TAG}.log" 2>&1 &
VPID=$!
trap 'kill $VPID 2>/dev/null || true' EXIT

echo ">> waiting for vLLM (first serve also downloads weights; up to 40 min) ..."
for i in $(seq 1 600); do
  if ! kill -0 "$VPID" 2>/dev/null; then
    echo "   vLLM exited early. The outer traceback is almost never the cause:"
    echo "   vLLM raises 'Engine core initialization failed. See root cause above',"
    echo "   and the real error is raised in the EngineCore subprocess further up."
    echo
    echo "   ---- first real error in vllm_${TAG}.log ----"
    grep -nE "^(ERROR|CRITICAL)|Error:|ValueError|RuntimeError|KeyError|TypeError|AssertionError|NotImplementedError|torch.OutOfMemoryError|No available memory|not supported|Unsupported" \
      "vllm_${TAG}.log" | grep -v "Engine core initialization failed" | head -20
    echo
    echo "   ---- EngineCore traceback ----"
    awk '/EngineCore.*(failed|Traceback)|Traceback \(most recent call last\)/{f=1} f' \
      "vllm_${TAG}.log" | head -40
    echo
    echo "   Full log: vllm_${TAG}.log ($(wc -l < "vllm_${TAG}.log") lines)"
    exit 1
  fi
  if curl -sf http://localhost:8000/v1/models >/dev/null 2>&1; then echo "   ready"; break; fi
  sleep 5
  [ "$i" -eq 600 ] && { echo "   timed out; see vllm_${TAG}.log"; exit 1; }
done

echo ">> letting the GPU settle before the idle-power baseline"
sleep 20
nvidia-smi --query-gpu=power.draw,memory.used --format=csv,noheader

echo ">> sweeping concurrency levels: $LEVELS"
python -m harness.scripts.concurrency_sweep \
  --config "$CONFIG" --levels "$LEVELS" --tag "$TAG"

echo ">> done. Results: harness/runs/concurrency_sweep/${TAG}.json"
echo ">> stopping vLLM."
