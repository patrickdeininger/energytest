# Revision Log — 2026-07-28

Revision round run under ARS `academic-paper` **revision mode**. There was no new
external decision letter this round, so the revision targets (a) the still-open *free*
items from the v3 review panel (`Review_Panel_2026-07-06_v3.md`) and (b) defects
introduced into the working tree while preparing the MDPI submission package.

Status vocabulary: **ADDRESSED** / **PARTIALLY ADDRESSED** / **DEFERRED** / **DISAGREE**.

Build state after this round: `main.tex` compiles to **15 pages**, 0 LaTeX warnings,
0 undefined references, 0 overfull boxes, **0 BibTeX warnings**. Harness suite: **82/82 pass**.

---

## Group A — Submission-package defects (found this round, not reviewer-raised)

### A1. Abbreviations list belonged to a different paper — **ADDRESSED**

**Finding.** The `\abbreviations` block added during submission prep listed 34 terms —
ANOVA, BIOS, CDI, DMA, GiB, HPC, IaaS, IOMMU, ITL, KPI, KVM, LXC, MIG, MPS, NUMA, PCI,
PVE, QEMU, SD, SM, SMT, SR-IOV, TOST, TPOT, TTFT, USB, VFIO, vGPU, VM, VMM, VRAM and
others. Each of them occurs **exactly once in the whole manuscript: inside the
abbreviations block itself.** The list was imported from an unrelated
GPU-virtualization manuscript and describes nothing in this paper.

**Change.** Replaced with the abbreviations this paper actually uses, in MDPI's
canonical tabular form: API, CI, CVE, FLOP, FP8, GPU, LLM, MCC, MoE, NVML, PUE.

**Why it mattered.** Shipping it would have been an immediate, visible signal to the
editorial office that the submission was assembled from another paper's template.

### A2. Data Availability DOI — **PARTIALLY ADDRESSED (blocker remains)**

**Change.** Reformatted from the bare string `Zenodo (10.5281/zenodo.21391074)` to a
resolvable link per MDPI style: `https://doi.org/10.5281/zenodo.21391074`.

**BLOCKER.** The DOI **does not resolve**. Checked three independent endpoints — all 404:
- `https://doi.org/10.5281/zenodo.21391074`
- `https://zenodo.org/records/21391074`
- `https://zenodo.org/api/records/21391074`

That signature is consistent with a **reserved-but-unpublished Zenodo draft**. Zenodo
issues the DOI at draft creation but does not register it with DataCite until the record
is published. **Action required by the author: publish the Zenodo record.** Until then the
Data Availability statement points at nothing, which is a desk-reject risk.

### A3. `harness.zip` deposit bundle — **DEFERRED to author**

- **Stale.** Built 2026-07-16; predates both the README rewrite and the test-count fix below.
- **Contains build artefacts.** 57 of its 1,799 entries are `__pycache__/*.pyc`.
- **Security scan: clean.** Scanned all text-bearing entries for credential patterns
  (`sk-`, `sk-or-v1-`, `AIza`, `ghp_`, bearer tokens) and for `.env` / key / credential
  filenames. **No matches.** Safe to publish; should be rebuilt without bytecode first.

### A4. Harness README claimed the wrong test count — **ADDRESSED**

README said `pytest suite (34 tests)`; the paper claims 82. Authoritative count via
`pytest --collect-only` is **82**, and all 82 pass. The paper was right, the README was
stale. README corrected — this matters because the README ships in the Zenodo deposit,
so the two artifacts would have contradicted each other in public.

### A5. First-submission front matter — **ADDRESSED**

`\daterevised{ }` commented out (a first submission has no revised date).

### A6. CRediT statement — **FLAGGED, no change made**

The revised `\authorcontributions` assigns W.S. **Supervision only**, having dropped W.S.
from Conceptualization and from Writing – review & editing (both present in the previous
committed version). This is valid MDPI/CRediT — every author retains at least one role —
but it is an authorship decision, not an editorial one, so it is left as the author set it.
**Confirm this is intended before submitting.**

---

## Group B — v3 review panel, remaining free items

### B1. Academic-language reviewer (MINOR): enumerated openers and "robust" repetition — **ADDRESSED**

**Enumerated "N X" openers reduced from four to two.** Removed the scaffolding from
§4.2 ("Three findings hold. First… Second… Third…") and §4.5 ("Two conclusions follow.
First… Second…"), converting both to direct prose. Retained the two that earn their
keep and are far apart with different verbs: §1 "Two blind spots persist" (sets up the
paper's motivation) and §4.4 "Two cautions bound what this validates."

**"robust" reduced from three uses to one.** The surviving use is the correct technical
sense ("the efficiency dominance is *robust to* allowing the frontier to reason").
The two rhetorical uses were replaced: "The robust claim is therefore narrower" →
"The defensible claim…"; "The robust finding is efficiency" → "Efficiency is the
firmest finding."

### B2. Domain reviewer (MINOR): Big-Vul / DiverseVul / CodeQL citations — **ADDRESSED**

All three verified against primary sources before being added (Crossref
content-negotiated records, dblp, and the RAID camera-ready PDF):

| Key | Work | Venue | Verified via |
|---|---|---|---|
| `bigvul` | Fan, Li, Wang, Nguyen — *A C/C++ Code Vulnerability Dataset…* | MSR 2020, 508–512 | Crossref `10.1145/3379597.3387501`, dblp |
| `diversevul` | Chen, Ding, Alowain, Chen, Wagner — *DiverseVul…* | RAID 2023, 654–668 | Crossref `10.1145/3607199.3607242`, camera-ready PDF |
| `codeql` | GitHub, Inc. — *CodeQL Documentation* | — | `codeql.github.com/docs/` |

**On CodeQL:** there is no canonical CodeQL paper. The two candidate papers (de Moor
et al. 2008 `.QL`; Avgustinov et al. ECOOP 2016 `QL`) describe the underlying query
language and **do not mention CodeQL by name**. Since the paper cites CodeQL as a *tool*
we would use as a future baseline, citing a language-design paper would misattribute it.
Cited the official documentation instead.

**Integration.** §2.1 now traces the dataset lineage — "from Devign and Big-Vul to the
de-duplicated DiverseVul" — before the label-noise point, which is more accurate than
lumping DiverseVul in with the noisy sets, since it was itself built to reduce that
noise. CodeQL is cited at the Baselines limitation where it was already named.

### B3. Green-AI reviewer (MINOR): SCI-style embodied-carbon magnitude — **ADDRESSED**

The paper previously named embodied carbon only to exclude it. It now carries a bounded
magnitude, sourced rather than asserted:

- **130–165 kgCO₂eq cradle-to-gate per datacenter GPU** — 127.6 kg from a primary-data
  teardown LCA of an A100 (Falk et al., *Environmental Impact Assessment Review* 121:108525,
  2026, peer-reviewed) and ≈164 kg per H100, derived from NVIDIA's disclosure of
  1,312 kgCO₂eq for the eight-GPU HGX H100 baseboard — a vendor figure, but one
  **critically reviewed to ISO 14067 by an independent third party (WSP)**.
- **≈4–7 gCO₂eq per GPU-hour** amortized over a 3–6 year service life at high utilization.
  Presented as our own arithmetic from the cited inputs, not as a quoted figure. The
  lifetime bracket endpoints are both peer-reviewed and AI-hardware-specific
  (Falk et al. 3 y; Luccioni et al. 6 y).
- **A fifth to a half of life-cycle emissions** attributable to manufacturing, the higher
  share on low-carbon grids (Luccioni et al., JMLR 24(253), 2023; Léobet et al. 2026).

**Framework.** Amortization follows the Software Carbon Intensity specification, cited as
**ISO/IEC 21031:2024** — the standardized form, stronger for a journal than the foundation
white paper.

**Argument added, not just a number.** Embodied carbon is a same-order *addition* to the
operational figures rather than a reversal, and since it accrues with occupied GPU-time it
falls hardest on the models that occupy the most per task. The honest counter-direction is
retained and sharpened: low on-premises utilization amortizes the same hardware over fewer
tasks, which is why the figures stay illustrative rather than a life-cycle assessment.

**Also:** the §5.1 carbon discussion had grown into one very long paragraph, so it was split
into three (operational magnitudes / embodied carbon / caveats), and a pronoun reference
broken by the insertion was repaired.

### B4. Reference `parttime` was broken **and** superseded — **ADDRESSED** (found this round)

BibTeX was emitting `Warning--empty author in parttime`: the entry had **no author field
at all**. Verifying it surfaced a second, larger problem — the arXiv preprint
(*"Part-time Power Measurements: nvidia-smi's Lack of Attention"*, arXiv:2312.02741) was
**published at SC24 under a different title**.

Corrected to: Yang, Z.; Adamek, K.; Armour, W., *"Accurate and Convenient Energy
Measurements for GPUs: A Detailed Study of NVIDIA GPU's Built-In Power Sensor"*,
SC24, pp. 1–17, DOI `10.1109/SC41406.2024.00028` (verified via Crossref).

This citation supports the paper's NVML under-sampling claim, so it is load-bearing for
the energy methodology — citing the superseded preprint under a stale title would have
been a poor look in exactly the section a Green-AI reviewer reads most closely.

### B5. EIC (MINOR): reasoning-vs-direct and energy-sensitivity-band figures — **DEFERRED**

Not attempted this round. Both are free to produce from committed data, but they add
figures to an already figure-complete 15-page paper. Flagged for the author to decide.

### B6. Bibliography compliance sweep — **ADDRESSED** (found this round)

MDPI permits "et al." only for works with **more than** 10 authors; 14 entries were
abbreviating with `and others` regardless. All 14 author lists were verified against
arXiv (abs pages + Atom API), Crossref and dblp, and expanded in full. Only three
genuinely exceed 10 authors and keep the truncation: `cyberseceval` (21),
`mlperfpower` (26), `helm` (50). `samsi` has **exactly 10**, so all ten are now listed.

Verifying them surfaced six further errors that had nothing to do with author counts:

| Entry | Problem found | Fix |
|---|---|---|
| `happe-review` | Cited as "Happe et al." — the paper has **only two authors** | Happe, A.; Cito, J. |
| `steenhoek` | Bib paired the **v1 title** with a bare arXiv ID that resolves to **v2**, which was retitled and has 8 authors, not 6 | Updated to the v2 title *"To Err is Machine: Vulnerability Detection Challenges LLM Reasoning"* + 8 authors |
| `secvuleval` | Cited as a preprint; **published at AIware '26 and retitled** | Now `@inproceedings`, ACM, pp. 388–396, DOI `10.1145/3805760.3814932` |
| `mlperfpower` | Cited as a preprint **and the title was truncated** | HPCA 2025, pp. 1201–1216, DOI `10.1109/HPCA61900.2025.00092`; title restored to "…from Microwatts to Megawatts for Sustainable AI" |
| `tokenpowerbench` | Cited as a preprint; **published at AAAI 2026** | pp. 32582–32590, DOI `10.1609/aaai.v40i38.40535` |
| `helm` | Cited as a 2022 arXiv preprint; **published in TMLR 2023**. Title also carried an editorial " (HELM)" that is not part of it | `Transactions on Machine Learning Research`, 2023; title corrected |

DOIs and page numbers were also added to `primevul`, `samsi` and `secllmholmes`, which
were already cited as published but lacked both.

**One text change followed from this.** §2.1 characterized Steenhoek et al. as reporting
"function-level accuracy close to random". The v2 paper states a specific figure — **54.5%
balanced accuracy for state-of-the-art models** — which is not only verifiable but is
expressed in *the same primary metric this paper adopts*. The sentence now cites the
number directly.

---

## Deferred — requires paid runs (author go-ahead needed)

Unchanged from the v3 panel; these remain the real gate to a top-tier accept and are
carried in the paper as Acknowledged Limitations (§5.3):

1. **Prompt-sensitivity probe** (Domain MAJOR) — 2–3 paraphrases on the top models.
2. **≥3 safe-pool draws / repeated generations** — bounds the closely-spaced middle of Table 2.
3. **VD-Score / precision at natural 1:44** in the main table.
4. **PrimeVul-trained detector** (LineVul-class) to replace the off-the-shelf CodeBERT-Devign,
   and/or the **PrimeVul paired P–C subset** as a memorization control.
5. **Measured Gemma-3-4B energy** so the efficiency-champion corner is measured, not estimated.

---

## Author actions before submission

1. **Publish the Zenodo record** — the DOI in Data Availability currently 404s. *(hard blocker)*
2. Rebuild `harness.zip` without `__pycache__` and re-upload before publishing.
3. Confirm the CRediT change (A6) reflects the intended division of contributions.
4. Decide on B5 (two optional figures).
5. Model version pins / snapshot dates; confirm the RunPod idle-power placeholder (60 W).
