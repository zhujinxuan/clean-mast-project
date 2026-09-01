# 07 — Benchmark: vertical extrapolation (WS and WD)

**Type:** grilling

**Status:** claimed

**Blocked by:** None

## Question

Finalize the extrapolation candidate matrix and exam design for WS-extrapolate and WD-extrapolate.

**WS candidates** (user-charted): 5 time scales (10-min, 1h, day, month, whole-series) × 4 source-layer schemes (topmost nearest 3, distance-weighted shear profile fitting, all >50m, all heights) = 20 candidates. Trim or keep? Shear fits are cheap, so cost is not the constraint — interpretability of the benchmark record might be.

**WD candidates**: constant veer offset — at which time scales; global vs per-sector-of-reference-direction; circular error metric (degrees).

**Exam design**: hold out the top WS/WD layer, train on the rest, monthly blocked bootstrap (same protocol as ticket 06). Decide:

1. Winner granularity: one winner per mast, or per (mast × target height)?
2. WD metric: circular RMSE vs circular MAE; how WD quality weighs against WS in a combined vertical strategy (or are WS and WD selected independently)?
3. How the winning extrapolation fit composes with interpolation (ticket 08) at the boundary layer (top measurement).

Context: ticket 01 decisions 4–6; research ticket 03 may trim the matrix.

## Acceptance

- [ ] Candidate matrix + exam design recorded under `## Answer`
- [ ] Winner granularity decided
- [ ] Map Decisions-so-far updated
- [ ] N/A — decision ticket, no code (verify_baseline not applicable)

## Comments

- 2026-08-31 research (ticket 03, `research/shear-validation.md`) sharpens this ticket: WS matrix trimmed 20→16 (drop the day scale; keep all 4 layer schemes); **law-family (power-law vs log-law) is a missing candidate dimension** to add; WD candidates = {global, per-sector} × {1h, month, whole-series} circular veer offsets, metric = wrapped-MAE; hold-out-layer exam is MEASNET-sanctioned "vertical cross-prediction". Tension flagged: log-law evidence vs MEASNET power-law mandate.
