# Stage 1 Research Plan — Open-Weight vs. Frontier LLMs for Vulnerability Detection: A Cost-, Latency-, and Energy-Aware Benchmark

**ARS academic-pipeline · Stage 1 (RESEARCH) deliverable · deep-research full mode**
Date: 2026-07-04 · Target: **MDPI Computers (IF 5.2)** · Scope: defensive primary + offensive secondary · Energy: **cloud-GPU measured** (open models on a rented GPU + Zeus/CodeCarbon; frontier estimated) · Status: Stage 1 complete + novelty sweep passed → entering data-collection (pilot harness)

> Evidence base: 5 parallel research threads, majority verified-by-fetch against primary sources (arXiv HTML/PDF, GitHub, HuggingFace, MDPI/Scopus metrics). Working notes in `scratchpad/stage1_*.md`. Citations flagged where only search-snippet confirmed.

---

## 1. Research Question Brief

### 1.1 Working title
*Local or Latent? A Cost-, Latency-, and Energy-Aware Benchmark of Open-Weight vs. Frontier LLMs for Software Vulnerability Detection.*

### 1.2 Core research question
When off-the-shelf **open-weight LLMs run locally** are compared against **frontier API models** on realistic software-vulnerability detection, how do they trade **detection quality** against **monetary cost, latency, and energy** — and where does each model sit on the **accuracy–efficiency Pareto frontier**?

### 1.3 Sub-questions
- **RQ1 (Quality):** How large is the open-vs-frontier detection-quality gap on a *label-clean, realistically imbalanced* benchmark (PrimeVul), and a *tiered-difficulty* benchmark (VulDetectBench)?
- **RQ2 (Efficiency):** What are the per-task **cost (USD)**, **latency (TTFT, tokens/s)**, and **energy** profiles — measured directly for local models, bounded-estimated for APIs — and what do the **accuracy-per-Joule / -per-dollar / -per-second** frontiers reveal about deployment choices?
- **RQ3 (Robustness of the method):** Does the picture hold in a harder **multi-turn offensive-agentic** regime (secondary case study), where clean per-task energy attribution breaks down and must be replaced by **Energy-per-Successful-Goal (EpG)** and **pass@k**? I.e., does the measurement methodology survive the worst case?

### 1.4 FINER assessment
| Criterion | Verdict | Basis |
|---|---|---|
| **Feasible** | ✅ Strong | Datasets public (PrimeVul CC-BY-4.0, VulDetectBench); models via OpenRouter + local GPU; primary study is *cheap* single-shot classification (~$100s API); 2–4 months. |
| **Interesting** | ✅ High | AI energy/cost is a front-page topic; security openly under-benchmarks local models; practical on-prem-vs-API decision. |
| **Novel** | ✅ Defensible (narrowed) | **Energy as a first-class per-task axis is unclaimed in security.** Differentiated from the two closest 2026 works (see §2). |
| **Ethical** | ✅ Clearable | Defensive framing, public/patched benchmarks, sandboxed, no exploit-artifact release, explicit DURC statement. |
| **Relevant** | ✅ High | Directly informs security-team tooling decisions + sustainability reporting. |

### 1.5 Scope boundaries
- **In scope:** open-weight (local) vs frontier (API) LLMs; vuln **detection/classification** as primary; cost/latency/energy measurement; a bounded offensive-agentic case study.
- **Out of scope:** training/fine-tuning new detectors; releasing novel exploits or offensive agents; live-HTB-VM headline results; claiming *measured* energy for closed APIs.

---

## 2. Novelty & Positioning (the sharpened gap)

**The gap has moved — position accordingly.** "Open models are ignored in security" is weakening monthly (multiple 2026 papers now do open-vs-frontier). **Lead instead with energy + open-zoo breadth + rigorous cost/latency.**

### 2.1 Nearest prior work (must differentiate explicitly)
- **Dahiya et al. 2026 (arXiv:2605.23243)** — dual-mode vuln+pentest; reports latency/tokens/cost. **But** compares frontier vs the authors' *own LoRA-fine-tuned* Qwen3, **not the off-the-shelf open zoo**, and **no energy**. → "specialized vertical model" paper.
- **Neef et al. 2026 (arXiv:2606.21397)** — off-the-shelf open (Qwen3.5, MiniMax) vs frontier on web vuln detection; reports runtime + coarse cost. **But** only 3+3 models, single narrow static task, **no energy**.
- **Happe & Cito 2025 (arXiv:2504.10112)** — meta-review of 19 offensive-security papers: proprietary models dominate, open underused, only 10/18 track cost, **energy reported by none.** ← strongest gap anchor.

### 2.2 Our unclaimed ground (the contribution)
1. **Energy as a co-equal per-task axis** in a security benchmark (first, to our verified knowledge).
2. **Breadth**: 5–6 off-the-shelf open models spanning size tiers × 3 frontier — a genuine Pareto spread, not a 1-vs-N or 3-vs-3.
3. **A two-regime measurement methodology** resolving the frontier-API energy asymmetry (measured-local + bounded-estimated-API) — portable beyond security; imports HELM/MLPerf-Power/CodeCarbon rigor into a security task.
4. **Robustness demonstration**: the same methodology stress-tested in the messy offensive-agentic regime via EpG/pass@k.

### 2.3 Final novelty sweep (2026-07-04) — GAP CONFIRMED INTACT ✅
Targeted search for the scooping combination *(security vuln-detection × open-vs-frontier × energy as measured first-class axis)* found no preemption. Two non-overlapping camps:
- **General energy benchmarks, no security task** (fresh precedents to cite): TokenPowerBench arXiv:2512.03024 (AAAI; J/token, 15+ open LLMs); "Smart but Costly?" 2511.07698 (accuracy×energy Pareto); "From Prompts to Power" 2511.05597; Bench360 2511.16682; "Efficient & Green LLM4SE" 2404.04566 (vision, accuracy–energy Pareto); "Towards Green AI: Decoding Energy of LLM Inference in SW Dev" 2602.05712.
- **Recent security evals, no energy** (reinforce gap): SEC-bench Pro 2605.26548; Seclens 2604.01637; "Vuln Detection at Project Scale" 2601.19239 (cost anchor: RepoAudit 225M input tok / >7h per project).
- **Watch:** general energy-benchmark surge means the "first to measure energy" window is real but closing → defensibility rests on energy + security-task + open-zoo breadth *together*. Re-run sweep at Stage 4.5 before submission.

> ⚠️ Fast-moving space — repeat this sweep at Stage 4.5 before submission.

---

## 3. Methodology Blueprint

### 3.1 Paradigm & design
Positivist/empirical, quantitative controlled benchmark. Factorial: **model × task-instance × run-repetition**, two measurement regimes (local vs API).

### 3.2 Benchmarks
- **Primary backbone — PrimeVul** (arXiv:2403.18624, ICSE'25; license **MIT — verify** vs CC-BY on mirror): CVE-linked, near-human labelers (PrimeVul-OneFunc 86%, NVDCheck 92%), realistic **1:32.8 imbalance**, **0% train→test leakage**. Metrics: **VD-Score = FNR@FPR≤0.5%** + pairwise P-C/P-V/P-B/P-R on 5,480 pairs. Frontier LLMs **fail below random**: GPT-4+CoT P-C **12.94%** vs 22.70% random baseline; StarCoder2 **68%→3% F1** BigVul→PrimeVul. Bounded self-contained C/C++ functions = **cleanest per-sample energy/latency attribution** (favored over repo-level/variable-context sets). Stratified subset per §4.1.
  - *Label-audit nuance to state precisely:* the "BigVul 25% / Devign 24%" noise figures are **positive-class-only** audits (PrimeVul/DiverseVul); the independent **Croft et al. ICSE'23 (arXiv:2301.05456)** all-label audit reports **BigVul 54.3% / Devign 80%**. Cite both — they measure different things. Older sets also carry leakage (BigVul 12.7%). This is itself a finding + the justification for choosing PrimeVul.
- **Companion (harder, fresh) — SecVulEval** (arXiv:2505.19828, AIware'26): 25,440 fns / 5,867 CVEs / 145 CWEs, C/C++, **statement-level** (adds localization), de-duplicated; baselines Claude-3.7 23.8% F1 > GPT-4.1 22.4% > open. *Verify license before redistribution.*
- **Robustness overlay — SecLLMHolmes** (arXiv:2312.12575, IEEE S&P'24, **GPL-3.0**): 228 scenarios; GPT-4 89.5% acc but **flips ~26%** on trivial renaming → cheap, high-signal robustness metric.
- *(Alt companions, UNCONFIRMED — verify to primary source first: VulDetectBench arXiv:2406.07595 tiered tasks; VulBench arXiv:2311.12420. Defensive thread could not confirm their stats.)*
- **Secondary case study (robustness) — one Dockerized offensive-agentic benchmark**: recommend **Cybench** (arXiv:2408.08926) or **NYU CTF Bench** (arXiv:2406.05590) or **CVE-Bench** (arXiv:2503.17332), public/educational, sandboxed. Small scope; report **EpG + pass@5**.

### 3.3 Model roster (final selection at build time; indicative)
| Bucket | Candidates | Why |
|---|---|---|
| Open — small (7–8B) | Qwen3-Coder-8B-class, Gemma3, Llama-3.x-8B | cheap local; low end of Pareto |
| Open — mid (24–34B) | Devstral-Small-24B, DeepSeek-Coder-33B, Qwen3-Coder-30B (MoE, 3.3B active) | single 24–48 GB GPU w/ quant |
| Open — large (70B+/MoE) | one 70B-class or DeepSeek-V4/GLM-class via quant/OpenRouter | high end (energy-asymmetry caveat if via API) |
| Frontier (API) | Claude Sonnet, one GPT-5-class, Gemini 3 Pro | native APIs for latency + OpenRouter for breadth |

### 3.4 Measurement protocol (the paper's spine)
**Two regimes, never conflated:**
- **Local (measured):** GPU energy via **Zeus** (`nvmlDeviceGetTotalEnergyConsumption` counter — avoids the NVML 25%-sampling error, arXiv:2312.02741) + full-node via **CodeCarbon**; idle-subtracted **active Joules/task** and **J/output-token**; fixed power cap; batch=1.
- **API (measured cost + latency + bounded energy *estimate*):** exact **USD/task** from published pricing; client-side **TTFT / total latency / tokens-per-sec** on **native endpoints** (not via OpenRouter's extra hop); energy as a **published-estimate *range*** (Epoch FLOP method ~0.3 Wh/GPT-4o-query; Jegham et al. arXiv:2505.09598 multipliers) with **sensitivity analysis** over (active params, utilization, PUE). Never place measured-local and estimated-API energy in the same cell unflagged.
- **Controls:** temp=0, fixed seed & max-output-tokens, ≥5 repetitions (median+IQR), warm-up discard, logged model-versions + price snapshots. Full per-task logging schema in `scratchpad/stage1_energy_methodology.md`.
- **Reporting:** **Pareto frontiers** — accuracy vs Joules/task (local; API estimate band overlaid), accuracy vs USD/task (the *fair* cross-regime plot), accuracy vs latency; plus J/task→gCO₂eq (avg + marginal grid).
- **Offensive case study:** per-*trajectory* energy + **EpG** (total energy over all attempts ÷ solved goals; agentic ≈4.33× overhead, arXiv:2605.22883) + pass@1/pass@5; tokens as the only cross-comparable frontier proxy.

### 3.5 Validity threats (pre-empted) — full table in energy notes
Hardware specificity (report J/token, ≥2 GPUs) · NVML sampling (Zeus counter) · non-determinism (temp0/≥5 reps) · API opacity (no energy claim; estimate+sensitivity) · scope mismatch (match GPU-board/full-node/wall) · verbosity (per-output-token) · batching operating point · grid avg-vs-marginal carbon · temporal drift (log versions/prices).

---

## 4. Feasibility & Budget Sizing

### 4.1 Compute/cost (measured-basis estimate)
- **Primary detection is cheap.** Subset design: stratified **N≈2,000 = 1,000 vuln/patched pairs, CWE-stratified → ±3% 95% CI** on accuracy/P/R (n≈2,400 → ±2%); a **VD-Score track** tops up to ~2,000–3,000 negatives (needed to resolve FPR≤0.5%); + **SecLLMHolmes 228** robustness scenarios. At ~0.7k in + ~0.15k out per call → **$7–20 per frontier model per pass**, <$2 open. Full roster (~4 open + 3 frontier × 2 prompt styles) stays **under a few hundred $** total. Full PrimeVul test ≈ $110–160/model; full DiverseVul/Draper = prohibitive → always subsample. Reproducibility: publish exact sampled IDs + seed + truncation rule (e.g. max_input 2,048).
- **Offensive secondary is the cost driver but bounded:** ~$1–3/task × ≥5 repeats × ~40 tasks × several models ≈ **$500–2,000** API (per offensive thread).
- **Realistic total: API ≈ $300–1,500; local electricity modest; wall-clock 2–4 months.**
- **Pipeline orchestration** (this ARS run: writing→review→revise→finalize) ≈ **$4–6** of Opus tokens — negligible vs the experiments.

### 4.2 Infrastructure needs
- **Rented cloud GPU** (dedicated instance — RunPod/Vast/Lambda; one *reference GPU*, e.g. A100-40/80GB or L40S/RTX-4090; ~$20–80 total for the open-side energy runs), **vLLM** for serving + **Zeus** (NVML energy counter) + **CodeCarbon** (full-node); native Anthropic/OpenAI/Gemini keys + OpenRouter (user has all keys). Largest open models optionally via OpenRouter (estimated energy). Report reference GPU/driver/vLLM/quant/power-cap for reproducibility.

### 4.3 Interaction-count budget (advisory, pipeline caps)
Worst-case round-trips this pipeline: 2 revision loops + ≤2 integrity re-verify loops. Direct-output mode → minimal coaching round-trips.

---

## 5. Venue Recommendation

| Rank | Journal | IF 2025 | Fit rationale |
|---|---|---|---|
| **#1 topical** | **J. of Cybersecurity & Privacy (JCP)** | 3.8 (CiteScore 9.1, Q1) | Tightest security fit; reviewers feel the gap; low APC (1000 CHF); Scopus. Class `jcp`. |
| **#1 impact/efficiency-framed** | **Computers** | 5.2 | Explicitly covers performance/energy + ML + security; fastest decisions (~17.5d). Class `computers`. |
| Alt (highest IF) | **AI** | 6.5 | Benchmarking-methodology framing; less security-specific. Class `ai`. |
| Broad fallback | Electronics / Future Internet | 2.9 / 4.6 | High volume / AI+security+systems. |

**Recommendation:** decide by framing. Security-first → **JCP**. Efficiency/benchmarking-first with higher IF + fast turnaround → **Computers**. (This is a checkpoint decision for you.)

---

## 6. Key References (annotated, verified)

**Gap/positioning:** Happe & Cito 2504.10112 · Dahiya 2605.23243 · Neef 2606.21397 · "SLMs for cybersecurity" 2510.14113.
**Detection benchmarks:** PrimeVul 2403.18624 · SecVulEval 2505.19828 · SecLLMHolmes 2312.12575 · DiverseVul 2304.00409 · CVEfixes 2107.08760 · CleanVul 2411.17274 · CASTLE 2503.09433 · CyberSecEval 2312.04724 · (unconfirmed: VulDetectBench 2406.07595, VulBench 2311.12420).
**Dataset label-quality:** Croft et al. ICSE'23 2301.05456 (BigVul 54.3%/Devign 80% all-label audit) · ReVeal critique 2009.07235.
**Offensive benchmarks:** Cybench 2408.08926 · NYU CTF 2406.05590 · CVE-Bench 2503.17332 · AutoPenBench 2410.03225 · BountyBench 2505.15216 · Kang one-day 2404.08144.
**Energy/efficiency methodology:** Luccioni 2311.16863 · Samsi 2310.03003 · Zeus (NSDI'23) · MLPerf-Power 2410.12032 · Part-time Power (NVML) 2312.02741 · Epoch AI (GPT-4o ~0.3 Wh) · Jegham 2505.09598 · EpG 2605.22883 · HELM 2211.09110 · CodeCarbon.

---

## 7. Risks & Mitigations
1. **Novelty erosion** (fast field) → final novelty sweep at Stage 4.5; lead with energy axis (least contested).
2. **Frontier-energy un-measurability** → never claim measured; report cost+latency+estimate-range+sensitivity; separate tables.
3. **Offensive variance** → keep it *secondary*; ≥5 runs; pass@k + CIs; EpG.
4. **Dataset label noise** → PrimeVul (human-verified) as primary; use BigVul only to *demonstrate* inflation.
5. **DURC/ethics** → public/patched benchmarks, sandbox, no artifact release, explicit DURC statement + cover letter.
6. **Hardware specificity** → report portable J/token; ideally ≥2 GPUs; log full config.

---

## 8. Recommended decision (for FULL checkpoint)
- **Scope:** defensive vuln-detection **primary** (PrimeVul + VulDetectBench) + offensive-agentic **secondary case study** (one Dockerized benchmark). ✅ evidence-backed.
- **Contribution:** energy-first, open-zoo-breadth, two-regime methodology.
- **Venue:** ✅ **MDPI Computers (IF 5.2)** — efficiency-aware benchmarking framing, covers perf/energy + ML + security, fast decisions (user-selected 2026-07-04). Class option `computers`.
- **Next:** on approval → build the benchmark + measurement harness and run the experiments (data-collection phase between Stage 1 and Stage 2), then Stage 2 writes from real numbers.
