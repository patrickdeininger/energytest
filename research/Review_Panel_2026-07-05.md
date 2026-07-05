# Fresh Peer-Review Panel — 8 Reviewers
**Manuscript:** *Open or Frontier? A Cost-, Latency-, and Energy-Aware Benchmark of LLMs for Software Vulnerability Detection* (`main.tex`, 9 pp, MDPI *Computers*)
**Date:** 2026-07-05 · **Panel:** EIC + Methodology + Domain + Perspective(Green-AI) + Devil's Advocate + Structure + Academic-Language + Statistics/Maths/Logic
**Reviewers ran independently (no cross-referencing), read-only, evidence-based.** Two reviewers (Stats, Devil's Advocate) and the Methodology reviewer recomputed numbers from the raw `results.jsonl`/code.

---

## EDITORIAL DECISION: MAJOR REVISION

**Tally:** Major ×6 (EIC, Methodology, Domain, Perspective, Devil's Advocate, Stats) · Minor ×2 (Structure, Language — each scoped only to its lens). The Devil's Advocate raised CRITICAL issues → per panel rules an Accept is impossible; the decision is **Major revision of a fundamentally sound, unusually honest paper.**

**The paper's spine is solid** (consensus non-defects): the **cost-axis Pareto result is rock-solid and needs no estimate** — DeepSeek-V3.2 dominates every frontier model on *measured* USD/task, and "no frontier model is Pareto-optimal" is factually correct on the data. All arithmetic reproduces exactly (Stats recomputed every cell of the results table; Methodology recovered the accuracies to ±0.001). The balanced-accuracy metric choice is correct, the `energy_source` provenance discipline is exemplary, reproducibility engineering is above venue norm, and the limitations section is candid. **DeepSeek-V3.2's quality advantage is genuine** (beats even the strongest frontier model, Gemini, at p<0.001 on a paired balanced-accuracy bootstrap).

**But the two headline claims overreach the evidence and must be rescoped.**

---

## CRITICAL ISSUES (block acceptance; DA-flagged)

### C1 — The headline significance claim is false as stated. [Stats CRITICAL + Devil's Advocate CRITICAL + Methodology CRITICAL — three independent reviewers, two recomputed from raw data]
Abstract & §4.2: "the three highest-quality models … each significantly exceeding all three frontier models (McNemar p<10⁻⁵)." Only **2 of the 9** implied comparisons were run, and they are the two easiest. Recomputed with the paper's own `mcnemar()`:
- DeepSeek vs all three frontier: p = 6.6e-6, 2.3e-14, 1.6e-14 — **all hold** ✓
- Gemma vs GPT-5.1 = **2.3e-3** (not <1e-5); Gemma vs Gemini (bootstrap on balanced acc) = **p=0.057, n.s.**
- GLM-5 vs GPT-5.1 = **p≈0.59, non-significant and directionally reversed**; none of GLM's gaps reach 1e-5.

Also, **McNemar tests raw correctness, but the ranking is balanced accuracy** — the wrong estimand. Counterexample: GLM-5 has higher balanced accuracy than GPT-5.1 (0.647 vs 0.614) yet lower raw accuracy (0.560 vs 0.567).

**Fix:** replace McNemar-on-correctness with a **paired balanced-accuracy test** (stratified bootstrap resampling 549 pos + 1000 neg), report the full 3×3 matrix with a **Holm multiple-comparison correction**, and rewrite the claim to what survives: *DeepSeek-V3.2 significantly beats all three frontier models; Gemma-3-4B and GLM-5 beat the two weaker frontier models but not Gemini-3.1-Pro.*

### C2 — No uncertainty on the primary metric; CIs overlap. [Stats MAJOR + Methodology MAJOR]
The only CI reported (±0.025) is for **raw accuracy**, not balanced accuracy/MCC/F1 (the ranking metric). Balanced-accuracy CIs: DeepSeek 0.674±0.022 (lower bound 0.652 > Gemini 0.639, separates cleanly), but **Gemma (0.649±0.023) and GLM (0.647±0.018) both overlap Gemini (0.623±0.016).** **Fix:** add balanced-accuracy + MCC CIs to the results table (the bootstrap in C1 yields them for free).

### C3 — "So what?" — the deployment claim is unsupported at realistic prevalence. [Devil's Advocate CRITICAL + Perspective MAJOR + Domain MAJOR]
Every model is near chance; no model beats the always-safe baseline on raw accuracy. At PrimeVul's real 1:44 prevalence the "winners" yield **precision ≈ 3–4%** (≈96% false alarms); the entire balanced-accuracy ranking spans 2.9–3.7% precision — operationally indistinguishable. The paper rebalances to 549:1000 and defers VD-Score, yet the Discussion makes deployment-scale claims ("triage over millions of functions," "alert fatigue") that only the imbalanced regime supports. **Fix:** report a prevalence-aware metric (VD-Score / precision@k / FPR-at-fixed-recall) at 1:44 for the top models (you already have full-split predictions), and make the deployment recommendation **conditional** ("if deploying, prefer small open models").

### C4 — "Carbon footprint" is claimed but never computed. [Perspective CRITICAL]
Abstract, Intro, and Conclusions invoke "carbon footprint" / "environmental cost," but the paper reports only Joules — no grid carbon intensity, no PUE, no CO₂ figure. **Fix:** either convert properly (state grid intensity with a low/high range, PUE ~1.1–1.6, report per-task and at-scale gCO₂eq) or **retreat every carbon/environmental claim to "energy"** and scope carbon out explicitly. (A worked number also helps context: the *ratio* is dramatic but absolute footprints are modest.)

### C5 — The energy validation is oversold and does not validate the frontier assumption that drives the headline. [Devil's Advocate CRITICAL + Domain MAJOR + Methodology MAJOR + Perspective/Stats MINOR]
The two measured points (Qwen, Llama — both open, known active params) validate ε and token→energy linearity **for small/mid open models only**. They do **not** touch the **~100B frontier active-parameter assumption** (Table 1, "assumed"), which is the dominant uncertainty in frontier energy. The flagship "one-fortieth the energy" (Gemma 64 J vs Claude 2489 J) is **estimate-vs-estimate**, ≈ the assumed 100B/4B ratio × token ratio, validated by **zero** measured points. ε is calibrated to reproduce frontier per-query estimates, so frontier energy agreeing with that calibration is partly circular. **Fix:** reframe the energy advantage as "1–2 orders of magnitude" with an explicit **sensitivity band on frontier active-params** (e.g. 25B / 100B / 400B); state plainly the measured points validate only the open-model regime and that the **robust, measurement-independent** result is that the *cost* Pareto ordering is unchanged.

---

## MAJOR ISSUES

- **M1 — "Latency-Aware" in the title, but no latency is reported.** [EIC + Perspective + Structure + Methodology] Table has no latency column; "reported latency" is a dangling reference; §5.3 admits the pass is "pending" and confounded by queueing. **Fix:** report single-request latency (labeled confounded), or drop "Latency" from the title and demote to future work. (The thesis doesn't depend on latency → demotion is the low-risk fix.)
- **M2 — "Within a factor of two" contradicts the paper's own 2.2×.** [Structure + Language + Methodology MAJOR; Stats + DA MINOR — 5 reviewers] Qwen's 2.2× is *outside* 2×; the §4.4 sentence self-contradicts. **Fix:** "roughly a factor of two (0.8×–2.2×)" everywhere (abstract, C3-contribution, Fig-2 caption, limitations, conclusion).
- **M3 — Data contamination unaddressed.** [Domain] PrimeVul functions are almost certainly in every model's pretraining; differential memorization could confound the cross-tier comparison. **Fix:** post-training-cutoff CVE subset and/or the PrimeVul-paired subset; at minimum elevate to an explicit threat and temper claims.
- **M4 — Direct-answer config may handicap the frontier tier specifically.** [Domain + Methodology] Disabling reasoning depresses exactly the tier claimed to lose; Gemini (forced-reasoning) is the most competitive frontier model. **Fix:** run a reasoning-enabled subset for the 3 frontier + top open models and report whether the ranking survives; else reframe the headline explicitly as "in direct-answer mode" (incl. abstract).
- **M5 — No non-LLM or fine-tuned baseline.** [Domain] Cannot answer "is 0.67 good?" **Fix:** add ≥1 static analyzer (CodeQL/Semgrep/Flawfinder) on the same 1549 functions, and cite/compare PrimeVul's own fine-tuned numbers (and/or LineVul).
- **M6 — Config heterogeneity may confound accuracy, not just efficiency.** [Devil's Advocate + Methodology] GLM-5 (an open "winner," and a marginal comparator) ran at max_output 256 vs 64 for DeepSeek/Gemma. **Fix:** rerun in one config or show GLM's verdict is budget-invariant; report per-model mean output tokens.
- **M7 — Single seed / single safe-set draw / single rep → no ranking-stability estimate.** [Methodology + Devil's Advocate] The balanced-accuracy ranking is specificity-driven, and specificity rests on one random draw of 1000 safe functions; closely-spaced models (0.61–0.67) could reorder. **Fix:** bootstrap the safe pool / ≥3 independent draws; ≥3 reps for 2–3 models to bound API non-determinism.
- **M8 — "Open vs frontier" is confounded; cost is API price, not on-prem TCO.** [Devil's Advocate + Perspective] All 8 served via one gateway → a model-level finding, not a tier-level one; "negligible marginal cost" on-prem is asserted, not modeled. **Fix:** reframe as model-level; add a break-even/TCO model (amortize the H200 over throughput × utilization × electricity price) for the on-prem claim.
- **M9 — Input truncation may corrupt ground-truth labels; magnitude unreported.** [Domain] Truncation budget not stated; truncating can remove the vulnerable statement. **Fix:** state the budget, report the truncation rate + length distribution, add a robustness check on the untruncated subset.
- **M10 — Measurement-regime + idle-power reproducibility.** [Methodology] Concurrency-1 (low-util) measurement vs batched-calibrated ε; `idle_power_w: 60.0` is a config *placeholder* (was a real measured idle used for the active-energy subtraction?). **Also a real bug in the current fold-in:** the validation table's "Estimated" column is the **N=1549** mean, while the measurement is **N=300** — confirm/recompute the estimate on the identical 300 requests. **Fix:** report the measured idle used; note concurrency-1 is a pessimistic (open-favoring) bound; recompute Table-5 estimates on the same 300 requests.

---

## MINOR ISSUES (polish)
- **Samsi anchor overstated** — "brackets 3–4 J/tok" but both points (1.4, 11.6) *miss* the band (`within_samsi_anchor=False` for both). State they straddle and scale with size; not corroboration. [Stats, DA, EIC, Perspective, Methodology]
- **Add a Specificity (TNR) column** — the over-flagging argument rests on it but the table shows only recall. [Structure]
- **"Gross energy" promised in Methods but only active reported.** Add it or drop the promise. [Structure, Methodology]
- **Trim repetition** — "Pareto unchanged" stated ~5×; move the under/overshoot *mechanism* from Results §4.4 into Discussion. [Structure]
- **Language / AI-tells** [Language]: recycled "cost, latency, and energy" tricolon (~6–7×) and "first-class axes" (×5); reassurance layer "honest/transparent/faithful"; "Crucially,"; editorializing heading "…and That Is the Point"; thesis restated 3× in parallel antithesis. De-tell per the Language review.
- **Mechanics** [Language]: `locally-servable`→`locally servable` (adverb-ly not hyphenated); model-name hyphenation inconsistent ("Claude Sonnet 5" vs "Claude-Sonnet-5"); thousands separators (24{,}788 vs 1549); AmE/BrE ("judgement" vs "behavior" — MDPI = American → "judgment"); bf16 vs bfloat16; **NVML never expanded**; text says overshoot "1.3×" while Table 5 says "0.8×" (state one direction).
- **Missing references** [Domain]: Ullah et al. *SecLLMHolmes* (IEEE S&P 2024); Steenhoek et al. (ICSE 2024); Chakraborty et al. *ReVeal* (TSE 2021); Devign (NeurIPS 2019); Big-Vul (MSR 2020); DiverseVul (RAID 2023); Fu & Tantithamthavorn *LineVul* (MSR 2022); a static-analysis reference.
- **Submission metadata** — author/affiliation/email/ORCID placeholders; Data Availability "[repository URL]". [EIC]
- **Model version pins/dates** not stated (archival benchmark needs them). [EIC, DA]
- **ε citation mismatch** — paper says Jegham, code (`energy.py`) says Epoch. Reconcile. [Stats]
- **"for the first time to our knowledge"** — soften. [Domain]
- **Over-flagging characterization selective** — GLM-5 (0.941) and Llama (0.956) over-flag as much as frontier; qualify to DeepSeek/Gemma. [Domain]
- **Green-AI completeness** — one sentence each on water (cited but unreported), rebound/Jevons, SCI spec, and embodied/lifecycle carbon (cuts against the low-utilization on-prem case). [Perspective]
- **Single prompt template** — add a prompt-sensitivity check. [Domain]
- **Single-function context** — name inter-procedural blindness in limitations. [Domain]

---

## DISAGREEMENTS AMONG REVIEWERS
No factual conflicts — convergence was unusually high. The only spread is on overall severity: **Structure** and **Language** returned *Minor* because within their lenses the paper is genuinely clean (coherent thread, fluent prose). The six content/stats/framing reviewers returned *Major* because the binding problems live in claims, statistics, and scope — dimensions Structure/Language were not scoped to judge. The editorial decision follows the substantive majority: **Major.**

---

## PRIORITIZED REVISION ROADMAP
**Tier A — required, no new model runs needed (fixes the two overstated claims):**
1. Rescope the significance claim (C1): paired balanced-accuracy bootstrap, full 3×3 matrix, Holm correction; rewrite abstract/§4.2/conclusion to "DeepSeek beats all three; Gemma/GLM beat the two weaker but not Gemini."
2. Add balanced-accuracy + MCC CIs to the results table (C2).
3. Add a prevalence-aware metric at 1:44 (VD-Score / precision@k) and make deployment claims conditional (C3).
4. Resolve carbon (C4): compute gCO₂eq with stated assumptions, or retreat to "energy."
5. Reframe the energy validation + add a frontier active-param sensitivity band; anchor the robust claim on the *measured cost* Pareto (C5).
6. Fix "within a factor of two" → "≈2× (0.8–2.2×)" (M2); recompute Table-5 estimate on the same 300 requests + report measured idle (M10).
7. Resolve latency: report it (confounded) or drop it from the title (M1).

**Tier B — strongly recommended (may need runs):**
8. Contamination analysis (M3); reasoning-enabled subset (M4); static-analysis + fine-tuned baseline (M5); one-config rerun or budget-invariance check for GLM (M6); safe-set bootstrap / rep-variance (M7); on-prem TCO model (M8); truncation-rate report + untruncated robustness (M9).

**Tier C — polish:** all MINOR items (language de-tell pass, specificity column, missing references, metadata, version pins).

---
---

# INDIVIDUAL REVIEWER REPORTS (verbatim)

## 1. Editor-in-Chief — Major revision
Recommendation: **Major revision.** Fit with *Computers* is good (applied, deployment-oriented, security × green-AI × LLM benchmarking). Novelty is moderate/incremental — every measurement technique is borrowed; the delta over Neef/Dahiya is essentially "adds energy" + a broader open roster. The more striking, genuinely publishable finding is the *quality* result (small open beats frontier on a hard clean benchmark), currently subordinated to the efficiency-novelty framing. Scores: novelty/significance 60, readership relevance 82, overall quality 70.
Key weaknesses: [MAJOR] three co-equal axes promised but **latency neither cleanly measured nor reported** (demote or deliver); [MAJOR] the signature "energy as first-class axis" novelty is undercut because energy is *measured* for only 2/8 and the flagship 64 J vs 2489 J is estimate-vs-estimate (measure Gemma, or reposition around the quality result); [MAJOR] scope reads preliminary (one dataset/task/mode; several "not-finished-yet" limitations) — add a second dataset or the VD-Score regime, or explicitly reposition as a focused benchmark; [MINOR] some "beats frontier" gaps are ~1 CI half-width (Gemma 0.649 vs Gemini 0.623) — separate robust from marginal; [MINOR] no model version strings/dates; [MINOR] placeholder metadata; [MINOR] Samsi "brackets" straddles.

## 2. Methodology — Major revision
Scores: design rigor 55, statistical validity 42, reproducibility 72. Strengths: correct primary metric correctly implemented (verified `stats.py`), exemplary `energy_source` provenance, strong reproducibility engineering, honest limitations.
[CRITICAL] significance claimed for the wrong estimand (McNemar on raw correctness) and for untested comparisons — only 2 of 9 run; GLM-5 vs GPT-5.1 likely null/reversed; the binding GLM/Gemma-vs-Gemini gap (~0.024–0.026) untested (z≈2.0, p≈0.05). Fix: paired balanced-accuracy bootstrap + Holm + rewrite.
[MAJOR] no CI on the headline metric (the ±0.025 is raw-accuracy). [MAJOR] single seed / single safe-draw / single rep → no rank stability (specificity-driven ranking rests on one draw of 1000). [MAJOR] energy validation doesn't touch the ~100B frontier assumption that drives the 40× flagship (estimate-vs-estimate). [MAJOR] "within a factor of two" contradicted by 2.2×; also measured N=300 vs estimated N=1549 may be non-identical requests. [MAJOR] concurrency-1 measured vs batched-ε; `idle_power_w:60` is a placeholder. [MAJOR] "latency-aware" in title, no latency reported. [MINOR] token-budget asymmetry not quantified; parse-failure exclusion; unfulfilled "sensitivity range" promised in code.

## 3. Domain (LLMs for software security) — Major revision
Scores: literature coverage 52, task validity 55, domain contribution 60.
[MAJOR] data contamination never addressed (PrimeVul in pretraining; may confound cross-tier). [MAJOR] direct-answer config likely handicaps frontier specifically (Gemini, forced to reason, is competitive). [MAJOR] no static-analysis and no fine-tuned baseline → can't calibrate "is 0.67 good." [MAJOR] rebalancing + balanced accuracy discards PrimeVul's realistic imbalance while making deployment-scale claims (report VD-Score/precision@k). [MAJOR] energy validation doesn't validate the frontier estimates that drive the headline (sweep the assumed active-params). [MAJOR] truncation may corrupt labels; budget/rate unreported. [MAJOR] Neef/Dahiya positioning too thin — state their actual findings; if they already found open competitive, the novelty collapses to the energy axis. [MINOR] single-function context; single prompt; over-flagging claim selective (GLM/Llama over-flag too); no multiplicity correction; "first to our knowledge." Missing refs: SecLLMHolmes/Ullah (S&P'24), Steenhoek (ICSE'24), ReVeal (TSE'21), Devign, Big-Vul, DiverseVul, LineVul, a static analyzer.

## 4. Perspective (Green-AI / Deployment) — Major revision
Scores: practical impact 62, framing rigor 54, cross-disciplinary insight 60. Strengths: right axis in the right place; correct counter-based NVML (not sampled power); gross+active; honest measured-vs-estimated.
[CRITICAL] "carbon footprint" claimed, never computed (no grid intensity/PUE/CO₂) — convert or retreat to energy. [MAJOR] deployment cost argument is API pricing, not on-prem TCO ("negligible marginal cost" is unmodeled — add break-even). [MAJOR] "latency-aware" promised, no latency reported. [MAJOR] practical significance over-claimed at near-chance / 1:44 (precision ≈3.7%). [MAJOR] measured (device-scope NVML) vs estimate (infra-inclusive ε) mixes measurement boundaries. [MAJOR] embodied/lifecycle carbon ignored (cuts against low-utilization on-prem). [MINOR] water cited but unreported; rebound/Jevons; SCI spec; frontier energy doubly-assumed and unvalidated.

## 5. Devil's Advocate — Major revision
Strongest counter-argument: the headline is unsupported as tested and the metric hides that every model is useless for the stated deployment. Significance is proven with McNemar on *raw* correctness (the metric the paper calls meaningless); a paired balanced-accuracy bootstrap gives Gemma-vs-Gemini Δ=+0.026 p=0.057 (n.s.); the paper only tested the two weakest frontier models. At 1:44 prevalence the winners are 2.9–3.7% precision — all catastrophic, no model beats always-safe.
[CRITICAL] wrong test for the headline metric; [CRITICAL] overgeneralized/cherry-picked comparators (only DeepSeek survives against Gemini); [CRITICAL] "so what" — metric hides deployment failure; [CRITICAL] energy "validation" doesn't test the frontier assumption / partial circularity. [MAJOR] open-vs-frontier confounded (single gateway; n=3 vs n=5 hand-picked → model-specific, not tier-level); [MAJOR] config heterogeneity (GLM at 256 tokens); [MAJOR] single seed/subsample; [MAJOR] threshold vs discrimination confound (no AUC). [MINOR] "within a factor of two" self-contradicted; Samsi straddle; uncorrected multiplicity; no version pins.
Non-defects that survive: the **cost-axis Pareto claim is well-supported and estimate-independent**; open–frontier energy separation (10–40×) survives 2–3× error; **DeepSeek's advantage is real** (bootstrap p<0.001); reported stats are honest and reproduce exactly; metric choice correct.

## 6. Structure & Golden Thread — Minor revision
Scores: thread clarity 85, section cohesion 84, abstract–body–conclusion consistency 77. The thesis is a single traceable sentence; disciplined non-overclaiming; excellent metric-choice-first ordering; measured-energy woven into the primary artifacts.
[MAJOR] latency is a promised first-class axis with zero data (orphaned promise + dangling "reported latency" refs). [MAJOR] "within a factor of two" contradicted by the paper's own 2.2× (fix wording everywhere). [MINOR] §4.4 mixes Discussion-register mechanism into Results and repeats "Pareto unchanged" 5×; [MINOR] "gross energy" orphan; [MINOR] Specificity discussed but not shown in the table; [MINOR] abstract 0.61–0.62 vs body 0.613–0.623 rounding.

## 7. Academic Language — Minor revision (language only)
Scores: clarity 83, register/human-voice 67, mechanical correctness 82. Clear and rigorous; weakness is register, not clarity.
AI-tells: recycled "cost, latency, and energy" tricolon (~6–7×) + "first-class axes" (×5); reassurance layer "honest/transparent/faithful"; "Crucially,"; editorializing heading "…and That Is the Point"; thesis restated 3× in parallel antithesis; heavy em-dashes. Mechanics: ratio direction text 1.3× vs Table 0.8×; `locally-servable` hyphenation; model-name hyphenation inconsistency; thousands separators; AmE/BrE (judgement/behavior); bf16 vs bfloat16; NVML/MoE/CI undefined on first use; one 60-word sentence at l.151; "roughly half" vague. Strengths: structured abstract with real numbers; effective two-blind-spots intro; exemplary inline statistical prose; candid limitations.

## 8. Statistics / Maths / Logic — Major revision
Scores: statistical validity 55, mathematical correctness 91, logical soundness 55. **Verification:** all 8×8 results-table cells reproduce exactly from the raw data; DeepSeek confusion matrix (TP=460,FP=489,FN=89,TN=511) → bal.acc 0.6745, MCC 0.3426, F1 0.6141 ✓; baselines 0.646/0.354 ✓; CI half-width 0.0249 ✓; both reported McNemar values reproduce exactly; energy math E=2·N·10⁹·T·ε (ε=1e-11) and all validation numbers ✓. The formulas in `stats.py` are all correct.
[CRITICAL] "each … all three … p<10⁻⁵" overgeneralization — ran all 9: GLM-5 vs GPT-5.1 p≈0.59 (reversed), Gemma vs GPT-5.1 p=2.3e-3; only DeepSeek clears 1e-5 against all three. [MAJOR] significance test misaligned with primary metric (McNemar on raw correctness vs balanced-accuracy ranking; GLM higher bal.acc but lower raw acc). [MAJOR] uncertainty on the wrong metric — balanced-accuracy CIs for Gemma/GLM overlap Gemini. [MINOR] "within a factor of two" vs 2.19×; Samsi straddle (neither in band); the "2 points ⇒ faithful proxy ⇒ justified for frontier" leap overreaches (narrow to Pareto-ordering-intact); Table-5 direction 0.8× vs text 1.3×; ε citation Jegham vs code "Epoch"; per-model parsed-subset denominators differ slightly. Confirms the *direction* is sound: DeepSeek genuinely dominates all frontier; Pareto frontier holds; arithmetic overwhelmingly correct — fixes are to inferential wording and primary-metric uncertainty, not the data.
