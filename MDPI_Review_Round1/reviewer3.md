# Reviewer 3 - Round 1

## Review Report Form

### Does the introduction provide sufficient background and include all relevant references?
Can be improved

### Is the research design appropriate?
Can be improved

### Are the methods adequately described?
Can be improved

### Are the results clearly presented?
Can be improved

### Are the conclusions supported by the results?
Can be improved

### Are all figures and tables clear and well-presented?
Can be improved

### English language and style
The English is fine and does not require any improvement.

## Reviewer Major Comments
Overall, this manuscript addresses a timely and practically relevant topic by comparing open-weight and frontier LLMs for software vulnerability detection from the perspectives of detection performance, monetary cost, and energy efficiency. The study is generally well organized, and the use of PrimeVul, statistical significance testing, and a reproducible evaluation framework are notable strengths. However, several methodological and experimental issues still limit the robustness of the main conclusions, particularly regarding energy estimation, reproducibility, dataset sampling, baseline selection, and fairness of model comparison.

Specific comments:

1. The related-work section should be further strengthened, especially regarding recent studies on cost-aware or efficiency-aware LLM evaluation in cybersecurity. The claim of being the “first” study in this direction should also be stated more cautiously unless supported by a more systematic literature comparison.

2. The energy analysis for proprietary models relies heavily on assumed active parameter counts and unknown serving configurations. Although direct measurements on two open-weight models provide an approximate validation of the estimator, they cannot validate the estimates for proprietary models; therefore, broader sensitivity analyses and more cautious interpretation of the energy Pareto frontier are needed.

3. More methodological details should be provided regarding the exact prompts, output constraints, parsing rules, model versions, inference parameters, and retry procedures. These factors can directly influence both detection performance and token-related cost and are important for reproducibility.

4. The study evaluates only one stratified subset of PrimeVul, consisting of all vulnerable samples and 1,000 sampled safe functions. Repeated sampling with different random seeds, or preferably evaluation on the complete test set, would provide stronger evidence that the reported model rankings are stable.

5. The current non-LLM baselines are relatively limited. In addition to Flawfinder and the cross-dataset CodeBERT model, the authors should consider including a stronger learned detector trained on PrimeVul and a widely used semantic/static-analysis tool, such as LineVul and CodeQL.

6. The comparison between open-weight and frontier models is not fully symmetric because different reasoning modes and output-token budgets are used. In particular, the substantial improvement of Gemini under a larger reasoning budget suggests that budget-controlled and native/recommended inference settings should be evaluated and reported separately.

## Reviewer Detailed Comments
