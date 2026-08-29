# RunPod runbook — round-2 GPU experiments (G1, G2, G3)

Everything here is scripted and dry-run validated on CPU. Budget roughly **3–4 GPU-hours
(~$12–15)**. Read §0 first — it contains the one install mistake that will cost you a
pod session, and we already made it once.

---

## 0. The install rule

Our published measurements used **vLLM 0.10.2** with torch 2.8.0 `cu128`. All three models
serve on it, provided `transformers` is pinned correctly (see below).

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

**Gemma-3 does serve on this stack**, contrary to what we believed when the paper was
submitted. The blocker was never vLLM itself but the `transformers` version: Gemma-3's config
needs >= 4.50 to parse (below it vLLM raises `ValidationError for ModelConfig`), while vLLM
0.10.2 needs < 4.56 (which drops `all_special_tokens_extended`). **4.55.2 satisfies both**,
and `setup_gpu.sh` now pins it. Verified on an H200 pod, 2026-08-29.

That means all three models run on one stack, so G2 is unblocked and the numbers stay
mutually comparable. Run them in size order anyway — a failure costs 8 minutes rather than a
70 GB download.

Do not upgrade `transformers` past 4.55.2 to fix some later problem: it will break vLLM
0.10.2 for *every* model, not just Gemma.

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

**The dataset is NOT in the repo.** `harness/data/primevul/` is gitignored (64 MB), so a
clone gives you code without data and every run dies with `FileNotFoundError` on
`primevul_test.jsonl`. Fetch it explicitly:

```bash
python -m harness.scripts.fetch_primevul
```

That pulls the split from a Hugging Face mirror and refuses to install it unless the row
count and vulnerable count match the split the paper was measured on — a different revision
would silently change the evaluated sample. (Option B's `rsync` carries the file already, so
this step is only needed after a clone.)

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
export IDLE_W=77.38        # the bare idle watts setup_gpu.sh printed on THIS pod

# G1a: Qwen3-Coder-30B  (~13 min + ~60 GB download)
bash harness/scripts/run_concurrency_sweep.sh Qwen/Qwen3-Coder-30B-A3B-Instruct \
     harness/configs/sweep_qwen.yaml qwen

# G1b: Llama-3.3-70B FP8  (~25 min + ~70 GB download)
bash harness/scripts/run_concurrency_sweep.sh RedHatAI/Llama-3.3-70B-Instruct-FP8-dynamic \
     harness/configs/sweep_llama.yaml llama
```

**Set `IDLE_W`.** Without it the sweep measures idle draw itself, but it can only do that once
vLLM is already up, which subtracts *model-resident* idle — a higher baseline than the
published runs subtracted, making the concurrency-1 point non-comparable to the very number
it is meant to validate. The script warns if you forget.

**Check `compressed-tensors` before the Llama run.** The FP8 checkpoint is a
compressed-tensors format, and `pip uninstall vllm torch` leaves that package behind at
whatever version the bare `pip install vllm` pulled — which was built for a newer torch:

```bash
python -c "import compressed_tensors as c, torch; print('ct', c.__version__, '| torch', torch.__version__)"
```

If it raises, install the version vLLM actually asks for rather than guessing:

```bash
python -c "import importlib.metadata as m; print([r for r in m.requires('vllm') if 'compressed' in r.lower()])"
pip install -q "compressed-tensors==<the version printed>"
```

Qwen is `bf16` and never loads compressed-tensors, so G1a is unaffected either way — which is
another reason to run it first.

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

## 3a. G2 — Gemma-3-4B (~8 min)

With `transformers==4.55.2` pinned by `setup_gpu.sh`, Gemma-3 serves on the same stack as the
other two, so this is just a third sweep rather than a special case:

```bash
bash harness/scripts/run_concurrency_sweep.sh google/gemma-3-4b-it      harness/configs/sweep_gemma.yaml gemma
```

Run it whenever it fits — it is small and fast. If it still fails, add `--enforce-eager`, and
if that fails too, stop: Gemma stays FLOP-estimated, which is what the manuscript currently
reports. It is a 4B model contributing one point to one figure and is not worth an hour of
GPU time.

**If it succeeds, tell me.** The manuscript states that Gemma could not be served under our
local stack; that sentence becomes false and the efficiency champion moves from estimated to
measured, which materially strengthens Figure 2.

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
