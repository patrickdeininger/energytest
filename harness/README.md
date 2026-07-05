# Benchmark Harness

Measurement harness for the paper *Open-weight vs. frontier LLMs for vulnerability
detection: a cost-, latency-, and energy-aware benchmark* (→ MDPI *Computers*).

For each `(model, code sample)` it obtains a vulnerability-detection prediction
and measures **accuracy, monetary cost, latency, and energy**, then reports
accuracy-vs-efficiency **Pareto frontiers**.

Design spec: `../docs/superpowers/specs/2026-07-04-benchmark-harness-design.md`.
Research plan: `../research/Stage1_Research_Plan.md`.

## Status

- **M1 (done): dry-run pilot** — full pipeline on a mock backend + mock energy
  meter: no API spend, no GPU.
- **M2 (done): real API backend + real-dataset loader** — OpenAI-compatible
  `APIBackend` (OpenAI / OpenRouter / vLLM) and a configurable-field JSONL loader
  for PrimeVul (`func`/`target`/`idx`). Validated by unit tests with a fake SDK
  (no spend) + a real smoke test. Concurrency, input truncation, and per-call
  error capture added for long runs.
- **M3 (built, GPU-pending): measured open-side energy** — `ZeusEnergyMeter`
  reads the NVML cumulative energy counter (delta per call, idle-subtracted) for
  models served locally by vLLM; `EstimatedEnergyMeter` (FLOP-based) covers the
  frontier/API side. Meter logic is unit-tested via an injected reader; the real
  `NvmlEnergyReader` runs on a rented cloud GPU. See below.

## Measured energy on a cloud GPU (M3)

No local GPU needed — rent a dedicated one (RunPod / Vast.ai / Lambda, ~$20-80
total). On the GPU host:

```bash
bash harness/scripts/setup_gpu.sh          # installs vLLM + pynvml, checks NVML, prints idle power
# set idle_power_w in the config, then serve a model and run:
vllm serve Qwen/Qwen3-Coder-30B-A3B-Instruct --port 8000 &
python -m harness.run --config harness/configs/primevul_local_energy.yaml   # concurrency=1
```

Energy is `energy_source: measured_nvml` for local open models and
`estimated_flops` for API/frontier — the two are kept strictly distinct so the
paper never conflates measured and estimated energy.

## Quickstart

```bash
python -m pytest harness/tests/ -q          # run the test suite (dry, no spend)
python -m harness.run --config harness/configs/pilot_dryrun.yaml   # mock dry-run
```

Outputs land in `harness/runs/<run_id>/`: `results.jsonl`, `manifest.json`,
`metrics.csv`, and `pareto_*.png`.

## Running with real APIs

1. Copy `.env.example` to `.env` and fill in the keys you'll use (`.env` is
   gitignored). The CLI loads it automatically.
2. Smoke-test the API path cheaply (~10 calls, a fraction of a cent):
   ```bash
   python -m harness.run --config harness/configs/pilot_api_smoke.yaml
   ```
   Adjust the model slug in that file to a current, cheap model if needed.

## Running on PrimeVul

1. Download PrimeVul JSONL (function-level, ~64 MB; gitignored) to
   `harness/data/primevul/primevul_test.jsonl`:
   ```bash
   mkdir -p harness/data/primevul
   curl -L -o harness/data/primevul/primevul_test.jsonl \
     "https://huggingface.co/datasets/colin/PrimeVul/resolve/main/primevul_test.jsonl"
   ```
   (Mirror of the PrimeVul dataset; original: GitHub `DLVulDet/PrimeVul`.)
2. Verify model slugs and run:
   ```bash
   python -m harness.run --config harness/configs/primevul_subset.yaml
   ```
   The config takes a stratified `n=2000` subset (±3% CI). Open models run via
   OpenRouter for now (estimated energy); measured open-side energy is M3.

## Structure

```
harness/
  schema.py            # pydantic models: Task, Response, GenParams
  config.py            # RunConfig + backend/meter registries + YAML loader
  runner.py            # run(): config -> metered inference -> results.jsonl
  data/loader.py       # JSONL fixture loader + stratified sampling
  data/fixtures/       # primevul_mini.jsonl (10 hand-made samples)
  backends/            # base + mock (api, local added later)
  meters/              # base(+compose) + cost + latency + energy(mock)
  tasks/vuln_detect.py # binary detection prompt + lenient output parser
  scoring/detection.py # accuracy/precision/recall/F1/parse_rate
  report/report.py     # per-model metrics CSV + Pareto plots
  run.py               # CLI entry point
  configs/             # run configs (pilot_dryrun.yaml)
  tests/               # pytest suite (34 tests)
```

Backends and meters are registered by name in `config.py`; the runner never
changes when we add real ones.

## Roadmap

- **M2** — `APIBackend` (OpenRouter + native Anthropic/OpenAI/Gemini) + real
  PrimeVul subset loader → small real frontier run (needs API keys). Real cost +
  latency + tokens.
- **M3** — rent a GPU → `LocalBackend` (vLLM) + `ZeusEnergyMeter` (NVML counter)
  + `CodeCarbonMeter` (full node) → **measured** open-side energy;
  `EstimatedEnergyMeter` (FLOP-based) for the frontier side. Sanity-check
  J/output-token vs the Samsi et al. ~3–4 J/token anchor.
- **M4** — full model roster + VD-Score (FPR≤0.5%) & pairwise metrics +
  SecVulEval / SecLLMHolmes + the offensive-agentic case study (EpG, pass@k).

## Reproducibility

Every run records its resolved config, seed, git SHA, timestamp, and package
versions in `manifest.json`. The mock backend is deterministic in `(seed, prompt)`
via SHA-256, so dry-runs reproduce exactly. Timestamps/run-ids are injected by the
CLI, never read inside the runner, so the core logic is deterministic.
