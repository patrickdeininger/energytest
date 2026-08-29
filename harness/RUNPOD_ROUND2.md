# RunPod runbook — round-2 GPU experiments (G1, G2, G3)

Everything here is scripted and dry-run validated on CPU. Budget roughly **3–4 GPU-hours
(~$12–15)**. Read §0 first: one choice there decides whether G2 is possible at all.

---

## 0. Before you start the pod — the one decision that matters

Our published measurements used **vLLM 0.10.2** on CUDA 12.8, because that was the newest
stack RunPod's H200 image supported. That stack **cannot serve Gemma-3** (it fails with a
`rope_scaling 'rope_type'` error; fixing it needs a newer `transformers`, which then breaks
vLLM 0.10.2 — they are mutually exclusive). That is the sole reason Gemma-3-4B's energy is
estimated rather than measured in the paper.

So pick a pod image and check its CUDA version:

| Driver CUDA | Stack | What you get |
|---|---|---|
| **≥ 12.9** | latest vLLM (≥ 0.11) | **Path A — do this.** All three models measurable on one stack, so G2 is unblocked *and* Qwen/Llama get re-measured on the same stack, which also replaces the `"source": "pasted"` energy JSON with harness-generated output. |
| 12.8 only | pinned torch 2.8.0 cu128 + vLLM 0.10.2 | Path B. Qwen and Llama only; Gemma stays estimated. Reproduces the published setup exactly. |

Prefer Path A. If you take it, **re-run all three sweeps on it** so the numbers are mutually
comparable — do not mix a Path A Gemma measurement with the old Path B Qwen/Llama numbers.

### Pod spec

- **GPU:** 1 × H200 SXM (141 GB)
- **Container disk:** 30 GB
- **Volume:** **200 GB** at `/workspace` — *not* the 100 GB we used last time. Qwen (~60 GB) and
  Llama-FP8 (~70 GB) together exceed 100 GB, which previously forced deleting one model
  between runs. 200 GB costs about $0.02/h and removes that whole failure mode.
- **Template:** any PyTorch/CUDA image matching your chosen path.

---

## 1. Get the code onto the pod

The pod needs the **current working tree**, not `origin/main`. The round-2 work (provider
pinning, retry/backoff, prompt variants, the concurrency override, and the G1/G3 scripts) is
uncommitted, and `origin/main` is still at `22fc67f`.

**Option A — commit and push (recommended), then on the pod:**

```bash
cd /workspace
git clone https://github.com/patrickdeininger/energytest.git
cd energytest
```

**Option B — copy the working tree directly from Windows** (no commit needed). From Git Bash
on your machine, using the SSH details RunPod shows for the pod:

```bash
rsync -avz --exclude '.git' --exclude 'harness/runs' --exclude '*.pyc' \
  -e "ssh -i ~/.ssh/runpod_ed25519 -p <POD_PORT>" \
  /c/Users/patri/IdeaProjects/Dissertation/anothertest/ \
  root@<POD_HOST>:/workspace/energytest/
```

Either way, the PrimeVul test split (`harness/data/primevul/primevul_test.jsonl`, 66 MB) must
end up on the pod — it is in the repo, so both options carry it.

---

## 2. Environment setup (on the pod)

```bash
cd /workspace/energytest
export HF_HOME=/workspace/hf          # 200 GB volume, NOT the 30 GB container disk
export HF_TOKEN=<your huggingface token>
nvidia-smi                            # confirm the CUDA version you planned for
```

**Path A (CUDA ≥ 12.9):**
```bash
pip install -q -r harness/requirements.txt pynvml accelerate
pip install -q vllm                   # latest; pulls a matching torch
```

**Path B (CUDA 12.8):**
```bash
bash harness/scripts/setup_gpu.sh     # pins torch 2.8.0 cu128 + vLLM <0.11
pip install -q accelerate
```

Verify before spending time on a download:

```bash
python -c "import torch, pynvml; pynvml.nvmlInit(); \
h=pynvml.nvmlDeviceGetHandleByIndex(0); \
print('cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0)); \
print('NVML energy counter mJ =', pynvml.nvmlDeviceGetTotalEnergyConsumption(h))"
python -m pytest harness/tests -q | tail -2      # expect 117 passed
```

`pynvml` must report a non-zero energy counter. If it errors, stop — G1 measures nothing
without it.

**Gated models.** Gemma and Llama require accepting their licences on their Hugging Face
model pages with the same account as `HF_TOKEN`. Do that now; otherwise the download fails
40 minutes in.

---

## 3. G1 + G2 — concurrency sweeps (~1 hour total)

One command per model. vLLM is started once and held up across all four concurrency levels,
so the levels differ only in in-flight request count. Energy is attributed at the **run**
level (NVML counter read before and after each level), because per-request energy windows
overlap once concurrency exceeds one.

Run smallest first — if something is wrong with the setup, you find out in 8 minutes rather
than after a 70 GB download.

```bash
# G2: Gemma-3-4B  (~8 min + small download)   -- PATH A ONLY
bash harness/scripts/run_concurrency_sweep.sh google/gemma-3-4b-it \
     harness/configs/sweep_gemma.yaml gemma

# G1a: Qwen3-Coder-30B  (~13 min + ~60 GB download)
bash harness/scripts/run_concurrency_sweep.sh Qwen/Qwen3-Coder-30B-A3B-Instruct \
     harness/configs/sweep_qwen.yaml qwen

# G1b: Llama-3.3-70B FP8  (~25 min + ~70 GB download)
bash harness/scripts/run_concurrency_sweep.sh RedHatAI/Llama-3.3-70B-Instruct-FP8-dynamic \
     harness/configs/sweep_llama.yaml llama
```

FP8 is **required** for Llama on a single H200: `bf16` is 140 GB and leaves no room for KV
cache on a 141 GB card.

Each writes `harness/runs/concurrency_sweep/<tag>.json` and prints a line per level:

```
  c=  1  n= 400  wall=  610.2s  active=    88.4 J/task  thru= 0.656 task/s
  c= 64  n= 400  wall=   19.8s  active=     9.1 J/task  thru=20.20 task/s
energy per task falls 9.7x from concurrency 1 to 64
```

Those two numbers are what the paper needs: **energy per task under realistic batching**
(answering R1 and R2#3's objection that concurrency 1 is energy-pessimistic) and
**throughput**, which pins the break-even table's axis (R2#4).

If disk runs short despite the 200 GB volume:
```bash
du -sh /workspace/hf/hub/*
rm -rf /workspace/hf/hub/models--Qwen*      # after its sweep has finished
```

---

## 4. G3 — PrimeVul-trained detector (~1–1.5 hours)

No vLLM needed; make sure any `vllm serve` from §3 has exited so the GPU is free.

```bash
# sanity check first -- verifies the HF mirror matches our test split and re-checks leakage
python -m harness.scripts.primevul_trained_baseline --check-only

# then train (batch 32 roughly halves wall-clock vs the default 16 on an H200)
python -m harness.scripts.primevul_trained_baseline --epochs 3 --batch-size 32
```

The train split (175,797 functions, 4,862 vulnerable) downloads automatically from a mirror
we verified byte-identical to our test split. Leakage is already confirmed clean from here:
**0 of 1549** evaluated functions appear in training, by ID and by whitespace-normalised body.

Writes `harness/runs/primevul_trained_baseline/scores.json` and `per_item.jsonl`. The
per-item scores are continuous, so unlike the LLMs this baseline gets a proper threshold
sweep and PR curve.

Expect a **weak** detector — PrimeVul's own authors report near-random results for models
fine-tuned on its training split. That is the point: it shows the benchmark is hard for
trained detectors too, rather than that our off-the-shelf baseline was a strawman.

---

## 5. Bring the results back

Small JSON files only — do not copy model weights.

```bash
# on the pod
cd /workspace/energytest
tar czf /workspace/r2_gpu_results.tgz \
  harness/runs/concurrency_sweep/ \
  harness/runs/primevul_trained_baseline/ \
  vllm_*.log

# from Windows (Git Bash)
scp -i ~/.ssh/runpod_ed25519 -P <POD_PORT> \
  root@<POD_HOST>:/workspace/r2_gpu_results.tgz \
  /c/Users/patri/IdeaProjects/Dissertation/anothertest/
```

Then unpack in the repo root and tell me — I fold them into §4.6 (measured vs estimated
energy), §4.4 (baselines), Table 8 (break-even throughput), and the response letter.

**Then terminate the pod.** It bills while idle.

---

## 6. Failure modes, and what they mean

| Symptom | Cause | Fix |
|---|---|---|
| `rope_scaling 'rope_type'` on Gemma | vLLM 0.10.2 | Path A; this is exactly why G2 was blocked |
| `CUDA driver too old` | plain `pip install vllm` pulled a newer-CUDA torch | Path B pinned install (`setup_gpu.sh`) |
| `all_special_tokens_extended` AttributeError | `transformers` upgraded past 4.56 under vLLM 0.10.2 | pin `transformers<4.56`; never `pip install -U transformers` on Path B |
| 401/403 on download | licence not accepted, or `HF_TOKEN` unset | accept on the model page with the same account |
| NVML energy counter is 0 or errors | GPU older than Volta, or no NVML | stop; G1 cannot be measured |
| vLLM OOM on Llama | not the FP8 repo, or `--max-model-len` too large | use `RedHatAI/...-FP8-dynamic`; the driver already caps at 4096 |
| Sweep hangs at concurrency 64 | KV cache exhausted | lower with `LEVELS=1,8,32 bash ...` |

Wall-clock at concurrency 1 dominates each sweep (~10 of Qwen's 13 minutes). If you are
short on time, `LEVELS=1,32 bash harness/scripts/run_concurrency_sweep.sh ...` still gives
the energy-vs-batching contrast and a throughput figure.
