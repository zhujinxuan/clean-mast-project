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
