# Critical self-review of the draft (Stage 3, reviewer's-eye)

Purpose: anticipate the strongest objections a Computers/efficiency reviewer will raise on `main.tex`, ranked by severity, with the fix.

## Major concerns
1. **Energy — the headline axis — is ESTIMATED, not measured.** [most serious]
   The open-vs-frontier energy claims rest on FLOP-based estimates with an *assumed* ~100B active-param figure for frontier models. A reviewer will not accept "1/40th the energy" as a measured result. **Fix (highest value): run the M3 measured-energy pass** on a rented GPU for the local-feasible open models (Gemma-3-4B, Qwen3-Coder-30B, Llama-3.3-70B) via vLLM + NVML. That converts the open side from estimated → measured and makes the energy contribution defensible. The harness already implements it (~$20-80, ~half a day).

2. **Token-budget asymmetry between the 5 first-run and 3 fill models.** The 3 reasoning models used max_output_tokens=256 vs 64. It's conservative (they're the efficiency losers) but a reviewer will flag unfairness. **Fix:** re-run all 8 at a single consistent cap (folds naturally into a clean consolidated run), or foreground-chunk a consistent re-run.

3. **Single dataset, single task, N=1549.** Generalizability is thin. **Fix:** add SecVulEval (already wired into the loader) as a second dataset, and/or add a language beyond C/C++. At minimum, frame scope explicitly (already partly done in Limitations).

4. **All models near chance (0.50–0.63).** A skeptic will ask whether a comparison among near-chance models is meaningful. **Fix / framing:** lead with (a) the *relative* ordering being stable and open-favoring, (b) efficiency being the real contribution, and (c) PrimeVul's documented hardness. Consider adding a majority-class baseline and a random baseline to the table for grounding.

## Moderate concerns
5. **Latency measured under concurrency=10** = service latency, not model speed. **Fix:** the concurrency=1 latency pass (~$1-2, quick).
6. **"Open beats frontier" leans on DeepSeek-V3.2 and Gemma-3-4B.** DeepSeek-V3.2 is open-weight but very large (not truly "small/local"). The cleanest, most defensible instance is **Gemma-3-4B > Claude-Sonnet-5** — lead with that; present DeepSeek as "the strongest open model overall."
7. **No statistical testing.** Add 95% CIs (±~2.5% at N=1549) and a paired McNemar test between the top open and top frontier model to show the gap is significant.
8. **Direct-mode choice needs justification.** Explain why direct (single-shot classification) is the right primary lens, and position reasoning as the deferred axis.

## Minor
9. Figures: the auto-generated Pareto PNGs are functional but not publication-grade; regenerate with clear open/frontier coloring + labels.
10. Author/affiliation/ORCID placeholders remain.
11. Add a DURC/responsible-use note (defensive framing; benchmark consumes public data, releases no exploits) even though detection is low-sensitivity.

## Verdict
The core result is real and compelling, and the draft is honest about its limits. The paper is currently at **"strong workshop / weak journal"** strength. The single change that most raises it to solid-journal strength is **#1 (measured energy)**; **#2, #5, #7** are cheap and high-return. #3 is the larger investment that would make it robust.
