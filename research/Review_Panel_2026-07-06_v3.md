# Review Panel v3 — 2026-07-06

Third fresh 8-reviewer panel on `main.tex` (13→14 pp) after the Tier-A reframing, C1/C2
resolution, author metadata, and two prior proofreads. Same roster + firm anti-derail
guard on every agent (all 8 returned substantive reviews this round).

## Recommendations

| Reviewer | Recommendation |
|---|---|
| Editor-in-Chief | Minor revision |
| Methodology | Minor revision |
| Domain expert | Minor revision |
| Green-AI / Deployment | Minor revision |
| **Devil's Advocate** | **Major revision** (1 CRITICAL) |
| Structure / Golden-thread | Minor revision |
| Academic language | Minor revision (language only) |
| Statistics / number-consistency | Minor revision (1 CRITICAL contradiction) |

**Net: 7 Minor + 1 Major.** Same shape as the v2 panel, but the panel praised the
statistical discipline, honesty, and (per Stats + Structure + Language) exceptional
numerical consistency. The Major hinges on wording/framing, not new science.

## Verified against committed data

The Stats reviewer recomputed ~40 quantities; the main table, all CIs, the 9- and
15-pair Holm matrices, energy sensitivity band, carbon, baselines, and prevalence math
all reproduced. I independently recomputed the disputed reasoning numbers.

## FIXED this round (free, committed 22d865a)

- **[CRITICAL — my error] The "0.676 ceiling" is false.** Gemini-with-reasoning = 0.6774
  > DeepSeek-direct 0.6755. Reworded to **statistical parity** (0.001 gap, inside both
  CIs) in all four locations. It is a top-of-table tie, not a ceiling no one clears.
- **Reasoning cost range "four to 7.5×" → "2.5 to 7.6×"** (measured: Claude 2.48×,
  Gemini 4.42×, GPT 7.60×), sourced per-model in §4.5.
- **"compute-matched direct" mislabelled Gemini** (no direct mode; 0.623 is a 256-tok
  reasoning run). Dropped "compute-matched"; added the Gemini caveat in §4.2; scoped the
  clean direct-mode win to Claude/GPT.
- **Claude mislabelled "reasoning-only"** in §5.3 — it runs reasoning-DISABLED (only
  Gemini is reasoning-only). Fixed §3.2 and §5.3.
- **Truncation budget stated:** 8000 chars; 6.8% of the sample and **15.8% of vulnerable
  functions** truncated → absolute recall is conservative. Non-LLM baselines see
  untruncated source (Flawfinder verified: full `func`).
- **On-prem story scoped:** DeepSeek is a multi-GPU MoE; the single-GPU on-prem case is
  Gemma-3-4B (+ Llama FP8).
- Abstract: added the learned-detector baseline; "confirms"→"is consistent with".
  §4.2 split at the MCC pivot; paired-delta labelled as common-subset; contribution-3
  xref → §4.4. Green-AI: PUE band (1.5–2.0 on-prem), EU grid referent, water note, PUE
  defined. "joule" lc, "10- to 150-fold" hyphen, model-name hyphenation. Added Schwartz
  "Green AI" (CACM 2020) + Strubell (ACL 2019) refs.

**Non-issue:** the Stats reviewer claimed the open-model reasoning numbers were stale
(DeepSeek 0.603/−0.073, GLM −0.013/p=0.33). The paper's values (0.608/−0.067;
0.621/−0.017/p=0.08) **reproduce exactly** from the committed run at seed 12345,
n_boot=20000. Left as-is; the reviewer's computation differed (likely solo-full-N vs
paired-common-subset or a different seed).

## REMAINING — needs Patrick (paid runs or author info)

**Paid / new experiments (recurring across panels — the real gate to top-tier):**
- **Prompt-sensitivity probe** (Domain MAJOR; SecLLMHolmes says phrasing is first-order):
  2–3 paraphrases on the top models to show the quality ranking is stable. The
  efficiency ranking is unaffected either way.
- **Stability: ≥3 safe-pool draws / repeated generations** (EIC, Methodology, DA) to
  bound the closely-spaced middle of the table. DeepSeek's win survives; the finer
  ordering is fragile.
- **VD-Score / precision at natural 1:44 in the main table** (Domain MAJOR) — the
  dataset's own deployment metric, given the "deployment-realistic" framing.
- **PrimeVul paired (P-C) subset** for a clean memorization control (Domain) and/or a
  **PrimeVul-trained detector** (LineVul-class) to replace the strawman CodeBERT-Devign
  (DA MAJOR).
- **Measure Gemma-3-4B energy** so the efficiency-champion corner is measured, not
  estimated (DA MINOR) — needs a compatible GPU stack.

**Author info / publication:**
- **Data Availability DOI** (still `[repository URL]`) — the last hard blocker.
- Model version pins / snapshot dates; confirm RunPod idle-power (60 W placeholder).
- Release the CVE-year mapping so the contamination gradient is reproducible (Stats).
- Regenerate the H200 energy from the harness rather than the pasted JSON, with a spread
  (Methodology).

**Optional polish (free, deferred):** thin the enumerated "Two/Three X" openers and the
"robust" repetition (Language MINOR); a reasoning direct-vs-reasoning figure and an
energy-sensitivity-band figure (EIC MINOR); an SCI-style embodied-carbon magnitude
(Green-AI MINOR); Big-Vul/DiverseVul/CodeQL citations (Domain — verify details first).

## Bottom line

On the panel's own logic the paper is at **Minor revision / near-acceptance**: the one
CRITICAL was a wording error (now fixed), and the remaining Majors are either fixed
(truncation, mislabels, cost range, on-prem scoping) or are the standard "add reps /
prompt-robustness / VD-Score" strengtheners that need paid runs and Patrick's go-ahead.
