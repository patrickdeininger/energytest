# Benchmark Harness — Design Spec

**Date:** 2026-07-04
**Project:** Open-weight vs. frontier LLM vulnerability-detection benchmark (cost/latency/energy axes) → MDPI *Computers*
**Status:** Approved design · pilot = dry-run plumbing (zero spend, no GPU)
**Related:** `research/Stage1_Research_Plan.md`

## 1. Purpose

Build the measurement harness that produces every empirical number in the paper: for each (model, code sample), obtain a vulnerability-detection prediction and measure **accuracy, monetary cost, latency, and energy**. The **pilot** validates the entire pipeline end-to-end using a **mock backend + mock energy meter** — no API spend, no GPU — so the plumbing is proven before real backends are swapped in.

## 2. Goals / Non-goals

**Goals (pilot):**
- Full end-to-end pipeline: dataset → prompt → (metered) inference → parse → score → report (tables + Pareto plots), runnable with `pytest` and one CLI command, zero external cost.
- Clean, pluggable interfaces so real backends/meters drop in without runner changes.
- Reproducibility scaffolding from line one (resolved config, seed, git SHA, versions, price snapshot per run).

**Non-goals (pilot — designed-for but stubbed):**
- Real API calls; real GPU/energy measurement; VD-Score FPR sweep; pairwise (P-C) metric; offensive-agentic case study; full model roster; dataset download.

## 3. Architecture

Config-driven runner wiring **swappable backends** and **swappable meters**. Each unit has one responsibility, a defined interface, and is independently testable.

```
config(YAML) → DatasetLoader → [ Runner: for each (model × task × rep):
                                   Prompt.build → Meters.wrap(Backend.generate) → Prompt.parse ]
             → results.jsonl → Scorer → Reporter(tables CSV + Pareto PNG)
```

### 3.1 Component contracts

| Module | Public interface | Depends on |
|---|---|---|
| `harness/schema.py` | pydantic models: `Task`, `Response`, `MeasuredResult`, `RunConfig`, `ModelSpec` | pydantic |
| `harness/data/loader.py` | `load_tasks(cfg) -> list[Task]`; stratified sampler; fixture loader | schema |
| `harness/backends/base.py` | `class Backend(ABC): def generate(self, prompt:str, params:GenParams) -> Response` | schema |
| `harness/backends/mock.py` | `MockBackend` — deterministic pseudo-prediction from a seed + task id | base |
| `harness/meters/base.py` | `class Meter(ABC): def measure(self, call:Callable[[],Response]) -> tuple[Response, dict]` | schema |
| `harness/meters/cost.py` | `CostMeter(price_in, price_out)` → `{usd_cost, input_tokens, output_tokens}` | base |
| `harness/meters/latency.py` | `LatencyMeter` → `{ttft_ms, total_ms, tokens_per_s}` | base |
| `harness/meters/energy.py` | `MockEnergyMeter` → `{energy_j, active_energy_j}` (deterministic); interface for Zeus/CodeCarbon/Estimated later | base |
| `harness/tasks/vuln_detect.py` | `build_prompt(task) -> str`; `parse(text) -> Prediction(label:int, raw:str, parsed_ok:bool)` | schema |
| `harness/runner.py` | `run(cfg) -> Path` (writes `results.jsonl` + run manifest) | all above |
| `harness/scoring/detection.py` | `score(results) -> dict` (accuracy, precision, recall, F1, confusion, parse_rate; VD-Score/P-C = stubs raising NotImplemented w/ clear msg) | schema |
| `harness/report/report.py` | `build_report(run_dir)` → per-model metrics CSV + Pareto PNGs (accuracy vs cost/latency/energy) | pandas, matplotlib |
| `harness/run.py` | CLI `python -m harness.run --config <yaml>` → runner → scoring → report | runner, scoring, report |

### 3.2 Meter composition

The runner composes meters around the backend call so each measures the *same* invocation:
```
call = lambda: backend.generate(prompt, params)
response, metrics = compose(meters).measure(call)   # merges each meter's dict
```
Order matters only for latency (must be the outer wall-clock wrapper); the runner fixes a canonical order: `Latency(Energy(Cost(call)))`.

## 4. Data & output schemas

**`Task`**: `{id:str, code:str, label:int(0/1), cwe:str|None, source:str, meta:dict}`
**Per-task result row (`results.jsonl`)**: run_id, model_id, task_id, rep, prompt_hash, prediction, correct(bool), parsed_ok, input_tokens, output_tokens, usd_cost, ttft_ms, total_ms, tokens_per_s, energy_j, active_energy_j, backend, meter_set.
**Run manifest (`manifest.json`)**: timestamp (injected, not `Date.now()` in-code — passed via CLI/config), git_sha, resolved_config, seed, harness_version, price_snapshot, python/pkg versions.

## 5. Config schema (`configs/pilot_dryrun.yaml`)

```yaml
run_name: pilot_dryrun
seed: 12345
dataset: { source: fixture, path: harness/data/fixtures/primevul_mini.jsonl, n: 10, stratify_by: label }
task: vuln_detect_binary
models:
  - { id: mock-small,  backend: mock, params: {behavior: high_recall},  price: {in: 0.5,  out: 1.5} }
  - { id: mock-frontier, backend: mock, params: {behavior: balanced},   price: {in: 5.0,  out: 25.0} }
meters: [cost, latency, energy_mock]
reps: 2
gen: { temperature: 0.0, max_output_tokens: 128 }
output_dir: harness/runs
```

## 6. Testing strategy (TDD — tests written first)

- `test_scoring.py`: known confusion counts → exact P/R/F1/accuracy; parse-rate; edge cases (all-correct, all-wrong, empty).
- `test_meters.py`: CostMeter tokens×price math; LatencyMeter monotonic timings; MockEnergyMeter determinism.
- `test_loader.py`: fixture loads N tasks; stratification balances labels; bad rows rejected.
- `test_parser.py`: vuln_detect parse handles "yes/no", JSON, verbose CoT, and garbage → `parsed_ok=False`.
- `test_backend_mock.py`: determinism given (seed, task_id); token counts populated.
- `test_e2e_dryrun.py`: run `pilot_dryrun.yaml` → assert results.jsonl rows == n×models×reps, manifest present, report CSV + ≥1 Pareto PNG produced, all metrics in valid ranges.

## 7. Extensibility path (post-pilot, no runner changes)

- `backends/api.py` — `APIBackend` (OpenRouter + native Anthropic/OpenAI/Gemini via one client); real token/latency.
- `backends/local.py` — `LocalBackend` (vLLM, batch=1).
- `meters/energy.py` — `ZeusEnergyMeter` (NVML counter), `CodeCarbonMeter` (full node), `EstimatedEnergyMeter` (FLOP-based for API/frontier; open = known params, frontier = bounded + sensitivity).
- `scoring/detection.py` — implement VD-Score (FPR≤0.5% sweep) and pairwise P-C once paired PrimeVul data is wired.
- `data/loader.py` — real PrimeVul/SecVulEval loaders + stratified subset (N≈2,000, 1,000 pairs).

Each is registered by name in config; the runner is closed for modification.

## 8. Dependencies

**Pilot:** `pydantic`, `pyyaml`, `pandas`, `matplotlib`, `pytest`.
**Deferred (with their backends/meters):** `vllm`, `zeus-ml`, `codecarbon`, `openai`/`anthropic`/`litellm`, `datasets`.

## 9. Determinism note

Scripts/runtime must not call wall-clock for reproducible artifacts *except* the latency meter (which legitimately times execution). Run timestamps are injected via CLI/config, not read inside pure logic, so tests are deterministic.

## 10. Milestones

1. **M1 (this session):** pilot dry-run — all modules + tests green + one example run producing tables & Pareto plots from the fixture.
2. **M2:** `APIBackend` + real PrimeVul subset loader → small real frontier run (needs API keys).
3. **M3:** rent GPU → `LocalBackend` + `ZeusEnergyMeter`/`CodeCarbonMeter` → measured open-side energy; sanity-check J/token vs Samsi 3–4 J/token.
4. **M4:** full roster + VD-Score/pairwise + offensive-agentic case study.
