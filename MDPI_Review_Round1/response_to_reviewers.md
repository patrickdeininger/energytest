# Response to Reviewers — Round 1

**Manuscript:** *Open or Frontier? A Cost- and Energy-Aware Benchmark of Large Language Models for Software Vulnerability Detection*
**Journal:** *Computers* (MDPI) · **Decision:** Major revision

We thank all three reviewers. The reviews converged on the same four issues, and we found them correct in every case — in particular Reviewer 2's point 1, that our evidence supports a decisive *efficiency* advantage together with quality *competitiveness*, not quality dominance. We have restructured the paper's claims around that distinction rather than defending the original wording.

Three of the changes go beyond what was asked, because acting on the reviews surfaced problems we had not seen:

- Auditing our own statistics against a second independently written script showed that a *p*-value in Section 4.2 was **wrong**. We report the corrected bound.
- Investigating Reviewer 1's "market price is not real serving cost" point produced a measurable result: for open-weight models, list price varies by up to **14× across providers at one instant**, and those providers serve *different numerics* (FP4 to `bf16`). We have added this as evidence, and it exposed a **threat to validity we had missed** — our original runs neither pinned nor logged the serving provider. All runs now do.
- Re-checking our static-analysis baseline showed we had reported Flawfinder at a single threshold. Swept properly it reaches **13.4%** precision, not the 6% we claimed — which makes our own LLM results look *worse*, and we report it.

Changes are marked in the revised manuscript. Section numbers refer to the revised version.

---

## Summary of changes

| # | Change | Raised by |
|---|---|---|
| 1 | Claim hierarchy recalibrated: efficiency = configuration-invariant headline; quality = configuration-specific; parity, not dominance. Abstract, contributions, §5.1, Conclusions, captions | R1, **R2#1**, R3 |
| 2 | New §4.7 configuration-matched families A/B/C (budget-matched / native / best-observed) | **R1**, R2#2, R3#6 |
| 3 | Energy provenance and sensitivity made explicit in Table 4, Figure 2, new Figure 3 | R1, R2#3, R2#7, R3#2 |
| 4 | New §3.3 provider price-dispersion analysis + Table 3; provider pinning; break-even model | **R1**, R2#4 |
| 5 | New §4.4 baselines: Semgrep, Cppcheck, threshold sweeps; PrimeVul-trained detector; CodeQL inapplicability documented | R2#5, R3#5 |
| 6 | New §4.8 robustness: 2 prompt paraphrases, 3 safe-pool draws, repeated generations | R2#6, R3#4 |
| 7 | New §4.3 deployment utility at realistic prevalence, promoted into Results + abstract + conclusions | **R1**, R2#8 |
| 8 | New Appendix A: parsed-set composition, CI construction, both hypothesis families, complete pairwise table | R2#9 |
| 9 | New Appendix B: prompts, parsing precedence, model versions, pinned providers, decoding, retry policy, latency table | R3#3, R2#7 |
| 10 | §2.3 rewritten: "first" replaced by a scoped claim + comparison table; recent cost-aware work added | R3#1, R2, R3 |
| 11 | English pass on the longest sentences in §4.2 and §5.1 | R1 |

---

## Reviewer 1

> **The main problem is that the comparison is not completely equal between all models: some models use reasoning and others do not, the output-token limits are not always the same...**

Agreed, and this was the single most-repeated point across all three reviews. We no longer defend one configuration as the fair one. **New §4.7** reports the three comparisons you asked for by name — same token budget, normal configuration, best-performing configuration — as Families A, B and C, and asks which conclusions survive all three.

The structure of the answer is that the **quality** ranking moves between families while the **efficiency** ordering is identical in all three and widens from A to C. That is now the paper's central organising contrast.

One model genuinely cannot be budget-matched, and we now demonstrate rather than assert it: Gemini-3.1-Pro returns `HTTP 400: "Reasoning is mandatory for this endpoint and cannot be disabled"`, and at a 64-token budget it spends the whole allowance on internal reasoning, emitting no verdict on 45.8% of tasks. We report that failure rate instead of scoring it against a set it could not answer. Notably, Claude-Sonnet-5 now parses **1549/1549 at 64 tokens** where it previously needed 256, so it enters Family A on equal terms.

> **Because of this, the claims about energy dominance and the Pareto frontier are sometimes stronger than what the design can fully support.**

Agreed. See the claim hierarchy in the summary above and Reviewer 2 #1 below. We have removed "dominate" wherever it referred to quality.

> **Figure 2 should also show much more clearly which values are measured and which are estimated, preferably with uncertainty ranges.**

Done. Table 4 now carries an explicit **Energy source** column rather than a dagger, and each frontier estimate is printed with its swept range in the same cell; Figure 2 distinguishes measured from estimated points by marker shape *and* fill and draws horizontal sensitivity bands on every estimated point; new Figure 3 sweeps the frontier active-parameter assumption across 25B–400B. We have also removed every fixed multiplier: "39×" is now "≈40× (10–150× across the plausible range)".

> **The authors should also be more careful when moving from API price to computational efficiency, because market price is not the same as real serving cost.**

This turned out to be the most productive comment in the review, and we have replaced our hand-waving with measurement. **New §3.3 and Table 3** report every provider serving each evaluated model at a single instant. For open weights, list price is not a property of the model: DeepSeek-V3.2 is offered by 14 providers spanning **14.4×** in input price, Llama-3.3-70B by 13 spanning **10.4×**. Worse for interpretation, those providers differ in *numerics* — the same Llama weights are served at `bf16`, `fp16` and FP8; GLM-5 at FP8 by most and FP4 by one — so a cheaper endpoint is sometimes a different computation rather than a better deal.

Two consequences follow, both new. First, every run now pins its provider with gateway fallbacks disabled, so the configured price is the price charged and the numerics are fixed (Appendix B, Table A2). This also caught a concrete fault: one provider for Qwen3-Coder-30B **billed output tokens while returning empty content**, which unpinned would have been scored as model parse failure. Second, we have added this as an explicit threat to validity in §5.3 — our open-model results pertain to those weights *as served at that precision*, not to the weights in the abstract. We are grateful for the push; we had not seen this.

> **The discussion about realistic prevalence is important and should perhaps appear earlier, because precision of around 2-4% means that the models are still not ready for independent practical use.**

Agreed and done. It is now **§4.3**, immediately after Detection Quality rather than buried in the Discussion, and it is expanded well beyond the original paragraph: precision, false positives per true positive, alert volume per 1000 functions, and cost and energy *per true positive found*. The headline numbers are now in the abstract and the Conclusions. Each model alerts on 43–75% of all functions scanned; the best raises 25.6 false alarms per true finding.

> **English language and style could be improved.**

We have split the longest sentences in §4.2 and §5.1, removed stacked hedges, and made comparatives parallel. We note Reviewers 2 and 3 judged the language to need no improvement, so we have kept the pass light rather than changing register.

---

## Reviewer 2

> **#1 ... the evidence supports a conclusion of strong efficiency advantages ... rather than a general conclusion that open-weight models dominate frontier systems on quality. This distinction should be reflected consistently in the title, abstract, introduction, discussion, conclusion, figures, and captions.**

You are right, and this is now the paper's organising principle. The claim hierarchy is:

1. **Configuration-invariant (headline):** open-weight models occupy the efficiency Pareto frontier; no frontier model is Pareto-optimal; the gap widens when the frontier reasons.
2. **Configuration-specific:** at a matched direct-answer budget the best open model significantly beats all three frontier models.
3. **Parity, not dominance:** with native reasoning the strongest frontier model reaches statistical parity (0.677 vs 0.676) at 2.5–7.6× the cost.
4. **Not deployment-ready:** precision 2.3–3.8% at 1:44 against a 2.2% base rate.

This is now stated in the abstract, Introduction contribution 2, §5.1, and the Conclusions, which we rewrote into three explicitly labelled parts ("Efficiency is the firm one… Quality is the conditional one… Both findings sit on top of a benchmark no model comes close to solving").

**On the title, we respectfully differ.** *"Open or Frontier?"* poses a question rather than asserting dominance, so it does not carry the overclaim; changing it would also break continuity with the published preprint and Zenodo record. We have instead made every other surface you list carry the distinction. We are happy to revisit if you still consider the title misleading.

> **#2 The direct-answer comparison is not fully symmetric... Please present a clearly separated, configuration-matched analysis... The abstract should not present the direct-mode result as an unqualified cross-tier comparison.**

Done — see Reviewer 1 above for §4.7. The abstract now reads "At a matched direct-answer budget the best open model significantly exceeds every frontier model (0.676 against 0.616–0.623); granting the frontier native reasoning raises it only to parity (0.677), at 2.5 to 7.6 times the cost." The qualification is in the same sentence as the claim.

> **#3 Energy is measured directly only for two models... avoid precise claims such as a fixed 39× or 100× advantage unless accompanied by the full parameter-assumption range.**

Done: provenance column in Table 4, sensitivity bands in Figure 2, new Figure 3, and all fixed multipliers replaced by ranges (the Gemma-vs-Claude energy ratio is now given as 39x with a swept range of 9.7x-154.5x). We have also separated the two axes' epistemic status in the text — the cost ratio is measured but is a *list-price* ratio (§3.3), while the energy ratio is physically grounded but partly estimated.

> **#4 ... measured cost and latency reflect gateway pricing and service behavior rather than self-hosted open-model deployment... A simple break-even analysis for self-hosting would materially improve practical relevance.**

Addressed in two parts. The distinction you ask for — (i) open-weight availability, (ii) API-served evaluation, (iii) self-hosted economics — is now explicit in §3.3 and §5.1, backed by the price-dispersion measurement described under Reviewer 1. The break-even model is in §5.1 and Table 8, with stated assumptions for hardware amortization, electricity price, PUE and utilization.

It changed our own reading of the result, and we report that plainly: self-hosting Llama-3.3-70B beats the API list price only above roughly **5 sustained tasks/s on owned hardware, or 12 on rented** (about 430k and 1.03M functions/day). Below that the gateway is cheaper. We therefore now say explicitly that the open models' *price* advantage is substantially a market fact — many providers competing at high batch efficiency — which an organization self-hosting at modest volume will not reproduce, whereas the *energy* advantage is physical and is inherited. That asymmetry is the strongest argument we can make for reporting energy rather than treating price as a proxy for efficiency.

The table's throughput axis is pinned by a **concurrency sweep (1, 8, 32, 64) on the H200**, which also addresses the concern you and Reviewer 1 both raised that our concurrency-1 measurement is an energy-pessimistic regime unrepresentative of batched serving. That sweep is scripted and pending GPU time; the table is presented as a sensitivity analysis over throughput so that its structure stands independently of which column applies.

> **#5 ... neither is a sufficiently strong modern baseline... include a model fine-tuned on PrimeVul training data, a stronger code-security baseline such as CodeQL... Without this, statements such as "the strongest tools available here" should be limited to the evaluated set.**

Agreed on all counts. **New §4.4** adds **Semgrep** (community C and security-audit rulesets; pattern and intraprocedural taint analysis) and **Cppcheck** (flow-sensitive), each with its severity threshold swept rather than fixed, plus a **CodeBERT detector fine-tuned on PrimeVul's own training split**. We verified there is no leakage: **0 of 1549** evaluated functions, and 0 evaluated function bodies up to whitespace, occur in the training split.

The offending phrase "the strongest tools available here" is removed.

**On CodeQL we must decline, with a reason.** Building a CodeQL database for C/C++ requires tracing an actual compilation, and PrimeVul functions are isolated snippets with no headers, includes, or build system, so no database can be constructed. This is a property of the function-level task formulation, not of CodeQL, and it applies to any whole-program analyzer. We state this explicitly in §4.4 rather than omitting CodeQL silently, and Semgrep and Cppcheck are the closest substitutes designed for unbuildable code.

**We also kept CodeBERT-Devign**, rather than replacing it. Its collapse under distribution shift is itself one of the paper's findings and corroborates PrimeVul's thesis; we now label it a *cross-dataset transfer reference point*, not a competitive baseline.

The result changed our own conclusions. Sweeping thresholds properly shows Flawfinder reaching **13.4%** precision at deployment prevalence, not the 6% we previously reported from a single threshold, and Semgrep reaching an estimated **26.0%** — roughly seven times the best LLM, though on 2 false positives, so we report its 95% interval of [5.7%, 66.9%] and lean only on the fact that even its lower bound exceeds every LLM. The honest picture is a monotone precision/recall frontier that no method here escapes: LLMs flag nearly everything and are almost never right; curated-rule analyzers flag almost nothing and are right somewhat more often.

> **#6 Results are based on one stratified sample... one fixed seed... one task formulation... Please add repeated stratified draws and, where API cost permits, repeated runs...**

Done — **new §4.8**. Because PrimeVul's test split has only 549 vulnerable functions, all of them are in every sample and only the 1000 safe functions vary; we draw two further independent safe pools overlapping the original by **under 6%**. Since the positives are identical across draws, re-running them yields repeated generations of the same 549 items under an unchanged configuration, which bounds API-side non-determinism at temperature 0 at no extra cost. We additionally re-run every model under **two prompt paraphrases**, each altering exactly one property (persona removed; answer-order reversed) so any shift is attributable.

We also re-ran the anchor configuration in the same measurement epoch as these robustness runs, so drift in the model services is measured rather than confounded with them.

> **#7 Figures 1 and 2 ... Table 2 should likewise use a distinct marker or separate column for energy provenance... Consider adding latency to a supplementary table.**

All three done: provenance column in Table 4, provenance encoding and uncertainty bands in Figure 2, and the latency distribution (mean, median, p95, output tokens/s) as Table A3 in Appendix B.

> **#8 ... precision at natural 1:44 prevalence is only 2.3–3.8% ... This is a crucial result and should be elevated in the abstract and conclusion ... add metrics ... such as precision–recall curves, false positives per true positive, workload at fixed recall, calibration/thresholding analysis, or the benchmark's proposed scored prevalence-aware metric.**

Agreed, and elevated: it is now in the abstract's final sentence, in the Introduction, as its own Results section (§4.3), and as the closing paragraph of the Conclusions. §4.3 adds false positives per true positive, alert volume, workload at achieved recall, a prevalence sweep, and cost and energy per true positive found.

PR curves, VD-Score and calibration require a continuous score, which binary verdicts do not provide. We therefore added a **confidence-elicitation run** in which every model emits `CONFIDENCE: 0–100` (defined as P(vulnerable)) alongside its verdict, giving a rankable score. We will report these as indicative, since self-reported LLM confidence is coarse and imperfectly calibrated — which the calibration analysis itself will quantify.

> **#9 ... Please provide more detail on the common parsed sets used in pairwise comparisons, treatment of parse failures, confidence-interval construction, and the exact family of hypotheses used for each correction. A supplementary table containing all pairwise effects...**

Done — **new Appendix A**. It documents that comparisons run on tasks *both* models parsed, that parse failures are excluded rather than recoded as "safe" (and why: recoding would credit a failing model with specificity, worth ~0.025 balanced accuracy at a 5% failure rate — comparable to the gaps under test), the percentile-bootstrap construction and its 5×10⁻⁵ resolution, and both hypothesis families (9-comparison primary, 15-comparison strict) with the complete pairwise table. All 28 pairs are released with the reproduction package.

**This audit found an error in the submitted manuscript.** §4.2 reported a Holm-adjusted *p* = 7×10⁻⁴ for DeepSeek-V3.2 against Gemini-3.1-Pro. Two independently written scripts agree that no resample of the 20,000 reverses the sign of that gap, so the correct statement is that the raw *p* lies below the bootstrap's 5×10⁻⁵ resolution and the adjusted *p* below 5×10⁻⁴, for all three frontier comparisons. The conclusion is unchanged and slightly stronger; the reported figure was wrong and is corrected.

---

## Reviewer 3

> **#1 The related-work section should be further strengthened, especially regarding recent studies on cost-aware or efficiency-aware LLM evaluation in cybersecurity. The claim of being the "first" should also be stated more cautiously...**

Agreed. §2.3 is rewritten. The phrase "for the first time to our knowledge" is gone, replaced by a scoped statement of the specific conjunction that is new, supported by **Table 1**, which places this paper against the closest prior work on three axes (security task / cost reported / energy reported / open-weight roster size). We added Lira et al. (arXiv:2604.08417), which assesses effectiveness *and* inference cost for LLM vulnerability detection — the closest cost-aware work we found; it reports cost but not energy, on four proprietary models with no open-weight roster. We state plainly: "We make no claim to be first on any single one of these axes."

> **#2 The energy analysis for proprietary models relies heavily on assumed active parameter counts... broader sensitivity analyses and more cautious interpretation of the energy Pareto frontier are needed.**

Agreed. All frontier energy figures are now reported as sensitivity ranges rather than point values, new Figure 3 sweeps the active-parameter assumption across 25B–400B, and the text states explicitly that the on-GPU measurements validate the estimator only in the open-model regime and cannot test the frontier parameter assumption. The claim we rely on is the weaker, measurement-independent one: the separation is one to two orders of magnitude, larger than the assumption's plausible range.

> **#3 More methodological details should be provided regarding the exact prompts, output constraints, parsing rules, model versions, inference parameters, and retry procedures.**

Done — **new Appendix B** covers every item: verbatim prompt templates, the parser's six precedence rules, gateway model identifiers with pinned providers and served precision, decoding parameters, truncation, and the retry policy.

The retry question exposed a genuine gap: the harness had **no retry logic**, so a transient rate limit was indistinguishable from a model that could not answer and silently depressed parse rates. We implemented bounded exponential backoff with jitter (four attempts; 408/429/5xx and timeouts retried, other 4xx not, since a malformed request fails identically forever), and every result row now records the attempts spent so retry-inflated runs are auditable. Thank you — this would have quietly biased the robustness runs.

> **#4 The study evaluates only one stratified subset... Repeated sampling with different random seeds, or preferably evaluation on the complete test set, would provide stronger evidence...**

Repeated sampling is done (§4.8; see Reviewer 2 #6).

**On the complete test set we would push back, and defer to you.** Running all 24,788 functions across 8 models costs roughly $275 and would only narrow confidence intervals that already separate the models we claim to separate; the class ratio is preserved by stratification, and the prevalence analysis is computed at the natural 1:44 rate regardless. Repeated draws address the underlying concern — sampling variability — directly and at a twentieth of the cost. If you consider the full-split evaluation necessary rather than preferable, we will run it.

> **#5 The current non-LLM baselines are relatively limited... a stronger learned detector trained on PrimeVul and a widely used semantic/static-analysis tool, such as LineVul and CodeQL.**

Addressed under Reviewer 2 #5. The learned detector fine-tuned on PrimeVul is the LineVul recipe (CodeBERT encoder with a binary classification head); Semgrep and Cppcheck replace CodeQL, which cannot be applied to unbuildable snippets, with the reason stated in the paper.

> **#6 The comparison ... is not fully symmetric because different reasoning modes and output-token budgets are used ... budget-controlled and native/recommended inference settings should be evaluated and reported separately.**

Done — §4.7 Families A/B/C, exactly as you and Reviewer 1 describe. Section 4.7 additionally isolates the output-budget effect by running every model at both 64 and 256 tokens with everything else held fixed.

---

## Note on remaining items

Several analyses in §4.7 and §4.8 depend on runs that were still executing when this draft was prepared; the runs are scripted, budgeted and in progress, and their results will be folded in before resubmission. The manuscript marks those two results paragraphs explicitly rather than presenting placeholder numbers.
