"""The README.md shipped inside reproduction.zip.

Kept as a module rather than a literal inside the builder so it can be edited as
prose and checked by eye. `build_resubmission.py` writes it to the archive root.
"""

README = r"""# Reproduction Package

Measurement harness, raw results and analysis code for:

**Open or Frontier? A Cost- and Energy-Aware Benchmark of Large Language Models
for Software Vulnerability Detection**
Patrick Deininger and Wolfgang Slany — MDPI *Computers* (revised submission)

Archived at Zenodo: <https://doi.org/10.5281/zenodo.21391073>
(concept DOI — always resolves to the latest version)

---

## What is here

| Path | Contents |
|---|---|
| `harness/` | The measurement harness: model backends, cost/latency/energy meters, scoring, analysis. 129 tests. |
| `harness/configs/` | Every run configuration, including the pinned serving provider and the price snapshot used for each model. |
| `harness/runs/` | Raw per-task records for every run reported in the paper, plus each run's resolved config, seed, git SHA and price snapshot. |
| `harness/scripts/` | Analysis entry points — see the mapping below. |
| `harness/tests/` | The test suite. `python -m pytest harness/tests` |
| `figures/` | Figures at the resolution used in the paper. |
| `main.pdf` | The manuscript. |
| `LICENSE` | CC BY 4.0, with carve-outs for third-party material. |

### Deliberately not included

| Omitted | Why, and how to obtain it |
|---|---|
| `harness/data/primevul/primevul_test.jsonl` (66 MB) | The PrimeVul corpus belongs to its original authors and is re-downloaded rather than redistributed. Run `python -m harness.scripts.fetch_primevul`, which fetches it and **refuses to install a copy whose row and class counts do not match** the split used here — a mirror carrying a different dataset revision would silently change the evaluated sample. |
| The fine-tuned detector's checkpoint (~500 MB) | Regenerated exactly by `primevul_trained_baseline.py` at the recorded seed. |
| That detector's per-item scores | Re-emitted by the same script. |

Every analysis in the paper other than the detector re-training can be reproduced from
what is in this archive; only re-running *inference* against the models needs the corpus
and API credentials.

---

## Setup

```bash
pip install -r harness/requirements.txt
python -m pytest harness/tests          # 129 tests, no network or GPU required
python -m harness.scripts.fetch_primevul  # only if re-running inference
```

API access, if re-running inference: copy `.env.example` to `.env` and add an
OpenRouter key. **Every reported figure can be recomputed from the committed run
records without any key.**

---

## Reproducing the paper

Each script regenerates the artifact named beside it. All read from
`harness/runs/` and need no network.

| Script | Produces |
|---|---|
| `build_final_analysis.py` | `enriched_metrics.csv`, Figure 1, Table 4 |
| `energy_figures.py` | Figures 2 and 3 (energy with provenance and sensitivity bands) |
| `prevalence_analysis.py` | Section 4.3 and Table 5 — deployment metrics at 1:44 prevalence |
| `confidence_analysis.py` | Table 6 — elicited confidence as a score source |
| `static_baselines.py` | Semgrep and Cppcheck rows of Table 7 (needs those tools installed) |
| `primevul_trained_baseline.py` | The fine-tuned detector rows of Table 7 (needs a GPU) |
| `score_per_item.py` | Threshold-free scoring of any per-item score file |
| `analyze_sweeps.py` | Section 4.6 and Table 8 — measured energy and throughput vs concurrency |
| `families_analysis.py` | Section 4.7, Tables 11 and 12 — configuration-matched families |
| `robustness_analysis.py` | Section 4.8 and Table 13 — prompt, draw and run-to-run variation |
| `pairwise_stats.py` | Appendix A and Table A1 — all pairwise effects, CIs and corrected *p* |
| `price_snapshot.py` | Table 3 — provider price and quantization dispersion (needs network) |
| `verify_paper_numbers.py` | Cross-checks 14 published figures against these artifacts |

```bash
python -m harness.scripts.verify_paper_numbers   # start here
```

---

## Three things to know before interpreting the runs

**There are two measurement epochs, and they should not be pooled.** Re-running the
anchor configuration seven weeks after the original evaluation moved several models by
+0.03 to +0.06 balanced accuracy. A three-provider control on identical weights rules out
provider and precision as the cause (effects below 0.01), so this is model-service drift.
Runs prefixed `r2_` are the later epoch; the others are the original. Every comparison in
the paper is made *within* an epoch, and Section 4.9 reports the earlier one as a
replication rather than merging it.

**Serving providers are pinned, and this matters.** An open-weight model reached through a
gateway may be served by up to fourteen independent operators whose prices differ by 14×
and whose numerics differ from FP4 to `bf16`. Every `r2_` config names its provider with
fallbacks disabled, and every result row records the provider that actually served it.
Two silent faults were caught this way and are documented in the paper: one provider
billed output tokens while returning empty content, and another accepted a request to
enable reasoning, returned HTTP 200, and did not enable it.

**Energy is measured in one regime and estimated in another.** On-GPU measurements are
NVML counter reads with the bare idle draw subtracted. FLOP-based estimates match
single-request serving to within a factor of two but sit 5–17× above batched serving, so
absolute energy figures for API-served models are upper bounds. Rows carry an
`energy_source` field; never mix the two without reading Section 4.6.

---

## Result record schema

One JSON object per model × task in `harness/runs/*/results.jsonl`:

| Field | Meaning |
|---|---|
| `model_id`, `task_id`, `rep` | Identity of the call |
| `label`, `prediction`, `correct` | Ground truth and verdict (1 = vulnerable) |
| `parsed_ok` | False when no verdict could be extracted. **Excluded from metrics, never scored as "safe"** — recoding failures as negatives would credit a failing model with specificity. |
| `confidence` | Elicited P(vulnerable), where the prompt asked for it |
| `raw_output` | Model output, truncated to 2000 characters |
| `usd_cost`, `input_tokens`, `output_tokens` | Cost computed from logged tokens and the config's price snapshot |
| `energy_j`, `active_energy_j`, `energy_source` | Energy and its provenance |
| `total_ms`, `tokens_per_s` | Client-side latency; collected under concurrency, so it conflates model speed with queueing |
| `provider`, `attempts` | Which upstream served it, and how many attempts it took |
| `prompt_variant`, `max_output_tokens` | The configuration actually used |

---

## Citing

Please cite the paper. If you use the harness itself, the Zenodo DOI above resolves to the
archived version. The PrimeVul dataset should be cited to its original authors.
"""
