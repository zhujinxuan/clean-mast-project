# 03 — Research: vertical shear validation practice

**Type:** research

**Status:** claimed

**Blocked by:** None

## Question

Survey vertical wind extrapolation/interpolation and its validation from high-trust primary sources:

1. **Hold-out-layer validation**: conventions for validating vertical extrapolation by withholding the top measurement layer (or a middle layer for interpolation); metrics used.
2. **Shear time variability**: how power-law α / log-law profiles vary by aggregation scale (10-min, 1h, day, month, whole-series) and by time of day / season / stability; evidence for which aggregation carries signal vs noise.
3. **Profile fitting**: distance-weighted shear profile fitting vs nearest-layers-only; minimum height thresholds (e.g. >50m) for excluding surface-layer distortion.
4. **Wind direction veer**: veer-with-height modeling (constant offset vs sectorized), circular statistics for direction error metrics.
5. **Interpolation between bracketing heights**: log-linear (in ln z) vs power-law two-point vs linear; when interpolation error matters.

Match recommendations to our charted candidate matrix (tickets 01, 07, 08): WS-extrapolate = 5 time scales × 4 layer schemes; WD-extrapolate = veer offsets; interpolation kept simple.

## Acceptance

- [ ] Findings captured at `.scratch/reconstruct-migration/research/shear-validation.md`, citing primary sources
- [ ] Concrete recommendations for the extrapolation matrix (trim or keep 20 candidates) and interpolation method set
- [ ] Answer gist appended under `## Answer` here; Status → resolved; map.md Decisions-so-far updated
- [ ] N/A — research ticket, no code (verify_baseline not applicable)
