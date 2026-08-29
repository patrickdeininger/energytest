# RunPod runbook — round-2 GPU experiments (G1, G2, G3)

Everything here is scripted and dry-run validated on CPU. Budget roughly **3–4 GPU-hours
(~$12–15)**. Read §0 first — it contains the one install mistake that will cost you a
pod session, and we already made it once.

---

## 0. The install rule

Our published measurements used **vLLM 0.10.2** with torch 2.8.0 `cu128`. Gemma-3 is the one
model that stack may refuse (`rope_scaling 'rope_type'`), which is the sole reason Gemma-3-4B's
energy is estimated rather than measured in the paper. Everything else serves fine on it.

### Never run a bare `pip install vllm`

Confirmed the hard way on 2026-08-29: the RunPod H200 driver reports CUDA **12.9**
(`found version 12090`), and the current release of vLLM ships a torch built against CUDA
**13.x**. Installing it produces, deep inside the EngineCore subprocess:

```
RuntimeError: The NVIDIA driver on your system is too old (found version 12090).
```

The rule is therefore not "newer CUDA means take the newer stack". It is: **pin torch to a
build matching the driver, then install vLLM under a constraint that forbids it from
upgrading torch.** `harness/scripts/setup_gpu.sh` does exactly that (torch 2.8.0 `cu128`,
then `vllm<0.11` constrained to that torch). A `cu128` build runs fine on a 12.9 driver —
CUDA minor versions are forward compatible — so this stack is correct for this pod, and it is
also the stack the published measurements used.

That leaves Gemma-3 as the open question, because vLLM 0.10.2 is where the
`rope_scaling 'rope_type'` failure lives. Take it in this order:

1. **`setup_gpu.sh`, then run Qwen and Llama.** This is G1, the high-value experiment, on a
   known-good stack. Do not let Gemma block it.
2. **Then attempt Gemma** (§3a below). If it fails, Gemma stays FLOP-estimated, which is the
   paper's current position — nothing breaks.

If Gemma *does* serve on a newer stack, do not mix epochs: re-run Qwen and Llama on that same
stack so all three are comparable, or report Gemma separately with the stack difference
disclosed.

### Pod spec

- **GPU:** 1 × H200 SXM (141 GB)
- **Container disk:** 30 GB
- **Volume:** **200 GB** at `/workspace` — *not* the 100 GB we used last time. Qwen (~60 GB) and
  Llama-FP8 (~70 GB) together exceed 100 GB, which previously forced deleting one model
  between runs. 200 GB costs about $0.02/h and removes that whole failure mode.
- **Template:** any recent PyTorch/CUDA image. The image's own CUDA version does not matter
  much, because `setup_gpu.sh` installs a driver-matched torch over the top of it.

---

## 1. Get the code onto the pod

The round-2 work (provider pinning, retry/backoff, prompt variants, the concurrency override,
and the G1/G3 scripts) lives on the **`revision/mdpi-round-1`** branch. `main` is still at
`22fc67f` and does **not** have it, so a plain `git clone` will give you stale code and the
sweep scripts will be missing.

**Option A — clone the branch (recommended):**

```bash
cd /workspace
git clone -b revision/mdpi-round-1 https://github.com/patrickdeininger/energytest.git
cd energytest
git log --oneline -1     # expect: docs: MDPI round-1 reviews, revision plan, ...
```

(If the branch has since been merged, a plain clone of `main` is equivalent — check that
`harness/scripts/concurrency_sweep.py` exists before relying on it.)

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

```bash
# If a bare `pip install vllm` was already run, clear it out first -- otherwise its
# CUDA-13 torch survives and every serve dies in the EngineCore subprocess.
pip uninstall -y vllm torch torchvision torchaudio

bash harness/scripts/setup_gpu.sh     # pins torch 2.8.0 cu128 + vllm<0.11, verifies NVML
pip install -q accelerate             # needed by the G3 Trainer
```

`setup_gpu.sh` fails loudly if torch cannot see the GPU, so a bad install cannot silently
reach the runs.

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

## 3a. G2 — Gemma-3-4B, only after G1 has finished

Gemma-3 is the one model vLLM 0.10.2 may refuse. Try these in order; each takes about two
minutes to fail, and extra arguments pass straight through to `vllm serve`.

```bash
# (a) the pinned stack, as-is -- try it first, it costs nothing to find out
bash harness/scripts/run_concurrency_sweep.sh google/gemma-3-4b-it \
     harness/configs/sweep_gemma.yaml gemma

# (b) transformers in the window that satisfies BOTH constraints:
#     Gemma-3's config needs >=4.50; vLLM 0.10.2 needs <4.56 (4.56 drops
#     all_special_tokens_extended, which vLLM calls). 4.55.x satisfies both.
pip install -q "transformers==4.55.2"
bash harness/scripts/run_concurrency_sweep.sh google/gemma-3-4b-it \
     harness/configs/sweep_gemma.yaml gemma --enforce-eager

# (c) newer vLLM WITHOUT letting it drag in a CUDA-13 torch
pip install -q "vllm==0.11.0" --extra-index-url https://download.pytorch.org/whl/cu128 \
    --constraint <(printf 'torch==2.8.0\n')
python -c "import torch; assert torch.cuda.is_available(), 'torch lost the GPU -- roll back'"
bash harness/scripts/run_concurrency_sweep.sh google/gemma-3-4b-it \
     harness/configs/sweep_gemma.yaml gemma
```

Check `torch.cuda.is_available()` after any reinstall. If none of these work, stop: Gemma
stays FLOP-estimated, which is what the manuscript already reports and discloses. It is a 4B
model contributing one point to Figure 2 — not worth an hour of GPU time.

If (c) succeeds, Gemma was measured on a different vLLM than Qwen and Llama. Either re-run
those two on 0.11.0 as well, or tell me and I will disclose the stack difference in
Section 4.6 rather than let it pass silently.

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
| `rope_scaling 'rope_type'` on Gemma | transformers too old for Gemma-3 under vLLM 0.10.2 | Section 3a, options (b) then (c) |
| `driver ... too old (found version 12090)` | bare `pip install vllm` pulled a CUDA-13 torch; this pod's driver is 12.9 | `pip uninstall -y vllm torch` then `setup_gpu.sh` |
| `all_special_tokens_extended` AttributeError | `transformers` upgraded past 4.56 under vLLM 0.10.2 | pin `transformers==4.55.2`; never `pip install -U transformers` |
| 401/403 on download | licence not accepted, or `HF_TOKEN` unset | accept on the model page with the same account |
| NVML energy counter is 0 or errors | GPU older than Volta, or no NVML | stop; G1 cannot be measured |
| vLLM OOM on Llama | not the FP8 repo, or `--max-model-len` too large | use `RedHatAI/...-FP8-dynamic`; the driver already caps at 4096 |
| Sweep hangs at concurrency 64 | KV cache exhausted | lower with `LEVELS=1,8,32 bash ...` |

Wall-clock at concurrency 1 dominates each sweep (~10 of Qwen's 13 minutes). If you are
short on time, `LEVELS=1,32 bash harness/scripts/run_concurrency_sweep.sh ...` still gives
the energy-vs-batching contrast and a throughput figure.
