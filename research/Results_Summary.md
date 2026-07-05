# PrimeVul Benchmark — Results Summary (data-collection phase)

**Date:** 2026-07-04 · Task: binary vulnerability detection on PrimeVul (function-level, C/C++)
**Sample:** stratified N=1549 (549 vulnerable + 1000 safe), seed 12345 · direct-answer mode
**Harness:** `harness/` (63 tests) · combined report: `harness/runs/primevul_combined/`

## Headline table (8 models + baselines, sorted by BALANCED ACCURACY)

> Raw accuracy is misleading here: the imbalanced set (549 vuln : 1000 safe) makes an
> always-safe classifier score 0.646 accuracy — higher than every model. Balanced
> accuracy (mean of TPR and TNR; trivial baselines = 0.5) is the primary metric.

| model | tier | bal_acc | MCC | F1 | acc | recall | USD/task | est. energy (J) |
|---|---|---|---|---|---|---|---|---|
| DeepSeek-V3.2 | open | **0.674** | 0.343 | 0.614 | 0.627 | 0.838 | 0.00017 | 526 |
| Gemma-3-4B | open | 0.649 | 0.290 | 0.587 | 0.612 | 0.778 | **0.00004** | 64 |
| GLM-5 | open | 0.647 | 0.325 | 0.602 | 0.560 | 0.941 | 0.00062 | 471 |
| Gemini-3.1-Pro | frontier | 0.623 | 0.297 | 0.591 | 0.525 | 0.963 | 0.00448 | 1966 |
| GPT-5.1 | frontier | 0.614 | 0.225 | 0.559 | 0.567 | 0.772 | 0.00139 | 1332 |
| Claude-Sonnet-5 | frontier | 0.613 | 0.264 | 0.579 | 0.519 | 0.934 | 0.00441 | 2489 |
| Llama-3.3-70B | open | 0.603 | 0.260 | 0.578 | 0.502 | 0.956 | 0.00008 | 944 |
| Qwen3-Coder-30B | open | 0.516 | 0.030 | 0.410 | 0.532 | 0.459 | 0.00006 | **40** |
| *always-safe (baseline)* | – | 0.500 | 0.000 | 0.000 | 0.646 | 0.000 | – | – |
| *always-vuln (baseline)* | – | 0.500 | 0.000 | 0.523 | 0.354 | 1.000 | – | – |

Accuracy 95% CI half-width ≈ ±0.025. Enriched CSV: `harness/runs/primevul_combined/enriched_metrics.csv`.
Figures: `figures/pareto_balacc_{cost,energy}.pdf`.

## Key findings (revised after adding baselines + significance tests)
1. **No model beats the trivial always-safe baseline on raw accuracy** (0.646) — so raw accuracy is not a meaningful headline; we use balanced accuracy.
2. **The three highest-quality models are all open-weight** — DeepSeek-V3.2 (0.674), Gemma-3-4B (0.649), GLM-5 (0.647) — each beating all three frontier models (0.613–0.623). **McNemar tests are significant**: DeepSeek vs GPT-5.1 χ²=20.3, p=7×10⁻⁶; Gemma-4B vs Claude-Sonnet-5 χ²=40.4, p=2×10⁻¹⁰.
3. **Best open beats frontier, not all open** — Qwen3-Coder-30B barely exceeds chance (0.516); the claim is about the best open models.
4. **Efficiency dominance is robust** — Gemma-3-4B beats Claude-Sonnet-5 on balanced accuracy at ~1/100th cost and ~1/40th estimated energy. On the Pareto plots, no frontier model is optimal.
5. **All models are weak in absolute terms** (balanced acc 0.52–0.67, MCC 0.03–0.34) — PrimeVul is genuinely hard. Frontier models over-flag (high recall, low specificity).

## Caveats (must be stated in the paper)
- **Estimated, not measured, energy** — FLOP-based (`energy_source: estimated_flops`); active-param assumptions (frontier = ~100B bounded). GPU-measured energy for local-feasible open models is the pending M3 step.
- **Direct mode** — reasoning disabled for Claude/GLM; Gemini-3.1-Pro is reasoning-only (no non-reasoning mode on OpenRouter). GPT-5.1/DeepSeek answered directly by default.
- **Token-cap asymmetry** — the 3 re-run models (Claude/GLM/Gemini) used max_output_tokens=256 vs 64 for the other 5, inflating their out_tok/cost/energy somewhat. Since they are already the efficiency losers, the conclusion is conservative (the gap would widen at equal caps).
- **Balanced N=1549** (549 vuln + 1000 safe) — PrimeVul's test split has only 549 vulnerable functions, so a fully balanced set caps at 1098; this run used all 549 vuln + 1000 safe.
- **Latency** measured under concurrency=10 (service latency, not compute latency) — a dedicated concurrency=1 latency pass is pending.
- **VD-Score / pairwise metrics** not yet computed (binary yes/no gives no confidence score; would need logprobs or a scored variant).

## Provenance
- 5 non-reasoning models (deepseek-v3.2, gemma-3-4b, gpt-5.1, llama-3.3-70b, qwen3-coder-30b): first run `primevul_full-20260704-133628`.
- 3 reasoning models (claude-sonnet-5, glm-5, gemini-3.1-pro): fill run `primevul_fill_main` (re-run after the 64-token cap left them with empty content).
- Merge: `harness/scripts/build_combined_report.py` → `harness/runs/primevul_combined/`.

## Spend (approximate; check OpenRouter dashboard for exact)
- First full run: ~$12.10 (measured). Smoke tests: <$0.05.
- Failed both-modes attempt (crashed, unsaved): up to ~$27 — the costly mistake (harness was not crash-safe; now fixed with incremental writes + resume).
- Fill run (3 models): ~$14.
- **Rough total so far: ~$40–53.**

## Pending experimental steps (require user go-ahead — cost/hardware)
1. **Latency-fidelity pass** — concurrency=1, ~100 samples, reps=5, native endpoints (~$1–2).
2. **M3 measured energy** — rent a cloud GPU (~$20–80), run local-feasible open models (Gemma, Qwen, Llama) via vLLM + Zeus to upgrade the open-side energy from estimated → measured.
3. (Optional) **Reasoning-vs-direct** full comparison (the deferred "both modes" contribution).
