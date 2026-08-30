# Cover Letter — Revised Submission

**To:** The Editors, *Computers* (MDPI)
**Manuscript:** *Open or Frontier? A Cost- and Energy-Aware Benchmark of Large Language Models for Software Vulnerability Detection*
**Authors:** Patrick Deininger, Wolfgang Slany
**Decision:** Major revision

Dear Editors,

Thank you for the constructive reviews. All three reviewers converged on the same core objection — that our quality claim was stated more strongly than the design supported — and we found them right. We have restructured the paper around that distinction and answered every numbered comment. Point-by-point responses are enclosed separately for each reviewer.

The revision is substantial. The manuscript grows from 14 to 32 pages, adds five sections, four figures' worth of new analysis, two appendices, and roughly $166 of new measurements, including 12 additional full-scale evaluation runs and three GPU experiments.

**What survived the scrutiny.** The paper's central finding is unchanged and is now far better supported: open-weight models occupy the cost and energy efficiency Pareto frontier, and no frontier model is Pareto-optimal. We tested this against everything the reviewers raised — three prompt phrasings, three independent sample draws, two output budgets, every reasoning configuration, two measurement epochs seven weeks apart, and three serving providers on identical weights. The efficiency ordering is identical under all of them. Where the submitted manuscript asserted this robustness, the revision measures it.

**What we corrected.** Acting on the reviews surfaced problems we had not seen, and we report them rather than quietly repairing them:

- Reviewers 2 and 3 judged our learned baseline too weak. They were right, and the consequence is larger than a missing baseline: a 125-million-parameter detector fine-tuned on PrimeVul **outperforms all eight LLMs we evaluated**. The paper is therefore explicit that its comparison is a comparison *among LLMs*, conditional on lacking in-distribution training labels.
- Our quality claim proved sensitive to prompt phrasing. Three reasonable paraphrases of the same question produce three different winners. This is now reported as the sharpest limitation on the quality results, and it applies to the wider literature as much as to us.
- A *p*-value in Section 4.2 was wrong, and Flawfinder's precision had been quoted at a single threshold rather than swept. Both are corrected, and the second makes our own results look worse by comparison.
- Direct measurement showed our FLOP energy estimator describes single-request rather than batched serving, so the absolute energy and carbon figures in the submitted manuscript were overstated by roughly an order of magnitude. The comparative conclusions survive; the absolute ones are revised.
- One hypothesis of our own — that serving-provider differences explained an inter-epoch shift — we tested and refuted, and we report the negative result.

**Enclosed.** Revised manuscript (PDF); a marked-changes version showing every edit against the submitted version; the LaTeX sources needed to rebuild it; the figures; and the reproduction package. Three separate point-by-point response letters, one per reviewer, each also noting the changes made in response to the other reviewers where those changes affect the same material.

**One point of disagreement.** Reviewer 2 asked that the recalibrated claim be reflected in the title. We have made the change everywhere else requested and explain in that response why we believe *"Open or Frontier?"* — a question rather than an assertion — does not carry the overclaim. We will of course change it if you disagree.

We believe the manuscript is considerably stronger for the reviewers' scrutiny, including in the places where it is now more modest.

Yours sincerely,

Patrick Deininger (corresponding author)
Wolfgang Slany
