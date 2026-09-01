# 12 — Representative-year consumption after redesign

**Type:** grilling

**Status:** ready-for-human

**Blocked by:** 05-method-registry-v1

## Question

Decide what representative-year calibration consumes from the redesigned reconstruction system.

Julia status quo (memory `core://agent/4`): rep-year calibration exists only in Julia — `Core.calibrate_to_representative_year` (2% threshold year selection), `apply_calibration` uses per-sector slopes from the 16-sector fit, no intercept. The 16-sector fit is trained but never used for reconstruction — dead weight except for rep-year.

Decide:

1. **Slope source**: keep Julia semantics — a deliberately-trained 16-sector fit feeding per-sector slopes — or re-derive calibration from the winning reconstruction method/fit?
2. **Calibration operator shape**: is rep-year calibration itself a method under the fit→predict contract (fit = slopes, predict = calibrated series), or a separate transform?
3. **Python gap**: Python currently has only config IR + on-the-fly report statistics (no calibrated series output) — what does the migrated version produce and persist?
4. **Migration semantics fidelity**: 2% threshold, no-intercept slope application — preserved as-is, or revisited while we're here?

## Acceptance

- [ ] Consumption design recorded under `## Answer`
- [ ] Consistent with ticket 05 registry outcome
- [ ] Map Decisions-so-far updated
- [ ] N/A — decision ticket, no code (verify_baseline not applicable)

## Comments

- 2026-08-31 (ticket 04): rep-year window selection policy is settled — coverage-driven: align all masts to the best common window when every mast has ≥90% clean-data availability there, else per-mast best-coverage; just-override for exceptions; the window must lie within the reconstructed extent (run-time validation, not a selection driver). Rep-year window is independent of report/wt-timeseries windows.
- 2026-09-01 (surfaced during ticket 05 grilling, user input): **Chinese 行标 rep-year procedure** differs from Julia semantics on three points: (1) global correction first — (meso observed-year mean − climatology mean), applied globally; (2) then a linear fit per 16 sectors; (3) then reduce — and sector grouping is by **mast direction**, not meso/source direction. v1 keeps Julia semantics (shared `horizontal.ws.ols-16sector` slopes); the 行标 two-stage procedure is a future calibration method — registry absorbs it additively (new horizontal variant id or a third `repyear.*` scope — decide here). Whether calibration methods benchmark at all, and how, is also this ticket's call. Note interplay with ticket 06's logged direction-field question: Julia-style sectors bin by source direction, 行标 bins by mast direction — the two cannot share one fit.
