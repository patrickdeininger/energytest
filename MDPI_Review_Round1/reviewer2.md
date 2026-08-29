# Reviewer 2 - Round 1

## Review Report Form

### Does the introduction provide sufficient background and include all relevant references?
Can be improved

### Is the research design appropriate?
Can be improved

### Are the methods adequately described?
Can be improved

### Are the results clearly presented?
Yes

### Are the conclusions supported by the results?
Can be improved

### Are all figures and tables clear and well-presented?
Yes

### English language and style
The English is fine and does not require any improvement.

## Reviewer Major Comments
This is a well-structured, readable, and timely manuscript. The study has clear novelty, strong presentation, and meaningful potential for the software-security and Green AI communities. However, the authors should substantially improve the comparability of model configurations, the treatment and visualization of estimated energy values, baseline strength, uncertainty analysis, and the alignment between performance metrics and realistic vulnerability-triage deployment conditions.

1. The results show that the best open model, DeepSeek-V3.2, significantly outperforms the tested frontier models in the direct-answer setting; however, the manuscript itself finds that Gemini-3.1-Pro with a larger reasoning budget reaches balanced accuracy of 0.677, statistically indistinguishable from DeepSeek-V3.2 at 0.676. Thus, the evidence supports a conclusion of strong efficiency advantages for the tested open-weight models and direct-mode quality advantages for specific models/configurations, rather than a general conclusion that open-weight models dominate frontier systems on quality. This distinction should be reflected consistently in the title, abstract, introduction, discussion, conclusion, figures, and captions.
2. The direct-answer comparison is not fully symmetric: Gemini-3.1-Pro has no direct/non-reasoning mode, while Claude-Sonnet-5 and GPT-5.1 are run with reasoning disabled; output budgets also differ, with Claude and Gemini requiring up to 256 output tokens while other models use a 64-token budget. Although the authors acknowledge these facts, they remain central threats to comparative validity. Please present a clearly separated, configuration-matched analysis wherever feasible—for example, direct-answer/short-budget comparisons, native-reasoning comparisons, and sensitivity analyses across output budgets. The abstract should not present the direct-mode result as an unqualified cross-tier comparison.
3. Energy is measured directly only for Qwen3-Coder-30B and Llama-3.3-70B on a single H200 GPU. The remaining six model values, including all frontier models, depend on a FLOP-based estimate and, for closed models, an assumed active parameter count of approximately 100B. The authors correctly disclose this limitation, but figures and table presentation may still invite readers to interpret estimated values as directly measured per-model energy. Please visually distinguish measured and estimated energy more prominently in Table 2 and Figure 2, include uncertainty intervals or sensitivity bands for all estimated values, and avoid precise claims such as a fixed 39× or 100× advantage unless accompanied by the full parameter-assumption range.
4. All evaluated LLMs appear to be accessed through a unified API gateway for the main comparison. Consequently, the measured cost and latency reflect gateway pricing and service behavior rather than self-hosted open-model deployment. The manuscript recognizes this point, but the practical implications for on-premises security tooling should be more cautiously framed. Please distinguish: (i) open-weight availability, (ii) API-served evaluation, and (iii) actual self-hosted deployment economics and energy consumption. A simple break-even analysis for self-hosting—under stated assumptions for hardware, utilization, electricity cost, and amortization—would materially improve practical relevance.
5. The inclusion of Flawfinder and cross-dataset CodeBERT-Devign is useful, but neither is a sufficiently strong modern baseline for the study’s main task. The CodeBERT model is trained on Devign and predictably suffers from cross-dataset shift. The authors should, if feasible, include a model fine-tuned on PrimeVul training data, a stronger code-security baseline such as CodeQL or another semantic/static-analysis baseline, and/or an established vulnerability-detection method evaluated under the same function-level protocol. Without this, statements such as “the strongest tools available here” should be limited to the evaluated set.
6. Results are based on one stratified sample of 1,549 functions, one fixed seed, deterministic decoding, one task formulation, and one dataset. The paired bootstrap quantifies within-sample uncertainty but not variation due to safe-function sampling, repeated API calls, model-service drift, or prompt sensitivity. Please add repeated stratified draws and, where API cost permits, repeated runs for a representative subset. At minimum, report whether conclusions are stable under multiple safe-negative samples and alternate prompt templates.
7. Figures 1 and 2 are clear, but Figure 2 should visually encode measured versus estimated energy points and uncertainty ranges. Table 2 should likewise use a distinct marker or separate column for energy provenance, rather than relying primarily on a dagger marker and caption text. Consider adding latency to a supplementary table, since latency is discussed but is not shown in the primary results table.
8. The paper correctly reports that precision at natural 1:44 prevalence is only 2.3–3.8% for all LLMs, with many false positives per true positive. This is a crucial result and should be elevated in the abstract and conclusion. Since a real triage workflow is highly prevalence-sensitive, add metrics and analyses that better reflect deployment utility, such as precision–recall curves, false positives per true positive, workload at fixed recall, calibration/thresholding analysis, or the benchmark’s proposed scored prevalence-aware metric if applicable. The current balanced-accuracy emphasis is appropriate for comparison but insufficient to establish practical triage value.
9. The paired-bootstrap design is reasonable, and the use of Holm correction is welcome. Please provide more detail on the common parsed sets used in pairwise comparisons, treatment of parse failures, confidence-interval construction, and the exact family of hypotheses used for each correction. A supplementary table containing all pairwise effects, confidence intervals, raw p-values, and corrected p-values would improve transparency.

## Reviewer Detailed Comments
