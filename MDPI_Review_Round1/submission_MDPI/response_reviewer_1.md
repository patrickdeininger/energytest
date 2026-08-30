# Response to Reviewer 1

**Manuscript:** *Open or Frontier? A Cost- and Energy-Aware Benchmark of Large Language Models for Software Vulnerability Detection*

We are grateful for this review. Your central objection — that the comparison was not equal across models and that the claims consequently outran the design — was shared by both other reviewers and became the organising principle of the revision. Section numbers below refer to the revised manuscript.

Before the point-by-point: the finding you were most sceptical of turned out to be the one that survived hardest testing. The efficiency result is unchanged under three prompt phrasings, three sample draws, two output budgets, every reasoning configuration, two measurement epochs and three serving providers. The quality result did not survive as stated, and we have narrowed it accordingly.

---

## 1. Unequal comparison: reasoning modes and output-token limits

> *"The main problem is that the comparison is not completely equal between all models: some models use reasoning and others do not, the output-token limits are not always the same... I suggest presenting separate comparisons for the same token budget, for the models' normal configuration, and for their best-performing configuration."*

Done exactly as you describe. **New Section 4.7** presents all three, computed within a single measurement epoch with serving providers pinned:

- **Family A — budget-matched direct** (Table 6): every model at 64 output tokens, reasoning disabled wherever the provider permits it.
- **Family B — native configuration** (Table 8): every reasoning-capable model with reasoning enabled at a 4096-token budget.
- **Family C — best observed**: each model's best score across all configurations.

Three results follow.

**The output budget does not drive the results.** We isolated this directly (Table 7): every model was run at both 64 and 256 output tokens with prompt, seed, sample and provider held fixed. Seven of eight move by at most 0.004 balanced accuracy, and none significantly (*p* ≥ 0.34). The asymmetry you identified is real but empirically negligible for every model that can comply with it.

**One model genuinely cannot be budget-matched, and we now demonstrate it rather than assert it.** Gemini-3.1-Pro returns `HTTP 400: "Reasoning is mandatory for this endpoint and cannot be disabled"`, and at a 64-token budget spends the entire allowance on internal reasoning, emitting no verdict on 45.8% of tasks. It is the sole exception in Table 7 (+0.061), and its parse rate explains it entirely (0.542 → 0.991): the gain is a *parsing* effect, not a reasoning-quality one. We report its failure rate rather than scoring it against a set it did not answer, and we note that any comparison against it rests on the 54.2% of tasks it chose to answer.

**The conclusion is narrower than we had claimed.** In Family A the open-weight lead survives and strengthens — DeepSeek-V3.2 (0.711) significantly exceeds all three frontier models. But Claude-Sonnet-5 reaches 0.653 under budget matching, level with Gemma-3-4B to three decimal places (*p* = 0.98) and third on MCC. In Family C, against each frontier model at its own best configuration, the best open model beats two of three significantly and is **statistically level with the best of them** (+0.025, *p* = 0.081). We state both halves rather than resting on "the three highest-scoring models are all open-weight."

---

## 2. Claims stronger than the design supports

> *"The claims about energy dominance and the Pareto frontier are sometimes stronger than what the design can fully support."*

Agreed. The paper now separates two claims of different strength wherever it makes them — abstract, contribution list, Section 5.1, Conclusions and every affected caption:

1. **Configuration-invariant:** open-weight models occupy the efficiency Pareto frontier; no frontier model is Pareto-optimal.
2. **Configuration-specific:** at a matched budget the best open model significantly beats all three frontier models.
3. **Parity, not dominance:** the strongest frontier system is level with the best open model at best configuration.
4. **Not deployment-ready:** precision 2.3–8.2% at natural prevalence.

The word "dominate" no longer appears in reference to quality. Reviewer 2 raised the same point independently and asked additionally that it be reflected in the title; we explain in that response why we have kept the title and changed everything else.

---

## 3. Figure 2 should distinguish measured from estimated energy, with uncertainty

> *"Figure 2 should also show much more clearly which values are measured and which are estimated, preferably with uncertainty ranges."*

Done, and the investigation went further than presentation.

Table 4 now carries an explicit **Energy source** column, with each frontier estimate printed alongside its sensitivity range. Figure 2 distinguishes measured from estimated points by marker shape *and* fill, with horizontal bars spanning the range each estimate takes as the assumed active-parameter count is swept. **New Figure 3** sweeps that assumption across 25B–400B. Every fixed multiplier ("39×", "one-hundredth") is now a range.

Acting on this led to a substantive finding. We re-measured all three locally servable open models across a concurrency sweep on a dedicated H200 (new Section 4.6, Table 5). Two results followed:

- **The published measurements replicate.** On a different GPU pod seven weeks later, with a different measured idle draw, Llama-3.3-70B reproduces to 1.00× (739.9 J against 738 J) and Qwen3-Coder-30B to 0.95×. The on-GPU numbers are the empirical anchor of the whole energy analysis and their reproducibility had not previously been shown.
- **The FLOP estimator describes single-request serving, not the batched serving it was calibrated for.** It is within a factor of two of the concurrency-1 measurement for all three models, but 5.4–16.9× *above* the concurrency-64 measurement. Since API-served models run batched, the estimated energies — and the carbon figures derived from them — are overstated by roughly an order of magnitude. We now say so.

The correction is architecture-dependent, which flips a ranking: by FLOP estimate the sparse Qwen3-Coder-30B looks more efficient than the dense Gemma-3-4B; at concurrency 1 they are level; under batching Gemma is twice as efficient. Because frontier architectures are undisclosed, this *widens* the uncertainty on their figures rather than resolving it. The claim we rely on is correspondingly weaker: the separation exceeds the plausible range of the assumption, which it does by a wide margin even under the least favourable combination.

---

## 4. Market price is not real serving cost

> *"The authors should also be more careful when moving from API price to computational efficiency, because market price is not the same as real serving cost."*

This was the most productive comment in the review, and we replaced hand-waving with measurement.

**New Section 3.3 and Table 3** record every provider serving each evaluated model at one instant. An open-weight model is typically offered by four to fourteen independent operators whose input prices differ by up to **14.4×** — DeepSeek-V3.2 ranges from \$0.209 to \$3.00 per million input tokens. More consequentially, those providers differ in *numerics*: the same Llama-3.3-70B weights are served at `bf16`, `fp16` and FP8 by different operators. A cheaper endpoint is therefore sometimes a different computation rather than a better deal.

Two methodological changes follow. Every run now **pins its provider** with gateway fallbacks disabled, so the configured price is the price charged and the numerics are fixed. And we treat the cost axis as an operating point with a provider attached rather than an intrinsic model property.

We then tested whether the dispersion threatens the *quality* results, and it does not. Llama-3.3-70B run on three providers in one epoch — two FP8 from different operators, one `bf16` — gives balanced accuracy 0.599–0.609, a numerics contrast of −0.003 (*p* = 0.57), an operator contrast of +0.007 (*p* = 0.17), and 96–97% per-item agreement. We had written serving-layer dependence into Section 5.3 as a threat to validity; the measurement refutes it and Section 5.3 now reports the negative result.

Pinning did, however, expose two silent serving faults, both recorded in Section 5.3. One provider **billed output tokens while returning empty content**, which unpinned would have been scored as a model parse failure. Another **accepted a request to enable reasoning, returned HTTP 200, and did not enable it** — producing an arm that measured direct answering under a reasoning label, while the gateway's capability metadata listed that provider as supporting the parameter. Only an output length an order of magnitude below expectation revealed it. The lesson we draw and report is that pinning buys reproducible pricing and numerics but not a guarantee that the requested configuration was applied.

Finally, **Section 5.1 and Table 10** give the self-hosting break-even analysis, with throughput **measured** rather than assumed. It refines our own headline: the small models sustain 45–64 tasks/s on one H200 and are three to seven times cheaper self-hosted, but Llama-3.3-70B sustains only 8.0 and straddles break-even — 1.6× cheaper on owned hardware, 1.5× *dearer* on rented. The open models' price advantage is therefore partly physical and partly a market artifact, and the paper now separates the two.

---

## 5. Realistic prevalence should appear earlier

> *"The discussion about realistic prevalence is important and should perhaps appear earlier, because precision of around 2-4% means that the models are still not ready for independent practical use."*

Agreed and done. It is now **Section 4.3**, immediately after Detection Quality rather than in the Discussion, and considerably expanded: precision, false positives per true positive, alert volume per 1000 functions scanned, workload at achieved recall, a prevalence sweep, and cost and energy *per true positive found*. The headline figures are now in the abstract, the introduction and the conclusions.

The numbers support your reading. Each model alerts on 43–75% of *all* functions scanned; Gemini-3.1-Pro flags 722 of every 1000 to find 21 of the 22 real ones. The best model raises 25.6 false alarms per true finding.

Reviewer 2 asked for the same elevation together with threshold-swept metrics, and one result from that work belongs here: at every threshold, a classical static analyzer is **more precise** than any LLM. Flawfinder reaches 13.4% precision against the best LLM's 3.8% — a figure we had previously understated as 6% by quoting a single threshold. Reviewer 3's request for a stronger learned baseline produced a sharper version still: a small fine-tuned detector reaches 8.2% precision at 71% recall, above every LLM on both axes.

---

## 6. English language and style

> *"The English could be improved to more clearly express the research."*

We have made a light pass: the longest sentences in Sections 4.2 and 5.1 are split, stacked hedges removed, and comparative constructions made parallel. Sentences over 50 words are reduced from four to two. Reviewers 2 and 3 judged the language to need no improvement, so we have not changed register or voice, but we are glad to go further if specific passages remain unclear.

---

## Changes made for the other reviewers

Two changes requested by Reviewers 2 and 3 materially affect the results you reviewed:

**A stronger learned baseline changes the paper's scope.** Both asked for a detector fine-tuned on PrimeVul's own training split rather than the off-the-shelf cross-dataset model we used. That detector — 125 million parameters — **outperforms all eight LLMs**: 0.765 balanced accuracy and MCC 0.526, against the best LLM's 0.711 and 0.403, at negligible inference cost. Section 4.4 and the Conclusions now state that our LLM comparison is a comparison *among LLMs*, conditional on lacking in-distribution labels.

**Prompt sensitivity limits the quality claims further.** Reviewers 2 and 3 asked for robustness to prompt phrasing. New Section 4.8 reports that paraphrasing moves results by up to 0.088 balanced accuracy — five to six times the effect of resampling — and reorders the top of the table: DeepSeek-V3.2 leads under the anchor prompt, Claude-Sonnet-5 under one paraphrase, GLM-5 under the other. Three reasonable phrasings, three different winners. This is the sharpest limitation on the quality results in the paper. The efficiency conclusions are untouched: cost and energy track token counts, not phrasing, and that ordering is identical under all three prompts.
