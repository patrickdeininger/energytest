# Response to Reviewer 3

**Manuscript:** *Open or Frontier? A Cost- and Energy-Aware Benchmark of Large Language Models for Software Vulnerability Detection*

Thank you for this review. Your six points identified the methodological soft spots accurately, and two of them — the weak learned baseline and the missing reproducibility detail — led to changes larger than the requests themselves. Section numbers refer to the revised manuscript.

Briefly on what the revision did to the paper: the efficiency finding survived every test the reviews prompted, including three prompt phrasings, three sample draws, two epochs and three serving providers. The quality finding did not survive as stated and is now substantially narrowed, partly because of the baseline you asked for.

---

## #1 Strengthen related work; state the "first" claim more cautiously

> *"The related-work section should be further strengthened, especially regarding recent studies on cost-aware or efficiency-aware LLM evaluation in cybersecurity. The claim of being the 'first' study in this direction should also be stated more cautiously unless supported by a more systematic literature comparison."*

Agreed on both counts. Section 2.3 is rewritten.

The phrase *"for the first time to our knowledge"* is gone. In its place is a scoped statement of the specific conjunction that is new — a security detection task, a five-model open-weight roster, and cost *and* energy as co-equal per-task axes — supported by **Table 1**, which places this paper against the closest prior work on four columns: security task, cost reported, energy reported, and open-weight roster size. A table is a checkable way to make a priority claim; an adjective is not. We now state explicitly: *"We make no claim to be first on any single one of these axes."*

We added Lira et al. (arXiv:2604.08417), the closest cost-aware work we could find, which assesses effectiveness *and* inference cost for LLM vulnerability detection over ReposVul. It reports monetary cost but not energy, on four proprietary models with no open-weight roster — which is precisely the gap the table is meant to make visible rather than assert. Section 2.2 no longer claims novelty for the methodology itself, only for its application in this setting.

---

## #2 Proprietary energy rests on assumed active parameters

> *"The energy analysis for proprietary models relies heavily on assumed active parameter counts and unknown serving configurations. Although direct measurements on two open-weight models provide an approximate validation of the estimator, they cannot validate the estimates for proprietary models; therefore, broader sensitivity analyses and more cautious interpretation of the energy Pareto frontier are needed."*

Agreed, and we went further than sensitivity analysis. Every frontier energy figure is now a range rather than a point; **new Figure 3** sweeps the active-parameter assumption across 25B–400B; and Table 4 carries an explicit energy-provenance column with the swept range printed inline.

More importantly, we measured the estimator's behaviour directly. **New Section 4.6** reports a concurrency sweep for all three locally servable open models on a dedicated H200. Two findings:

- **The concurrency-1 measurements replicate** across pods seven weeks apart: Llama-3.3-70B 1.00× (739.9 J against 738 J), Qwen3-Coder-30B 0.95×. This had not previously been demonstrated, and the on-GPU numbers anchor the whole energy analysis.
- **The estimator describes single-request serving, not the batched serving it was calibrated for.** It is within a factor of two of the concurrency-1 measurement for all three models but 5.4–16.9× *above* the concurrency-64 measurement. Because API-served models run batched, the estimated energies and the carbon figures derived from them are overstated by roughly an order of magnitude.

Your point about "unknown serving configurations" proves sharper than the parameter-count issue. The correction factor is **architecture-dependent** — 12.7–16.9× for the two dense models, 5.4× for the sparse mixture-of-experts — and it flips a ranking: by FLOP estimate Qwen3-Coder-30B appears more efficient than Gemma-3-4B; at concurrency 1 they are level; under batching Gemma is twice as efficient. Since frontier architectures are undisclosed, we cannot say which factor applies to them. This *widens* the stated uncertainty rather than resolving it, and the manuscript says so. The claim we rely on is correspondingly weaker: the open/frontier separation exceeds the plausible range of the assumption, which it does by a wide margin even under the least favourable combination.

---

## #3 Methodological detail and retry procedures

> *"More methodological details should be provided regarding the exact prompts, output constraints, parsing rules, model versions, inference parameters, and retry procedures. These factors can directly influence both detection performance and token-related cost and are important for reproducibility."*

**New Appendix B** covers every item you list: the verbatim prompt templates for all four variants; the output constraint per model; the parser's six precedence rules and why negative markers are checked before positive ones; gateway model identifiers with the pinned provider and served precision for each (Table A2); decoding parameters and seed; the truncation rule; and the retry policy.

Your question about retries exposed a genuine gap. **The harness had no retry logic.** A transient rate limit was therefore indistinguishable from a model that could not answer, and silently depressed parse rates — we lost an entire model to a 429 in a preflight run before noticing. We implemented bounded exponential backoff with jitter over four attempts: 408, 429, 5xx and network timeouts are retried; other 4xx are not, since a malformed request fails identically forever. Empty completions are also retried, because we observed a provider billing output tokens while returning empty content. After the budget is exhausted the empty response is accepted as-is; the harness never fabricates a verdict. Every result row now records the attempts spent, so retry-inflated runs are auditable, and cost is computed from the tokens actually returned by the successful attempt.

This would have biased the robustness runs requested by Reviewer 2 had you not raised it.

We also now pin the serving provider for every run with gateway fallbacks disabled, and log the provider actually used — see #5 and the note on the other reviewers below.

---

## #4 Only one stratified subset; consider the complete test set

> *"The study evaluates only one stratified subset of PrimeVul... Repeated sampling with different random seeds, or preferably evaluation on the complete test set, would provide stronger evidence that the reported model rankings are stable."*

Repeated sampling is done, and it vindicates the concern by answering it cleanly. **New Section 4.8** reports two further independent draws of the safe pool. Because PrimeVul's test split holds only 549 vulnerable functions, all of them appear in every sample and only the 1000 safe functions vary; the three draws overlap by under 6% on the negative side. **The rank ordering is identical across all three** — Spearman correlation 1.000 against the anchor for both redraws — and no model's balanced accuracy moves by more than 0.015.

Section 4.8 also reports two variations you did not name but which turned out to matter more. Re-running the fixed positive set measures generation variance at temperature 0: per-item agreement is 88.3% to 100%, so up to twelve verdicts in a hundred flip on a repeat call. And prompt paraphrasing moves results by up to 0.088 — five to six times the draw effect — and reorders the top of the table. If the concern is whether the reported rankings are stable, the answer is that they are stable to the sample and unstable to the prompt.

**On the complete test set we would push back, and defer to you.** Running all 24,788 functions across eight models costs roughly \$275 and would narrow confidence intervals that already separate the models we claim to separate. Stratification preserves the class ratio, and the prevalence analysis in Section 4.3 is computed at the natural 1:44 rate regardless, so the deployment figures do not depend on the sample's balance. Repeated draws address the underlying concern — sampling variability — directly and at a twentieth of the cost, and they show the effect to be negligible. If you consider the full-split evaluation necessary rather than preferable, we will run it.

---

## #5 Non-LLM baselines are limited

> *"The current non-LLM baselines are relatively limited. In addition to Flawfinder and the cross-dataset CodeBERT model, the authors should consider including a stronger learned detector trained on PrimeVul and a widely used semantic/static-analysis tool, such as LineVul and CodeQL."*

Your suspicion was correct, and acting on it changed the paper's scope.

**New Section 4.4** adds **Semgrep** (community C and security-audit rulesets) and **Cppcheck**, each with its severity threshold swept rather than fixed, plus a **CodeBERT detector fine-tuned on PrimeVul's own training split** — which is the LineVul recipe you name: a RoBERTa/CodeBERT encoder with a binary classification head. We verified there is no leakage: **0 of 1549** evaluated functions, and 0 evaluated function bodies up to whitespace, occur in the training split.

**That detector outperforms every LLM in our roster**: 0.765 balanced accuracy, MCC 0.526 and 8.2% precision at deployment prevalence while recovering 71% of vulnerable functions, against the best LLM's 0.711, 0.403 and 3.8%. A 125-million-parameter encoder exceeds the best of eight general-purpose models by more than 50% on MCC, at negligible inference cost. Section 4.4 and the Conclusions now state the consequence: our LLM comparison is a comparison *among LLMs*, not a search for the best available detector. The condition is data — a fine-tuned detector needs several thousand in-distribution labels, an LLM needs none — and where such labels exist our results say to fine-tune a small model rather than prompt a large one.

Two methodological notes, both recorded in the paper because they were nearly errors. The threshold is selected on the **validation** split, not swept on the evaluation set; sweeping on the evaluation set would have reported 0.777 instead of 0.765, which describes the best a threshold could have achieved rather than what the detector achieves. And our first attempt returned 0.500 balanced accuracy with recall exactly zero — which we came close to reporting as evidence that trained detectors fare no better than LLMs on PrimeVul. It was an artifact of unweighted cross-entropy on a 2.77%-positive split: no output score exceeded 0.372, so an argmax rule could not emit a positive whatever the model had learned, while the ranking underneath was already at ROC-AUC 0.845.

**On CodeQL we must decline, with a reason.** Building a CodeQL database for C/C++ requires tracing an actual compilation, and PrimeVul functions are isolated snippets with no headers, includes or build system, so no database can be constructed for them. This is a property of the function-level task formulation rather than of CodeQL, and it applies equally to any whole-program analyzer. We state this explicitly in Section 4.4 rather than omitting CodeQL silently. Semgrep and Cppcheck are the closest substitutes designed to operate on unbuildable code.

Sweeping the analyzers' thresholds also corrected a figure of our own: Flawfinder reaches **13.4%** precision at deployment prevalence, not the 6% we had reported from a single threshold — which makes our LLM results look worse by comparison, and is reported as such.

---

## #6 Asymmetric reasoning modes and output budgets

> *"The comparison between open-weight and frontier models is not fully symmetric because different reasoning modes and output-token budgets are used. In particular, the substantial improvement of Gemini under a larger reasoning budget suggests that budget-controlled and native/recommended inference settings should be evaluated and reported separately."*

Done exactly as you and Reviewer 1 describe. **New Section 4.7** reports three configuration-matched families — budget-matched direct, native, and best-observed — all computed within a single measurement epoch with providers pinned.

We isolated the budget question you raise directly (Table 7): every model at both 64 and 256 output tokens with everything else fixed. **Seven of eight move by at most 0.004 balanced accuracy, none significantly** (*p* ≥ 0.34). Gemini-3.1-Pro is the sole exception at +0.061, and its parse rate explains it entirely: 0.542 → 0.991. Its improvement under a larger budget is therefore a *parsing* effect rather than a reasoning-quality one — at 64 tokens it spends the whole allowance on internal reasoning and never emits a verdict on 45.8% of tasks. It rejects any request to disable reasoning (`HTTP 400`), so it cannot be budget-matched at all, and we report its failure rate rather than scoring it against a set it did not answer.

The native comparison (Table 8) is now symmetric in a way the submitted manuscript could only assert: **reasoning helps every frontier model and helps neither open model.** Gemini gains +0.096, GPT-5.1 +0.044, Claude-Sonnet-5 +0.032, all significant; GLM-5 loses a non-significant 0.019 and DeepSeek-V3.2 loses 0.133 (*p* < 10⁻⁴). At best configuration the best open model beats two of three frontier models significantly and is statistically level with the best (+0.025, *p* = 0.081). Reasoning costs 4.5–12.1× more per task, so the configurations that let the frontier compete are precisely those that widen the cost gap.

---

## Changes made for the other reviewers

**Reviewer 1** asked us to be more careful moving from API list price to computational efficiency. That produced a measured provider-dispersion analysis (Section 3.3, Table 3): open weights are served by 4–14 independent operators spanning up to 14.4× in list price and differing in numerics from FP4 to `bf16`. This bears directly on your #3, since it means an unpinned run is neither price- nor numerics-reproducible; every run now pins its provider.

It also exposed a second silent serving fault relevant to your #3 and #6: a provider accepted a request to enable reasoning, returned HTTP 200, and did not enable it — producing an arm that measured direct answering under a reasoning label, at 131 mean output tokens against 1771 in an earlier epoch. The gateway's own capability metadata listed that provider as supporting the parameter, so only an output length far below expectation revealed it. Section 5.3 now states that pinning buys reproducible pricing and numerics but not a guarantee that the requested configuration was applied, and that detecting a silent no-op requires an independent expectation to check against.

We also tested whether provider choice threatens the quality results, and it does not: Llama-3.3-70B on three providers in one epoch gives a numerics contrast of −0.003 (*p* = 0.57) and an operator contrast of +0.007 (*p* = 0.17), with 96–97% per-item agreement.

**Reviewer 2** asked for threshold-swept deployment metrics. We attempted these by eliciting a calibrated confidence from each model; most models did not follow the specified scale, and VD-Score proved uncomputable for several because their score grids are too coarse for a 0.5% false-positive target. That negative result is reported in Section 4.3 (Table 6). Reviewer 2 also identified an error in our statistics: a Holm-adjusted *p*-value in Section 4.2 was wrong and is corrected to a bound.
