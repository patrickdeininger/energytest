# Reviewer 1 - Round 1

## Review Report Form

### Does the introduction provide sufficient background and include all relevant references?
Yes

### Is the research design appropriate?
Can be improved

### Are the methods adequately described?
Yes

### Are the results clearly presented?
Yes

### Are the conclusions supported by the results?
Can be improved

### Are all figures and tables clear and well-presented?
Can be improved

### English language and style
The English could be improved to more clearly express the research.

## Reviewer Major Comments
This is an interesting, relevant and generally well-written paper, and I think the combination of vulnerability-detection quality, monetary cost and energy use is a useful contribution.  The manuscript is also quite honest about the fact that the absolute performance of all models is still limited.

Still, I think some points need more attention before publication.

The main problem is that the comparison is not completely equal between all models: some models use reasoning and others do not, the output-token limits are not always the same, and most energy values are estimated while only two models were measured directly.

Because of this, the claims about energy dominance and the Pareto frontier are sometimes stronger than what the design can fully support. I suggest presenting separate comparisons for the same token budget, for the models’ normal configuration, and for their best-performing configuration.

Figure 2 should also show much more clearly which values are measured and which are estimated, preferably with uncertainty ranges. The authors should also be more careful when moving from API price to computational efficiency, because market price is not the same as real serving cost.

The discussion about realistic prevalence is important and should perhaps appear earlier, because precision of around 2-4% means that the models are still not ready for independent practical use . In general, I see a good paper here, but the main claims should be made more precise and the uncertainty around the energy estimates should be presented more directly. 

## Reviewer Detailed Comments
