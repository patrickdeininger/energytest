# Response to Reviewers — Round 1

**Manuscript:** *Open or Frontier? A Cost- and Energy-Aware Benchmark of Large Language Models for Software Vulnerability Detection*
**Journal:** *Computers* (MDPI) · **Decision:** Major revision

We thank all three reviewers. The reviews converged on the same four issues and we found them correct in every case — most importantly Reviewer 2's point 1, that our evidence supports a decisive *efficiency* advantage together with quality *competitiveness*, not quality dominance. We have restructured the paper's claims around that distinction rather than defending the original wording.

Acting on the reviews produced five findings we did not anticipate. Four of them make our own results look worse, and we report all five:

1. **Reviewers 2 and 3 were right that our learned baseline was a strawman — and the proper baseline beats every LLM we tested.** A 125-million-parameter CodeBERT fine-tuned on PrimeVul reaches 0.765 balanced accuracy against the best LLM's 0.711, at negligible cost. This narrows the paper's scope: our comparison is a comparison *among LLMs*, not a search for the best detector.
2. **A *p*-value in §4.2 was wrong.** Two independently written scripts agree the reported 7×10⁻⁴ should be a bound below the bootstrap's resolution.
3. **Flawfinder's precision was reported at a single threshold.** Swept properly it reaches 13.4%, not the 6% we claimed — which makes our LLM results look worse by comparison.
4. **The FLOP energy estimator describes single-request, not batched, serving.** A measured concurrency sweep shows it sits 5–17× above batched energy, so the absolute energy and carbon figures in the submitted manuscript are overstated by roughly an order of magnitude.
5. **A hypothesis of our own, tested and refuted.** We suspected serving-provider dependence explained an inter-epoch shift; a three-provider controlled experiment shows the effect is below 0.01 and not significant. We report the negative result.

Section numbers refer to the revised manuscript.

---

## Summary of changes

| # | Change | Raised by |
|---|---|---|
| 1 | Claim hierarchy recalibrated: efficiency = configuration-invariant headline; quality = configuration-specific; parity, not dominance | R1, **R2#1**, R3 |
| 2 | New §4.7: Family A budget-matched comparison + output-budget sensitivity across all eight models | **R1**, R2#2, R3#6 |
| 3 | New §4.6 concurrency sweep; Table 4 energy-provenance column; Fig. 2 provenance encoding; new Fig. 3 sensitivity band | R1, R2#3, R2#7, R3#2 |
| 4 | New §3.3 provider price dispersion + Table 3; provider pinning; §5.1 break-even from measured throughput | **R1**, R2#4 |
| 5 | New §4.4: Semgrep, Cppcheck, and a **PrimeVul-fine-tuned detector** with swept thresholds; CodeQL inapplicability documented | R2#5, R3#5 |
| 6 | New §4.8 robustness: prompt paraphrases, three safe-pool draws, repeated generations | R2#6, R3#4 |
| 7 | New §4.3 deployment utility at realistic prevalence + confidence-elicitation analysis, elevated into abstract and conclusions | **R1**, R2#8 |
| 8 | New Appendix A: parsed sets, CI construction, both hypothesis families, complete pairwise table | R2#9 |
| 9 | New Appendix B: prompts, parsing precedence, model versions, pinned providers, decoding, retry policy, latency | R3#3, R2#7 |
| 10 | §2.3 rewritten: "first" replaced by a scoped claim + comparison table; recent cost-aware work added | R3#1, R2, R3 |
| 11 | English pass; longest sentences reduced | R1 |

---

## Reviewer 1

> **The comparison is not completely equal between all models: some models use reasoning and others do not, the output-token limits are not always the same...**

Agreed — the most-repeated point across all three reviews. **New §4.7** reports the three comparisons you named: same token budget, normal configuration, best-performing configuration.

**Family A** (Table 6) runs every model at 64 output tokens with reasoning disabled where permitted, in a single epoch with providers pinned. The open-weight lead survives and strengthens: DeepSeek-V3.2 (0.711) significantly exceeds all three frontier models. But the margin against the *best* frontier model is now essentially nil — Claude-Sonnet-5 reaches 0.653, level with Gemma-3-4B to three decimals (*p*=0.98) and third on MCC — and we state that plainly rather than resting on "the three highest-scoring models are all open-weight".

We also isolated the budget confound directly (Table 7). **Seven of eight models move by ≤0.004 balanced accuracy between 64 and 256 output tokens, none significantly** (*p* ≥ 0.34). The asymmetry you flagged is empirically negligible. Gemini-3.1-Pro is the exception at +0.061, and its parse rate explains it entirely (0.542 → 0.991): the gain is a *parsing* effect, not a reasoning one. It returns `HTTP 400: "Reasoning is mandatory for this endpoint and cannot be disabled"`, so it cannot be budget-matched at all; we report its failure rate rather than scoring it against a set it did not answer.

> **Claims about energy dominance and the Pareto frontier are sometimes stronger than what the design can fully support.**

Agreed; see the claim hierarchy under Reviewer 2 #1. "Dominate" is removed wherever it referred to quality.

> **Figure 2 should show much more clearly which values are measured and which are estimated, preferably with uncertainty ranges.**

Done. Table 4 carries an explicit **Energy source** column with frontier sensitivity ranges inline; Figure 2 distinguishes measured from estimated by marker shape *and* fill, with horizontal sensitivity bars; **new Figure 3** sweeps the active-parameter assumption across 25B–400B. Fixed multipliers are gone.

This turned out to matter more than presentation. We re-measured all three locally servable models across a concurrency sweep (§4.6), and two results followed. The concurrency-1 figures **replicate** — Llama-3.3-70B at 739.9 J against the published 738 (1.00×), Qwen at 84.0 against 88 (0.95×), on a different pod seven weeks later with a different measured idle draw. And **the estimator describes single-request serving, not the batched serving it was calibrated for**: within 2× of the c=1 measurement for all three models, but 5.4–16.9× above the c=64 measurement. Since API-served models run batched, the estimated energies and the carbon figures derived from them are overstated by roughly an order of magnitude. We now say so.

The correction is also architecture-dependent, which flips a ranking: by FLOP estimate Qwen (a sparse MoE) appears more efficient than Gemma (dense); at c=1 they are level; under batching Gemma is twice as efficient. Because frontier architectures are undisclosed, this *widens* the uncertainty on their figures rather than resolving it — but the ≥50× separation the argument rests on survives the worst combination of assumptions.

> **The authors should also be more careful when moving from API price to computational efficiency, because market price is not the same as real serving cost.**

The most productive comment in the review. We replaced hand-waving with measurement.

**§3.3 and Table 3** record every provider serving each model at one instant. Open weights are offered by 4–14 independent operators spanning up to **14.4×** in list price, and differing in *numerics* (FP4, FP8, `bf16`, `fp16`). Every run now pins its provider with fallbacks disabled — which caught a concrete fault: one provider for Qwen3-Coder-30B **billed output tokens while returning empty content**, which unpinned would have been scored as a model parse failure.

We then asked whether that dispersion threatens the *quality* results. It does not. Llama-3.3-70B run on three providers in one epoch — two FP8 from different operators, one `bf16` — gives balanced accuracy 0.599–0.609, a numerics contrast of −0.003 (*p*=0.57), an operator contrast of +0.007 (*p*=0.17), and 96–97% per-item agreement. We had written serving-layer dependence into §5.3 as a threat; the measurement refutes it, and §5.3 now reports the negative result instead.

Finally, §5.1 and Table 8 give the break-even analysis with throughput **measured** rather than assumed. It refines our own headline: the small models sustain 45–64 tasks/s on one H200 and are 3–7× cheaper self-hosted, but Llama-3.3-70B sustains only 8.0 and *straddles* break-even — 1.6× cheaper on owned hardware, 1.5× **dearer** on rented. The open models' price advantage is therefore partly physical and partly a market artifact, and we now separate the two.

> **The discussion about realistic prevalence should perhaps appear earlier...**

Agreed and done — now **§4.3**, immediately after Detection Quality, expanded to precision, false positives per true positive, alert volume, and cost and energy *per true positive found*, and elevated into the abstract and conclusions.

> **English language and style.**

A light pass: longest sentences split, stacked hedges removed, comparatives made parallel. Reviewers 2 and 3 judged the language to need no improvement, so we did not change register.

---

## Reviewer 2

> **#1 ... strong efficiency advantages ... rather than a general conclusion that open-weight models dominate frontier systems on quality ... reflected consistently in the title, abstract, introduction, discussion, conclusion, figures, and captions.**

You are right, and this is now the paper's organising principle:

1. **Configuration-invariant:** open-weight models occupy the efficiency Pareto frontier; no frontier model is Pareto-optimal.
2. **Configuration-specific:** at a matched budget the best open model significantly beats all three frontier models.
3. **Parity, not dominance:** the strongest frontier system is level with the second and third open models, and reaches parity with the best under native reasoning.
4. **Not deployment-ready:** precision 2.3–8.2% at 1:44 prevalence.

**On the title we respectfully differ.** *"Open or Frontier?"* poses a question rather than asserting dominance, and changing it would break continuity with the preprint and Zenodo record. Every other surface you list now carries the distinction. We will revisit if you still consider it misleading.

> **#2 The direct-answer comparison is not fully symmetric... The abstract should not present the direct-mode result as an unqualified cross-tier comparison.**

Addressed by §4.7 (see Reviewer 1). The abstract now reads "at a matched output budget the best open model significantly exceeds every frontier model (0.711 against 0.606–0.653), although the strongest frontier system is level with the next two open models" — the qualification sits in the same sentence as the claim.

> **#3 Energy is measured directly only for two models... avoid precise claims such as a fixed 39× or 100× advantage...**

Done, and superseded by the concurrency sweep described under Reviewer 1: provenance column, sensitivity bands, new Figure 3, no fixed multipliers, and a measured demonstration that the estimator's regime is single-request rather than batched.

> **#4 ... measured cost and latency reflect gateway pricing ... A simple break-even analysis for self-hosting would materially improve practical relevance.**

Done, with measured throughput — see Reviewer 1. The three-way distinction you asked for (open-weight availability / API-served evaluation / self-hosted economics) is explicit in §3.3 and §5.1.

> **#5 ... neither is a sufficiently strong modern baseline ... include a model fine-tuned on PrimeVul training data, a stronger code-security baseline such as CodeQL ... statements such as "the strongest tools available here" should be limited to the evaluated set.**

You were right, and this became the most consequential change in the revision.

**New §4.4** adds **Semgrep** and **Cppcheck** with swept severity thresholds, and a **CodeBERT detector fine-tuned on PrimeVul's own training split**. We verified no leakage: **0 of 1549** evaluated functions, and 0 evaluated function bodies up to whitespace, occur in training.

**The fine-tuned detector outperforms every LLM we tested**: 0.765 balanced accuracy, MCC 0.526, and 8.2% precision at deployment prevalence while recovering 71% of vulnerable functions, against DeepSeek-V3.2's 0.711, 0.403 and 3.8%. A 125-million-parameter encoder exceeds the best of eight general-purpose models by more than 50% on MCC, at negligible inference cost. §4.4 and the Conclusions now state the consequence: our LLM comparison is a comparison *among LLMs*, not a search for the best available detector. The condition is data — a fine-tuned detector needs several thousand in-distribution labels; an LLM needs none.

Two methodological notes, both recorded in the paper. The threshold is selected on the **validation** split, not swept on the evaluation set (which would have reported 0.777 rather than 0.765). And our *first* attempt returned 0.500 balanced accuracy with recall exactly zero, which we nearly reported as evidence that trained detectors fare no better than LLMs. It was an artifact: under unweighted cross-entropy on a 2.77%-positive split, predicting "safe" everywhere is optimal, and no output score exceeded 0.372, so argmax could not emit a positive whatever the model had learned — while the ranking underneath was already at ROC-AUC 0.845. We report the near-miss because the failure is silent and points at exactly the wrong conclusion.

The offending phrase "the strongest tools available here" is removed.

**On CodeQL we must decline, with a reason.** Building a CodeQL database for C/C++ requires tracing an actual compilation, and PrimeVul functions are isolated snippets with no headers or build system. This is a property of the function-level task formulation, not of CodeQL, and it applies to any whole-program analyzer. We state it explicitly rather than omitting CodeQL silently; Semgrep and Cppcheck are the closest substitutes designed for unbuildable code.

**We kept CodeBERT-Devign** alongside the new detector rather than replacing it: its collapse under distribution shift is itself a finding, now labelled a cross-dataset transfer reference point rather than a competitive baseline.

> **#6 Results are based on one stratified sample... one fixed seed... Please add repeated stratified draws and, where API cost permits, repeated runs...**

Done — **§4.8**. Because PrimeVul's test split holds only 549 vulnerable functions, all of them appear in every sample and only the 1000 safe functions vary; we draw two further independent safe pools overlapping the original by under 6%. Since the positives are identical across draws, re-running them yields repeated generations of the same items under an unchanged configuration, bounding API-side non-determinism at no extra cost. Every model was also re-run under two prompt paraphrases, each altering exactly one property so that a shift is attributable.

We additionally re-ran the anchor configuration in the same epoch as the robustness runs. That mattered: several models moved by +0.03 to +0.06 balanced accuracy between July and August. The three-provider control (Reviewer 1) rules out provider and precision as the cause, so this is model-service drift — exactly the effect you asked us to quantify, and the reason families are compared only within an epoch.

> **#7 Figures 1 and 2 ... Table 2 should use a distinct marker or separate column for energy provenance ... Consider adding latency to a supplementary table.**

All three done: provenance column in Table 4, provenance encoding and sensitivity bars in Figure 2, and latency (mean, median, p95, output tokens/s) as Table A3.

> **#8 ... precision at natural 1:44 prevalence is only 2.3–3.8% ... should be elevated ... add metrics ... such as precision–recall curves, false positives per true positive, workload at fixed recall, calibration/thresholding analysis, or the benchmark's proposed scored prevalence-aware metric.**

Elevated into the abstract, the introduction, its own Results section (§4.3) and the conclusions, with false positives per true positive, alert volume, workload at achieved recall, a prevalence sweep, and cost and energy per true positive.

For the threshold-swept metrics we ran a dedicated experiment: every model re-run emitting an integer 0–100 defined in the prompt as P(vulnerable). **Most models did not follow that instruction, and the pattern of failure is our answer to this comment.** Only Claude-Sonnet-5 used the requested scale with usable resolution (34 levels, 99.7% coverage, ROC-AUC 0.814). Gemma-3-4B, GLM-5 and GPT-5.1 reported confidence *in their own verdict* instead — both verdict classes average 0.75–0.91 — recoverable to AUC 0.76 / 0.75 / 0.69 only by inferring the convention from their outputs. DeepSeek-V3.2 emitted the literal token `-1` on 1409 of 1549 tasks. Llama-3.3-70B used both conventions within one verdict class. Gemini-3.1-Pro produced a parseable pair on 1.2% of tasks.

Where usable, the number does add ranking information over the verdict (+0.005 to +0.110). What it cannot support is **VD-Score**, which PrimeVul defines at a fixed 0.5% false-positive rate: at 5–34 distinct levels the grids are too coarse. Claude-Sonnet-5's brackets the target (achievable FPRs 0.000 / 0.002 / 0.003 / 0.004); GLM-5's jumps from 0.009 to 0.028, so no threshold on its output reaches the definition. We therefore report operating points where the grid supports them and decline VD-Score where it does not, rather than interpolating a number the data does not contain. Notably, the best LLM score (0.814) still ranks below the fine-tuned detector (0.845).

> **#9 ... more detail on the common parsed sets, treatment of parse failures, confidence-interval construction, and the exact family of hypotheses ... A supplementary table containing all pairwise effects...**

Done — **Appendix A**. It documents that comparisons run on tasks *both* models parsed; that parse failures are excluded rather than recoded as "safe", and why (recoding would credit a failing model with specificity worth ~0.025 balanced accuracy at a 5% failure rate, comparable to the gaps under test); the percentile-bootstrap construction and its 5×10⁻⁵ resolution; and both hypothesis families with the complete pairwise table. All 28 pairs ship with the reproduction package.

**This audit found an error in the submitted manuscript.** §4.2 reported Holm-adjusted *p* = 7×10⁻⁴ for DeepSeek-V3.2 against Gemini-3.1-Pro. Two independently written scripts agree that no resample of the 20,000 reverses the sign of that gap, so the correct statement is a bound: raw *p* below the bootstrap's 5×10⁻⁵ resolution and adjusted *p* below 5×10⁻⁴, for all three frontier comparisons. The conclusion is unchanged and slightly stronger; the figure was wrong and is corrected.

---

## Reviewer 3

> **#1 The related-work section should be further strengthened... The claim of being the "first" should also be stated more cautiously.**

Agreed. §2.3 is rewritten: the phrase is gone, replaced by a scoped statement supported by **Table 1**, which places this paper against the closest prior work on security task / cost reported / energy reported / open-weight roster size. We added Lira et al. (arXiv:2604.08417), the closest cost-aware work we found; it reports cost but not energy, on four proprietary models with no open-weight roster. We state plainly: "We make no claim to be first on any single one of these axes."

> **#2 The energy analysis for proprietary models relies heavily on assumed active parameter counts... broader sensitivity analyses and more cautious interpretation are needed.**

Agreed, and taken further than sensitivity analysis alone. All frontier energy figures are now ranges, new Figure 3 sweeps the assumption across 25B–400B, and the concurrency sweep (§4.6) establishes empirically that the estimator matches single-request rather than batched serving — so the estimates are systematically high, by an architecture-dependent factor we cannot resolve for undisclosed frontier architectures. This widens the stated uncertainty rather than narrowing it. The claim we rely on is the weaker one: the separation exceeds the plausible range of the assumption.

> **#3 More methodological details ... exact prompts, output constraints, parsing rules, model versions, inference parameters, and retry procedures.**

Done — **Appendix B** covers every item: verbatim prompt templates, the parser's six precedence rules, gateway identifiers with pinned providers and served precision, decoding parameters, truncation, and retry policy.

Your question exposed a real gap: the harness had **no retry logic**, so a transient rate limit was indistinguishable from a model that could not answer and silently depressed parse rates. We implemented bounded exponential backoff with jitter (four attempts; 408/429/5xx and timeouts retried, other 4xx not), and every result row now records the attempts spent. Thank you — this would have biased the robustness runs.

> **#4 The study evaluates only one stratified subset... Repeated sampling with different random seeds, or preferably evaluation on the complete test set...**

Repeated sampling is done (§4.8; see Reviewer 2 #6).

**On the complete test set we would push back, and defer to you.** All 24,788 functions across eight models costs roughly $275 and would only narrow intervals that already separate the models we claim to separate; stratification preserves the class ratio, and the prevalence analysis is computed at the natural 1:44 rate regardless. Repeated draws address the underlying concern — sampling variability — at a twentieth of the cost. If you consider the full-split evaluation necessary rather than preferable, we will run it.

> **#5 The current non-LLM baselines are relatively limited... a stronger learned detector trained on PrimeVul and a widely used semantic/static-analysis tool, such as LineVul and CodeQL.**

Addressed under Reviewer 2 #5 — and your suspicion was correct: the LineVul-recipe detector trained on PrimeVul outperforms every LLM in our roster. CodeQL cannot be applied to unbuildable snippets, with the reason stated in the paper; Semgrep and Cppcheck replace it.

> **#6 The comparison ... is not fully symmetric because different reasoning modes and output-token budgets are used ... budget-controlled and native/recommended inference settings should be evaluated and reported separately.**

Done — §4.7, exactly as you and Reviewer 1 describe, including the direct measurement that the output budget changes balanced accuracy by ≤0.004 for every model that can comply with it.

---

## A note on what changed our conclusions

Three of the reviewers' requests overturned claims we had made, and the paper is substantially more useful for it: the learned baseline was a strawman and its replacement beats the LLMs; the energy estimator measures the wrong serving regime; and one *p*-value and one precision figure were simply wrong. We are grateful for the scrutiny.
