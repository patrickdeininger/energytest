# Response to Reviewer 2

**Manuscript:** *Open or Frontier? A Cost- and Energy-Aware Benchmark of Large Language Models for Software Vulnerability Detection*

Thank you for a review that was unusually precise about what the evidence did and did not support. Your point 1 states the corrected claim better than we had, and it became the organising principle of the revision. Your point 5 turned out to change the paper's scope. Section numbers refer to the revised manuscript.

One framing note before the detail. The efficiency result you identified as well supported survived every test the reviews prompted — three prompts, three sample draws, two budgets, all reasoning configurations, two epochs and three serving providers. The quality result did not survive as stated, and the revision narrows it in the direction you indicated, further than you asked.

---

## #1 Efficiency advantage versus quality dominance

> *"The evidence supports a conclusion of strong efficiency advantages for the tested open-weight models and direct-mode quality advantages for specific models/configurations, rather than a general conclusion that open-weight models dominate frontier systems on quality. This distinction should be reflected consistently in the title, abstract, introduction, discussion, conclusion, figures, and captions."*

You are right, and this is now the paper's organising principle. The claim hierarchy is stated explicitly and consistently:

1. **Configuration-invariant (headline):** open-weight models occupy the efficiency Pareto frontier; no frontier model is Pareto-optimal.
2. **Configuration-specific:** at a matched output budget the best open model significantly beats all three frontier models.
3. **Parity, not dominance:** the strongest frontier system is level with the best open model at each model's best configuration (+0.025, *p* = 0.081), and level with the *second and third* open models under budget matching.
4. **Not deployment-ready:** precision 2.3–8.2% at natural prevalence.

This now appears in the abstract, Introduction contribution 2, Section 5.1, the Conclusions (restructured into three explicitly labelled parts), and the affected captions. "Dominate" no longer appears in reference to quality.

Subsequent work made the distinction sharper than we could have stated at submission: Section 4.8 shows the quality ranking is *prompt-dependent* — three reasonable phrasings produce three different winners — while the efficiency ordering is identical under all of them. Your instinct was correct beyond the evidence then available.

**On the title we respectfully differ.** *"Open or Frontier?"* poses a question rather than asserting dominance, so we do not believe it carries the overclaim; changing it would also break continuity with the preprint and the Zenodo record. We have made the change on every other surface you list. If the editors disagree we will change it without objection.

---

## #2 Asymmetric direct-answer comparison

> *"...Gemini-3.1-Pro has no direct/non-reasoning mode, while Claude-Sonnet-5 and GPT-5.1 are run with reasoning disabled; output budgets also differ... Please present a clearly separated, configuration-matched analysis... The abstract should not present the direct-mode result as an unqualified cross-tier comparison."*

**New Section 4.7** presents three configuration-matched families — budget-matched direct (A), native (B) and best-observed (C) — all computed in a single measurement epoch with providers pinned.

We also ran the budget-sensitivity analysis you asked for (Table 7): every model at both 64 and 256 output tokens, everything else fixed. **Seven of eight models move by ≤0.004 balanced accuracy, none significantly** (*p* ≥ 0.34). Gemini-3.1-Pro is the exception at +0.061, and its parse rate accounts for it (0.542 → 0.991) — the gain is a parsing effect rather than a reasoning-quality one. Gemini rejects any request to disable reasoning (`HTTP 400`), so it cannot be budget-matched at all; we report its failure rate rather than scoring it against a set it did not answer.

The abstract now reads: *"at a matched output budget the best open model significantly exceeds every frontier model (0.711 balanced accuracy against 0.606–0.653), although the strongest frontier system is level with the next two open models."* The qualification sits in the same sentence as the claim.

---

## #3 Energy measured for only two models; avoid fixed multipliers

> *"...figures and table presentation may still invite readers to interpret estimated values as directly measured per-model energy... avoid precise claims such as a fixed 39× or 100× advantage unless accompanied by the full parameter-assumption range."*

Table 4 now carries an explicit **Energy source** column with each frontier estimate's sensitivity range printed inline. Figure 2 distinguishes measured from estimated by marker shape *and* fill, with horizontal uncertainty bars. **New Figure 3** sweeps the active-parameter assumption across 25B–400B. No fixed multiplier survives.

Acting on this produced a result we did not anticipate. We re-measured all three locally servable open models across a concurrency sweep (new Section 4.6, Table 5). The concurrency-1 figures **replicate** across pods seven weeks apart (Llama 1.00×, Qwen 0.95×). But **the FLOP estimator describes single-request serving, not the batched serving it was calibrated for**: within 2× of the concurrency-1 measurement, yet 5.4–16.9× *above* the concurrency-64 measurement. Since API-served models run batched, the estimated energies and the carbon figures derived from them are overstated by roughly an order of magnitude, and the manuscript now says so.

The correction is architecture-dependent — dense models 12.7–16.9×, the sparse MoE 5.4× — which flips the Gemma/Qwen energy ranking between regimes. Because frontier architectures are undisclosed we cannot resolve which factor applies to them, so this *widens* the uncertainty on those figures rather than narrowing it. What survives is the comparison the argument rests on: even under the least favourable combination of assumptions the separation exceeds fiftyfold.

---

## #4 Gateway pricing versus self-hosted economics

> *"...the practical implications for on-premises security tooling should be more cautiously framed. Please distinguish: (i) open-weight availability, (ii) API-served evaluation, and (iii) actual self-hosted deployment economics... A simple break-even analysis for self-hosting would materially improve practical relevance."*

All three are now distinguished explicitly in Sections 3.3 and 5.1.

**Section 3.3 and Table 3** measure the dispersion: open weights are served by 4–14 independent operators spanning up to 14.4× in list price and differing in numerics (FP4 through `bf16`). Every run now pins its provider with fallbacks disabled.

**Section 5.1 and Table 10** give the break-even analysis with throughput **measured** on an H200 rather than assumed. It refines our own headline rather than confirming it: the small models sustain 45–64 tasks/s and are three to seven times cheaper self-hosted, but Llama-3.3-70B sustains only 8.0 and *straddles* break-even — 1.6× cheaper on owned hardware, 1.5× **dearer** on rented. So an organisation with its own hardware should self-host any of these models; one renting by the hour should self-host the small ones and buy the 70B from an API. The open models' price advantage is therefore partly physical and partly a market artifact, and we now separate the two rather than claiming both.

---

## #5 Baselines are not sufficiently strong

> *"The inclusion of Flawfinder and cross-dataset CodeBERT-Devign is useful, but neither is a sufficiently strong modern baseline... include a model fine-tuned on PrimeVul training data, a stronger code-security baseline such as CodeQL... Without this, statements such as 'the strongest tools available here' should be limited to the evaluated set."*

You were right, and this became the most consequential change in the revision.

**New Section 4.4** adds **Semgrep** (community C and security-audit rulesets, pattern and intraprocedural taint analysis) and **Cppcheck** (flow-sensitive), each with its severity threshold swept rather than fixed, plus a **CodeBERT detector fine-tuned on PrimeVul's own training split** — the LineVul recipe. We verified there is no leakage: **0 of 1549** evaluated functions, and 0 evaluated function bodies up to whitespace, occur in the training split.

**That detector outperforms every LLM we evaluated**: 0.765 balanced accuracy, MCC 0.526, and 8.2% precision at deployment prevalence while recovering 71% of vulnerable functions — against DeepSeek-V3.2's 0.711, 0.403 and 3.8%. A 125-million-parameter encoder exceeds the best of eight general-purpose models by more than 50% on MCC, at negligible cost. Section 4.4 and the Conclusions now state the consequence plainly: our LLM comparison is a comparison *among LLMs*, not a search for the best available detector. The condition is data — a fine-tuned detector needs several thousand in-distribution labels; an LLM needs none.

Two methodological notes, both recorded in the paper. The threshold is selected on the **validation** split, not swept on the evaluation set — which would have reported 0.777 rather than 0.765, an oracle figure describing the best a threshold could have achieved rather than what the detector achieves. And our *first* attempt at this baseline returned 0.500 balanced accuracy with recall exactly zero, which we came close to reporting as evidence that trained detectors fare no better than LLMs. It was an artifact: under unweighted cross-entropy on a 2.77%-positive split, predicting "safe" everywhere is optimal, and no output score exceeded 0.372, so an argmax rule could not emit a positive whatever the model had learned — while the ranking underneath was already at ROC-AUC 0.845. We report the near-miss because the failure is silent, produces a plausible number, and would have supported precisely the wrong conclusion.

The phrase *"the strongest tools available here"* is removed.

**On CodeQL we must decline, with a reason.** Building a CodeQL database for C/C++ requires tracing an actual compilation, and PrimeVul functions are isolated snippets with no headers, includes or build system, so no database can be constructed. This is a property of the function-level task formulation rather than of CodeQL, and it applies to any whole-program analyzer. We state this explicitly in Section 4.4 rather than omitting CodeQL silently; Semgrep and Cppcheck are the closest substitutes designed for unbuildable code.

**We kept CodeBERT-Devign** alongside the new detector rather than replacing it: its collapse under distribution shift is itself one of the paper's findings and corroborates PrimeVul's thesis. It is now labelled a cross-dataset transfer reference point, not a competitive baseline.

Sweeping thresholds properly also corrected a figure of our own: Flawfinder reaches **13.4%** precision at deployment prevalence, not the 6% we previously reported from a single threshold — which makes our LLM results look worse, and is reported as such.

---

## #6 One sample, one seed, one prompt

> *"The paired bootstrap quantifies within-sample uncertainty but not variation due to safe-function sampling, repeated API calls, model-service drift, or prompt sensitivity. Please add repeated stratified draws and, where API cost permits, repeated runs... At minimum, report whether conclusions are stable under multiple safe-negative samples and alternate prompt templates."*

**New Section 4.8** addresses all four sources you name, and they turn out to differ by an order of magnitude.

**Safe-function sampling — negligible.** Because PrimeVul's test split holds only 549 vulnerable functions, all of them appear in every sample and only the 1000 safe functions vary; we drew two further pools overlapping the original by under 6%. The rank ordering is *identical* across all three draws (Spearman 1.000 against the anchor for both) and no model moves by more than 0.015. Your concern was well founded and the answer is that a single stratified draw was adequate — which is also what the paired bootstrap predicted, so the two methods corroborate each other.

**Repeated API calls — small but non-zero.** Since the positives are identical across draws, re-running them measures generation variance directly at temperature 0. Per-item verdict agreement ranges from 88.3% (Qwen3-Coder-30B) to 100% (Gemma-3-4B), so up to twelve verdicts in a hundred flip on a repeat call that should be deterministic. Aggregate recall moves by at most 0.036. We report this because "temperature 0" is routinely treated as a reproducibility guarantee and for API-served models it is not one.

**Prompt sensitivity — large, and it changes the answer.** Paraphrasing moves results by up to **0.088** balanced accuracy, five to six times the draw effect, and reorders the top of the table. DeepSeek-V3.2 leads under the anchor phrasing (0.711); removing the expert persona puts Claude-Sonnet-5 first (0.741) with DeepSeek down at 0.638; reversing the order the two answers are offered in puts GLM-5 first (0.700). **Three reasonable phrasings, three different winners.** Rank correlation with the anchor is 0.381 and 0.810. Averaged over the three, Claude-Sonnet-5 (0.689) and GLM-5 (0.688) are level, with DeepSeek third (0.668). Models also differ markedly in *stability* — GLM-5 varies by 0.031 across phrasings, Claude by 0.088 — which a single-prompt evaluation cannot see at all. This is now stated as the sharpest limitation on the quality claims, applying to the literature as much as to us.

**Model-service drift — real, and the reason we re-ran the anchor.** Re-running the anchor configuration seven weeks later moved several models by +0.03 to +0.06 balanced accuracy. A three-provider control on identical weights rules out provider and precision (effects below 0.01), so this is service drift. It is why every family in Section 4.7 is computed within one epoch, and why Section 4.9 now reports the earlier epoch as a *replication* — two epochs agree on every sign and both significance patterns while absolute values differ by up to 0.06.

---

## #7 Figure and table presentation; latency

> *"Figure 2 should visually encode measured versus estimated energy points and uncertainty ranges. Table 2 should likewise use a distinct marker or separate column for energy provenance... Consider adding latency to a supplementary table."*

All three done: an **Energy source** column in Table 4 replacing the dagger, provenance encoding plus uncertainty bars in Figure 2, and latency (mean, median, p95, output tokens/s) as **Table A3** in Appendix B, with the standing caveat that those figures were collected under concurrent load.

---

## #8 Elevate prevalence; add threshold-swept metrics

> *"...precision at natural 1:44 prevalence is only 2.3–3.8% for all LLMs... This is a crucial result and should be elevated in the abstract and conclusion... add metrics and analyses that better reflect deployment utility, such as precision–recall curves, false positives per true positive, workload at fixed recall, calibration/thresholding analysis, or the benchmark's proposed scored prevalence-aware metric."*

Elevated into the abstract, the Introduction, its own Results section (**4.3**) and the Conclusions, with false positives per true positive, alert volume, workload at achieved recall, a prevalence sweep, and cost and energy per true positive found.

For the threshold-swept metrics we ran a dedicated experiment: every model re-run emitting an integer 0–100 defined in the prompt as P(vulnerable). **Most models did not follow that instruction, and the pattern of failure is our answer to this comment** (Table 6). Only Claude-Sonnet-5 used the requested scale with usable resolution — 34 distinct levels over 99.7% of tasks, ROC-AUC 0.814. Gemma-3-4B, GLM-5 and GPT-5.1 reported confidence *in their own verdict* instead, recoverable to AUC 0.76/0.75/0.69 only by inferring the convention from their outputs. DeepSeek-V3.2 emitted the literal token `-1` on 1409 of 1549 tasks. Llama-3.3-70B used both conventions within one verdict class. Gemini-3.1-Pro produced a parseable pair on 1.2% of tasks. We infer each model's convention from its own outputs rather than from which reading scores better, since selecting the reading by result would fit the metric to the data.

Where usable, the elicited number does add ranking information over the verdict (+0.005 to +0.110). What it cannot support is **VD-Score**, which PrimeVul defines at a fixed 0.5% false-positive rate: at 5–34 distinct levels the grids are too coarse. Claude-Sonnet-5's brackets the target (achievable FPRs 0.000/0.002/0.003/0.004); GLM-5's jumps from 0.009 to 0.028, so no threshold on its output reaches the definition. We therefore report operating points where the grid supports them and decline VD-Score where it does not, rather than interpolating a number the data does not contain.

Two results from this bear on your other points. The best LLM score (0.814) still ranks below the fine-tuned detector (0.845). And at every threshold a classical static analyzer is more precise than any LLM.

---

## #9 Statistical transparency

> *"Please provide more detail on the common parsed sets used in pairwise comparisons, treatment of parse failures, confidence-interval construction, and the exact family of hypotheses used for each correction. A supplementary table containing all pairwise effects, confidence intervals, raw p-values, and corrected p-values would improve transparency."*

**New Appendix A** documents each item: that comparisons run on tasks *both* models parsed; that parse failures are excluded rather than recoded as "safe", and why (recoding would credit a failing model with specificity worth roughly 0.025 balanced accuracy at a 5% failure rate — comparable to the gaps under test); the percentile-bootstrap construction and its 5×10⁻⁵ resolution; and both hypothesis families, the 9-comparison primary and the 15-comparison strict check, with the complete pairwise table (Table A1). All 28 model pairs ship with the reproduction package.

**This audit found an error in the submitted manuscript.** Section 4.2 reported a Holm-adjusted *p* = 7×10⁻⁴ for DeepSeek-V3.2 against Gemini-3.1-Pro. Two independently written scripts agree that no resample of the 20,000 reverses the sign of that gap, so the correct statement is a bound: raw *p* below the bootstrap's 5×10⁻⁵ resolution and adjusted *p* below 5×10⁻⁴, for all three frontier comparisons. The conclusion is unchanged and slightly stronger; the reported figure was wrong and is corrected.

---

## Changes made for the other reviewers

Reviewer 1 asked us to be more careful moving from API price to computational efficiency. Investigating that produced the provider-dispersion analysis described under your #4, and also exposed two silent serving faults now reported in Section 5.3: one provider billed output tokens while returning empty content, and another accepted a request to enable reasoning, returned HTTP 200, and did not enable it — producing an arm that measured direct answering under a reasoning label. The gateway's own capability metadata listed that provider as supporting the parameter, so only an output length an order of magnitude below expectation revealed it. This bears on your #6: it is a further mechanism by which a benchmark run can silently measure something other than what it claims.

Reviewer 3 asked that our claim of being "first" be stated more cautiously and that recent cost-aware security evaluations be added. Section 2.3 is rewritten around a scoped claim supported by a comparison table (Table 1), and we now state plainly that we make no claim to be first on any single axis.
