# 09 — Feasibility screen

**Type:** grilling

**Status:** ready-for-human

**Blocked by:** None

## Question

Define the feasibility screen precisely (charted in ticket 01, decision 3: computed inside recommend; spans + counts; not a standalone product).

Decide:

1. **Inputs/outputs**: exactly what is computed per (method × source × target) — overlap span, fillable spans (target gaps coverable by source), counts, coverage ratios?
2. **Thresholds**: minimum overlap length, minimum fillable span, minimum correlation-at-screen? Which thresholds are config vs hard-coded?
3. **Which pairs are screened**: all (method × source × target) or only benchmark winners? Screening before or after reference-height selection (ticket 11)?
4. **Consumption**: how reconstruct reads the screen to skip pairs; behavior when config strategy overrides to a pair the screen rejected (warn? hard fail? allow with flag?).
5. **Back-reconstruction interaction**: a pair feasible only for a sub-range (the 2022–2023 vs 2025 case) — spans must express this; timerange from ticket 04.

## Comments

- 2026-09-01 (ticket 07, resolved): vertical exam-feasibility inputs for the screen — extrapolation exam requires ≥3 WS layers (hold out top, ≥2 below to fit shear); interpolation exam requires a qualifying middle layer inside `interpolation_exam_range` with brackets after hold-out; tall-mast "extrapolation not needed" is a derived exam-plan state the screen must express. Plus research R2's height-ratio guard (z_pred/z_obs ≲ 2, Kelly E-0121) for extrapolation targets.

## Acceptance

- [ ] Screen definition recorded under `## Answer`
- [ ] Consistent with tickets 04, 06, 11
- [ ] Map Decisions-so-far updated
- [ ] N/A — decision ticket, no code (verify_baseline not applicable)
