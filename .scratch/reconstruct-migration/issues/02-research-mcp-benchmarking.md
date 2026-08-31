# 02 — Research: MCP benchmarking practice

**Type:** research

**Status:** resolved

**Blocked by:** None

## Question

Survey measure-correlate-predict (MCP) benchmarking practice from high-trust primary sources (peer-reviewed literature, IEC 61400-12 / MEASNET where accessible, reputable technical reports):

1. **Resampling design for wind time series**: block bootstrap / subsampling for autocorrelated wind data — recommended block lengths, fold counts, contiguous vs stratified blocks, exam-period sizing.
2. **Selection metrics**: WS RMSE vs energy/prediction-error-based metrics; role of bias guardrails; treatment of direction reconstruction quality.
3. **Method evidence**: variance-ratio vs OLS regression variants vs sectorized approaches — what does the evidence actually support for long-term correction?
4. **Long-record vs short-record evaluation conventions**: when is whole-series evaluation considered adequate?

Known starting points (from prior work, verify and deepen): Rogers, Rogers & Manwell 2005 (MCP method comparison, no dominant method); TU Delft 2023 MCP survey. Wind data is autocorrelated — row-level bootstrap is invalid.

Match recommendations to our charted protocol (ticket 01): monthly contiguous blocks, ≥5 folds, whole-series WS RMSE for ≥1yr & ≥90% availability, ε-group sort (ε=0.05 m/s) with bias secondary.

## Acceptance

- [ ] Findings captured at `.scratch/reconstruct-migration/research/mcp-benchmarking.md`, citing primary sources
- [ ] Concrete recommendations mapped to our protocol items; where literature contradicts a charted decision, say so explicitly
- [ ] Answer gist appended under `## Answer` here; Status → resolved; map.md Decisions-so-far updated
- [ ] N/A — research ticket, no code (verify_baseline not applicable)

## Answer

Findings at `research/mcp-benchmarking.md` (28 sources, incl. Rogers et al. 2005; Weekes & Tomlin 2014; Basse et al. 2021 WES; Jonietz Alvarez et al. 2024 WES; Sheridan et al. 2025 WES; Carta et al. 2013; IEC 61400-1 §11.3.4 / MEASNET / FGW). Gist: the charted protocol is evidence-aligned — contiguous blocking is the validated treatment for autocorrelated series and month-scale blocks match the seasonal dependence that dominates MCP error; whole-series evaluation for ≥1 complete year is the benchmarking convention (IEC/MEASNET/FGW 12-month norm); WS-RMSE + bias-secondary matches the literature's dual value-by-value/distribution evaluation with mean bias dominating energy error (~6× variance error); "no dominant MCP method" is the most replicated result, justifying benchmark-over-hardcode, with VR/OLS-residuals beating plain OLS only on distribution/energy metrics and VR able to amplify seasonal bias. No hard contradictions; two flagged tensions: (a) the ≥90% availability gate is stricter than gap-impact evidence warrants (FGW accepts 80%; 180-day gaps shift long-term mean <0.04 m/s) — conservative, MEASNET-aligned, keep but document an 80% acceptance option; (b) the 16-sector ≥5-point fallback is far more permissive than the ≥20-points-per-30°-bin literature precedent and sector fits degrade on short records — rely on the benchmark's 1-vs-16-sector contrast or raise the floor.
