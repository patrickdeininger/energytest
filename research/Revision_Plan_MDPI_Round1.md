# Revision Plan — MDPI *Computers*, Review Round 1

**Manuscript:** *Open or Frontier? A Cost- and Energy-Aware Benchmark of Large Language Models for Software Vulnerability Detection* (14 pp, `main.tex`)
**Reviews:** `MDPI_Review_Round1/reviewer{1,2,3}.md`
**Editor decision:** Major revision.
**Status:** plan approved in scope (author decisions below); no manuscript edits made yet.

## 0. Decisions locked with the author (2026-08-29)

| Decision | Choice | Consequence |
|---|---|---|
| **Budget** | **T2 — full program, ≈ $170** | All twelve issues closed, including PR curves / VD-Score / calibration (P4) and measured Gemma energy (G2). |
| **Editor decision** | **Major revision** | Standard MDPI window (10–21 days). Free work lands first; runs execute in parallel. |
| **Reframing depth** | **Keep the title; recalibrate everything else** | `\Title` unchanged. Abstract, contribution bullets, §5.1, Conclusions, and all figure/table captions are rewritten against the §2 claim hierarchy. R2#1's seven surfaces minus the title — the response letter must say *why* the title is already neutral (it poses a question rather than asserting dominance). |
| **RunPod H200** | **Available now** | G1, G2, G3 all in scope, on the *same* H200 as the original measurements, so the new energy numbers are directly comparable to Table 3. G1 runs first — highest value item in the plan. |

Each paid batch will be shown with its exact command and a cost estimate before it is
fired, per standing practice.

---

## 1. Reading of the reviews

All three reviewers recommend revision, none rejects. R2 calls it "well-structured,
readable, and timely" with "clear novelty"; R1 calls it "interesting, relevant and
generally well-written"; R3 calls it "timely and practically relevant". Nobody disputes
the contribution or the data. Every substantive request is about **claim calibration and
experimental completeness**, not about redoing the study.

The three reviews converge hard. Stripped of wording, there are **twelve** distinct
issues, and the four biggest are raised by all three reviewers independently:

| # | Issue | R1 | R2 | R3 |
|---|---|---|---|---|
| **C1** | Quality claim is stronger than the design supports; reframe around efficiency | yes | #1 | yes |
| **C2** | Configuration asymmetry (reasoning modes, output budgets) → matched comparisons | yes | #2 | #6 |
| **C3** | Measured vs. estimated energy must be visually explicit, with uncertainty | yes | #3, #7 | #2 |
| **C4** | API list price ≠ compute cost; self-hosting economics | yes | #4 | — |
| **C5** | Baselines too weak (need PrimeVul-trained + semantic analyzer) | — | #5 | #5 |
| **C6** | One draw, one seed, one prompt → robustness unquantified | — | #6 | #4 |
| **C7** | Prevalence/deployment metrics must be elevated and expanded | yes | #8 | — |
| **C8** | Statistical transparency (parsed sets, CI construction, hypothesis families) | — | #9 | — |
| **C9** | Reproducibility detail (prompts, parsing, versions, retries) | — | — | #3 |
| **C10** | Related work thin; soften the "first" claim | — | yes | #1 |
| **C11** | Table/figure presentation (energy provenance column, latency table) | yes | #7 | yes |
| **C12** | English polish | yes | — | — |

**The good news:** C1, C3, C7, C8, C9, C10, C11, C12 — eight of twelve — are **free**.
They need writing, re-plotting and re-analysis of data we already hold per-item in
`harness/runs/`. C2, C4, C5, C6 need new runs, and those runs are cheap (see §4).

**The honest news:** the reviewers found the same soft spots our own three internal
review panels flagged and we deferred (`research/Revision_Log_2026-07-28.md`, "Deferred —
requires paid runs"). The deferred list and the reviewer list are nearly the same list.
That deferral is now due.

---

## 2. The one structural decision: reframing (C1)

R2 states the corrected claim precisely, and it is right:

> the evidence supports a conclusion of **strong efficiency advantages** for the tested
> open-weight models and **direct-mode quality advantages for specific
> models/configurations**, rather than a general conclusion that open-weight models
> dominate frontier systems on quality.

The manuscript already concedes this in the body (§4.4, §5.3) — Gemini-3.1-Pro at 0.677
vs. DeepSeek-V3.2 at 0.676 is a tie, and we say so. But the **abstract, the contribution
bullets, and the Conclusions still lead with quality dominance**, and the word "dominate"
appears in all three. The fix is to make the top-level framing match what §4.4 already
admits.

**Proposed claim hierarchy after revision:**

1. **Robust, configuration-invariant (headline):** open-weight models occupy the
   cost/energy efficiency Pareto frontier; no frontier model is Pareto-optimal; the
   separation is one to two orders of magnitude and *widens* when the frontier is allowed
   to reason.
2. **Configuration-specific (secondary, always qualified):** in a matched direct-answer
   configuration the best open model (DeepSeek-V3.2) significantly exceeds all three
   frontier models on balanced accuracy.
3. **Parity, not dominance (stated up front, not buried):** with native reasoning the
   strongest frontier model reaches statistical parity with the best open model at
   2.5–7.6× the cost. No configuration we tested clears the best open direct-mode score.
4. **Elevated caveat (new to abstract + conclusions, per R2#8/R1):** at PrimeVul's natural
   1:44 prevalence every LLM's precision is 2.3–3.8% against a 2.2% always-flag base rate
   — roughly 26 false positives per true positive. Not deployment-ready.

Edits: `\Title` (option — see the author questions), abstract, Intro contribution bullet 2,
§5.1 opening, Conclusions, Figure 1/2 captions, Table 2 caption.

---

## 3. Free work (no runs; data we already hold)

### 3.1 Configuration-matched comparison families — analysis half (C2)
R1 asks literally for three comparisons: *"the same token budget, the models' normal
configuration, and their best-performing configuration."* R2#2 and R3#6 ask the same.
Restructure §4 around exactly those three families:

| Family | Definition | Have | Need |
|---|---|---|---|
| **A — Budget-matched direct** | reasoning off where permitted, 64-token cap for every model | 6 of 8 | Claude@64, Gemini@64 (P3) |
| **B — Native / vendor-recommended** | each model in its default mode, budget adequate for that mode | frontier yes, DeepSeek/GLM yes | Gemma/Qwen/Llama@256 (P3) |
| **C — Best observed** | each model's best-scoring configuration in our sweep | yes | — |

The point of the section is the contrast: the **quality** ranking moves between families
(open leads A, top-of-table is a tie in B and C), while the **efficiency** ordering is
identical in all three and the gap grows A→B→C. That is the paper's robust claim, and
presenting it this way turns the reviewers' central objection into a result.

New Table 3 (three families side by side); the current §4.4 folds into it.

### 3.2 Energy provenance and uncertainty (C3, C11)
- **Table 2:** replace the `†` marker with a dedicated **Energy source** column
  (`measured (H200, NVML)` / `FLOP-estimated`), and give estimated values as a **range**,
  not a point (frontier: the 10–150× active-parameter sensitivity band we already
  computed).
- **Figure 2:** distinct marker shape *and* fill for measured vs. estimated; horizontal
  error bars spanning the sensitivity band on every estimated point; measured points carry
  the NVML run's dispersion. Legend states the distinction explicitly.
- **New Figure 3** (our own deferred item B5): energy sensitivity band — balanced accuracy
  vs. energy with the frontier active-parameter assumption swept 25B–400B, showing the
  conclusion survives the whole range.
- **Purge fixed multipliers:** "39×" and "one-hundredth" become "≈40× (10–150× across the
  plausible active-parameter range)"; the cost ratio stays precise but is relabelled
  explicitly as a *list-price* ratio, not a compute ratio.

### 3.3 Deployment utility at realistic prevalence (C7)
R1: *"should perhaps appear earlier."* R2#8: *"should be elevated in the abstract and
conclusion."* Both are right — it is currently a paragraph in §4.2 and a sentence in §5.1.

Promote to its own **Results subsection §4.5, "Deployment utility at realistic
prevalence"**, computed from existing per-item predictions:
- Precision, FP-per-TP, and alerts per 1000 functions at 1:44, with the always-flag base
  rate on the same axes.
- **Cost and energy per true positive found** — the paper's own axes applied to the
  deployment question, and the number a security lead actually needs. Computable today,
  and no other paper in this space reports it.
- Prevalence sweep (precision vs. prevalence, 1:10 → 1:200) as a small figure.
- Operating-point table: workload (functions a human must review) at each model's
  achieved recall.
- PR curves / VD-Score / calibration need a continuous score, which binary verdicts do not
  give us → run P4 in §4. Without P4 we report operating points only and say so.

### 3.4 Statistical transparency (C8)
New **Appendix A** (or Supplementary): every pairwise open-vs-frontier and
reasoning-vs-direct comparison with Δ, 95% CI, raw *p*, Holm-adjusted *p*, the hypothesis
family it belongs to, and *n* of the common parsed set. Plus explicit prose on how the
common parsed set is formed, how parse failures are handled (excluded, never counted as
"safe"), the percentile-bootstrap CI construction, and the exact families used for each
Holm correction (the 9-pair primary and the 15-pair stricter check). Generated by
extending `harness/scripts/revision_stats.py`.

### 3.5 Reproducibility appendix (C9)
New **Appendix B**: verbatim prompt templates (system + user, both modes), the output
constraint per model, the lenient parser's exact rules and precedence, model version
strings **with snapshot dates**, decoding parameters, retry/backoff policy and how retries
are accounted in cost, the truncation rule, and the gateway identity. Most of this lives in
the harness configs and needs transcribing, not deciding.

### 3.6 Latency table (C11)
Supplementary table with mean/median/p95 wall-clock and output tok/s per model, plus the
standing caveat that these were collected under concurrent load. Data already logged.

### 3.7 Related work + "first" claim (C10)
- Soften §2.2's *"for the first time to our knowledge"* to a scoped statement of what is
  novel (co-equal per-task energy **and** cost across a broad open-weight roster on a
  security-detection task), and support it with a short **comparison table** of the closest
  prior work (CyberSecEval, SecVulEval, Neef, Dahiya, HELM, TokenPowerBench) against three
  columns: security task / cost reported / energy reported. A table is a defensible way to
  make a priority claim; an adjective is not.
- Add a subsection on cost- and efficiency-aware LLM evaluation in security specifically
  (R3#1). Requires a fresh literature sweep for anything published since our last search.

### 3.8 Self-hosting economics (C4) — analytic half
New §5.x **break-even model**, stated with explicit assumptions: H200 capex/rental,
amortization window, electricity price, PUE, utilization, and measured throughput. Output
is a break-even *volume* (functions/month above which self-hosting the open model beats
the API list price) plus a sensitivity table over utilization and electricity price. The
throughput input is far better measured than assumed → run G1 in §4. This also delivers the
three-way distinction R2#4 asks for: (i) open-weight *availability*, (ii) our *API-served*
evaluation, (iii) actual *self-hosted* economics.

### 3.9 English polish (C12)
R1 alone flags language (R2 and R3 explicitly say it is fine), so this is a light pass, not
a rewrite: split the several 60+ word sentences in §4.2 and §5.1, remove the hedge-stacking
("roughly … approximately … about" inside one clause), and make comparative constructions
parallel. No change of voice or register.

---

## 4. Runs required, with costs

Costs below are **computed from our own logged per-token spend**, not estimated: a full
8-model direct sweep over N=1549 costs **$17.21**; over the 1000 safe functions only,
**$11.11**. (Frontier reasoning is the expensive part: the 3-model reasoning sweep was $64.)

| ID | Run | Answers | Cost |
|---|---|---|---|
| **P0** | **Anchor re-run** of the baseline direct config, in the same epoch as everything below | model-service drift (R2#6); makes every robustness comparison within-epoch | $17 |
| **P1** | **Prompt sensitivity** — 2 paraphrased templates × 8 models × N=1549 | R2#6, R3#3, and our own deferred item 1 | $34 |
| **P2** | **Safe-pool redraws** — 2 further independent 1000-function safe draws × 8 models (the 549 positives are exhaustive, so only the negative draw varies — exactly the reviewers' ask) | R2#6, R3#4 | $22 |
| **P3** | **Budget-matched configs** — Claude@64, Gemini@64; Gemma/Qwen/Llama@256; DeepSeek/GLM/GPT-5.1@256 | C2 families A and B; R1's "same token budget"; R2#2's budget sensitivity | $18 |
| **P4** | **Confidence-elicitation sweep** — 8 models × N=1549 emitting a 0–100 confidence alongside the verdict | unlocks PR curves, VD-Score, workload-at-fixed-recall, calibration (R2#8) | $25 |
| **P5** | **Repeat generations** — 1 further full rep, 8 models | run-to-run variance at temperature 0 (R2#6) | $17 |
| | **API subtotal (everything)** | | **≈ $133** |

| ID | GPU run (RunPod H200) | Answers | Cost |
|---|---|---|---|
| **G1** | **Concurrency/batching sweep** (1, 8, 32, 64) for Qwen3-Coder-30B + Llama-3.3-70B: energy per task **and** throughput | Kills the weakest methodological point — that concurrency-1 is energy-pessimistic and unrepresentative of API serving (R1, R2#3) — *and* supplies the throughput term for the break-even model (R2#4) | ~$15 |
| **G2** | **Gemma-3-4B measured energy** — needs a vLLM/CUDA stack that serves Gemma, or a plain `transformers` serving path (NVML measurement is stack-agnostic; a stack difference would be disclosed) | Puts the efficiency champion's corner of Figure 2 on measured rather than estimated footing | ~$8 |
| **G3** | **PrimeVul-trained detector** — fine-tune CodeBERT (LineVul-class) on the PrimeVul *train* split, evaluate on our identical 1549 functions | R2#5, R3#5 — replaces the acknowledged CodeBERT-Devign strawman with the baseline both reviewers named. Needs the train split downloaded (we hold only test locally) | ~$12 |
| | **GPU subtotal** | | **≈ $35** |

| ID | Free / local CPU | Answers |
|---|---|---|
| **F1** | **Semgrep** (security rulesets) + **Cppcheck** + **Joern** (`joern-scan`, CPG/dataflow) over the identical 1549 functions | R2#5, R3#5's "semantic/static-analysis baseline". **CodeQL is not applicable at function level**: C/C++ database creation requires a traced build, and PrimeVul functions are isolated snippets with no headers or build system. Joern is the right substitute — it fuzzy-parses snippets into code property graphs and gives genuine dataflow analysis. We say this explicitly rather than silently omitting CodeQL |

**Total: ≈ $170.** For scale, roughly a tenth of the MDPI APC.

---

## 5. Proposed scope tiers

| Tier | Contents | Cost | Addresses |
|---|---|---|---|
| **T0 — Free only** | §3 in full: reframing, matched-family analysis from existing data, energy provenance + sensitivity figures, prevalence section, appendices A/B, related work, break-even with *assumed* throughput, English pass | $0 | C1, C3, C7, C8, C9, C10, C11, C12 + partial C2, C4 |
| **T1 — Recommended floor** | T0 + P0, P1, P2, P3 + G1, G3 + F1 | ≈ $105 | **All twelve**, with the two most-cited gaps (C2 configuration, C5 baselines) fully closed |
| **T2 — Complete** | T1 + P4, P5 + G2 | ≈ $170 | Adds PR/VD-Score/calibration, run-to-run variance, measured Gemma energy |

**Recommendation: T2.** The marginal $65 from T1 to T2 buys the two things a round-2
reviewer is most likely to ask for again — a threshold-sweepable score (R2#8 explicitly
names PR curves and VD-Score) and the last estimated point on the efficiency champion. At
this price the argument for stopping at T1 is weak.

**→ T2 selected (§0).** Full program, all API runs P0–P5 and all GPU runs G1–G3 in scope.

---

## 6. Length and structure

Current: 14 pp. T2 adds roughly 2 pp of main text (matched-families §4.x, prevalence §4.5,
break-even §5.x, related-work table) and 3 figures. Appendices A and B plus the pairwise
statistics and latency tables go to **Supplementary Materials**, not the body, keeping the
main text near 16–17 pp. MDPI *Computers* has no hard page cap; the constraint is
readability, not length.

---

## 7. Execution order

Sequenced for T2 + major revision + H200 available. Stages 1–3 are concurrent: the API
batch runs unattended, the RunPod work runs on your side, and the writing proceeds against
data we already hold.

| Stage | Work | Depends on | Blocking? |
|---|---|---|---|
| **1** | **Reframing pass** (C1, §2) — abstract, contribution bullets, §5.1, Conclusions, captions. Title unchanged | — | No. Everything else is written against the corrected claim hierarchy, so this goes first |
| **2a** | **Fire API batch** P0 → P3 → P1 → P2 → P4 → P5, in that order (config-matching before robustness: P3 defines the families the rest are measured within) | Stage 1 not required | Runs unattended |
| **2b** | **RunPod: G1** concurrency sweep (1/8/32/64, Qwen + Llama) — energy per task *and* throughput | H200 pod | Feeds §3.8 break-even and the §3.2 energy discussion |
| **2c** | **RunPod: G3** PrimeVul fine-tune — download train split, fine-tune CodeBERT, evaluate on the identical 1549 | H200 pod (or any 16 GB+ card) | Gates the §5.2 baseline story |
| **2d** | **F1** Semgrep + Cppcheck + Joern, local CPU | — | Free, run immediately |
| **3** | **Free analysis and writing** §3.2–3.9: energy provenance table/figures, prevalence §4.5, appendices A/B, latency table, related-work sweep and table, English pass | Stage 1 | Concurrent with 2 |
| **4** | **RunPod: G2** Gemma measured energy | after G1 (same pod, sequential HF cache — the 100 GB volume can't hold two models) | — |
| **5** | **Fold results in** — matched-family §4.x, regenerate every figure and table, recompute each number quoted in prose against the regenerated artifacts | 2, 3, 4 | Yes |
| **6** | **Response letter** (§8), full compile, citation check, verification pass | 5 | Yes |
| **7** | **Rebuild and publish the Zenodo deposit** with the new runs | 5 | Hard blocker on resubmission |

Note on **P0 ordering**: the anchor re-run goes first so that if the services have drifted
since July, we learn it before spending on P1–P5 and can decide whether the robustness runs
are compared against the July epoch or the new one.

Note on **G1 → G2 ordering**: the RunPod volume is 100 GB and Qwen (60 GB) + Llama-FP8
(70 GB) already exceed it, so models are served sequentially with `rm -rf` between — Gemma
slots in after G1 rather than alongside it.

**Standing blocker, unrelated to the reviews:** the Data Availability DOI
`10.5281/zenodo.21391074` still 404s (reserved-but-unpublished draft). It must be published
before resubmission, and `harness.zip` rebuilt without `__pycache__` first.

---

## 8. Response letter skeleton

One document in MDPI's standard format: reviewer comment quoted verbatim, then response,
then the exact manuscript location of the change.

```
Response to Reviewers — Round 1
  Summary of changes (<= 1 page)
    - Claim hierarchy recalibrated per R2#1 (efficiency = headline; quality = configuration-specific / parity)
    - New §4.x configuration-matched families A/B/C per R1, R2#2, R3#6
    - Energy provenance + sensitivity bands in Table 2, Fig. 2, new Fig. 3 per R1, R2#3/#7, R3#2
    - New baselines: PrimeVul-trained LineVul-class detector; Semgrep/Cppcheck/Joern per R2#5, R3#5
    - New §4.5 deployment utility at realistic prevalence per R1, R2#8
    - Robustness: multiple prompt templates, 3 safe-pool draws, repeated generations per R2#6, R3#4
    - New §5.x self-hosting break-even per R2#4
    - Supplementary: full pairwise statistics, latency, prompts/parsing/versions per R2#9, R3#3
  Reviewer 1  — points 1..n   (comment / response / location)
  Reviewer 2  — comments 1..9
  Reviewer 3  — comments 1..6
```

**Three places where we should push back rather than comply**, politely and with reasons:

- **CodeQL (R3#5).** Not applicable to isolated function snippets without a build. We
  substitute Joern (CPG/dataflow, snippet-capable) and state the reason.
- **"Evaluation on the complete test set" (R3#4).** The full 24,788-function test split
  across 8 models is a ~$275 run whose only effect is to shrink confidence intervals that
  are already narrow enough to separate the models we claim to separate; the class ratio is
  preserved by our stratification, and the prevalence analysis is computed at the natural
  1:44 rate regardless. We offer repeated draws (P2) instead, which answers the actual
  concern — sampling variability — at a twentieth of the cost. *(If you would rather just
  run it, say so: it is affordable, merely poor value.)*
- **Cross-dataset CodeBERT-Devign (R2#5).** We keep it *alongside* the new PrimeVul-trained
  detector rather than replacing it: the collapse under distribution shift is itself one of
  the paper's findings and corroborates PrimeVul's own thesis. We will say plainly that it
  is a transfer reference point, not a competitive baseline, and drop the phrase "the
  strongest tools available here" per R2#5.

---

## 9. Progress log — 2026-08-29

Manuscript **30 pp**, compiles clean: exit 0, **0 LaTeX warnings**, 0 undefined refs,
2 overfull boxes (none >25pt). Harness **129 tests** (was 82). Branch
`revision/mdpi-round-1`, all work pushed.

### All twelve issues addressed

| Issue | Status |
|---|---|
| **C1** reframing | Abstract rewritten (199 w), contribution bullets, §5.1, Conclusions restructured. Title kept, justified in the letter. |
| **C2** config matching | **§4.7**: Family A (all 8 @ 64 tok, one epoch, pinned) + budget sensitivity. 7 of 8 models move ≤0.004 between 64 and 256 tokens, none significant. Gemini cannot comply (HTTP 400; 45.8% no-verdict). |
| **C3** energy provenance | Table 4 provenance column + inline ranges, Fig. 2 re-encoded, **new Fig. 3**, and **§4.6 concurrency sweep**. |
| **C4** price ≠ cost | **§3.3 + Table 3** (4.2–14.4× provider spread), provider pinning, **§5.1 + Table 8** break-even from measured throughput. |
| **C5** baselines | **§4.4**: Semgrep, Cppcheck, and a **PrimeVul-fine-tuned detector that beats every LLM**. CodeQL inapplicability documented. |
| **C6** robustness | **§4.8**: 2 prompt paraphrases, 3 safe-pool draws, repeated generations. Runs partly still executing. |
| **C7** prevalence | **§4.3 + Table 5**, elevated into abstract and conclusions. |
| **C8** statistics | **Appendix A + Table A1**, all three families. |
| **C9** reproducibility | **Appendix B**: prompts, parser precedence, versions/providers/precision, retry policy. |
| **C10** related work | §2.3 rewritten, **Table 1**, Lira et al. added (verified). |
| **C11** presentation | Provenance column, latency Table A3. |
| **C12** English | Sentences >50 words: 4 → 2. |

### The five findings we did not expect

1. **The fine-tuned detector beats every LLM.** 0.765 bal.acc / MCC 0.526 / 8.2% precision
   vs the best LLM's 0.711 / 0.403 / 3.8%, from 125M parameters. Threshold chosen on
   *validation* (oracle would have been 0.777). Zero leakage verified.
2. **A *p*-value in §4.2 was wrong** — 7×10⁻⁴ should be a bound below the bootstrap's resolution.
3. **Flawfinder's precision was quoted at one threshold** — 13.4% swept, not 6%.
4. **The FLOP estimator describes single-request, not batched, serving** — 5.4–16.9× above
   the c=64 measurement, so absolute energy and carbon figures are ~an order of magnitude high.
   Architecture-dependent, which flips the Gemma/Qwen ranking between regimes.
5. **Our provider hypothesis was refuted.** Three-provider control on identical Llama weights:
   numerics −0.003 (p=0.57), operator +0.007 (p=0.17), 96–97% agreement. The July→August
   shifts are model-service drift, not serving-layer dependence.

Also: the concurrency-1 measurements **replicate** (Llama 1.00×, Qwen 0.95×), retiring the
`"source": "pasted"` reproducibility gap.

### GPU work — complete

G1 (concurrency sweeps, 3 models), G2 (Gemma, unblocked by pinning `transformers==4.55.2`),
G3 (PrimeVul fine-tune) all done. The pod can be terminated. `setup_gpu.sh` now pins the
working stack and prints resolved versions for Appendix B.

### Still running

API batch: `prompt_v2` ~82%, then `prompt_v3`, `draw2`, `draw3`. **$55.74 of ~$88.**
Resumable — re-run `harness/scripts/run_round2_batch.sh`, completed rows are skipped.
§4.8's results paragraph is the last placeholder in the manuscript.

### Open decision

Families B and C are deliberately **not** merged with Family A: the reasoning runs are the
July epoch and drift is real. Bringing them in-epoch costs ~$64 (3 frontier models with
reasoning). Currently the paper reports each family within its own epoch and says so.
