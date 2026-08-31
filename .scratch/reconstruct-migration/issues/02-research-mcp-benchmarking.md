# 02 — Research: MCP benchmarking practice

**Type:** research

**Status:** claimed

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
