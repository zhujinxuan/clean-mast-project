# 03 — Research: vertical shear validation practice

**Status:** resolved

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

- [x] Findings captured at `.scratch/reconstruct-migration/research/shear-validation.md`, citing primary sources
- [x] Concrete recommendations for the extrapolation matrix (trim or keep 20 candidates) and interpolation method set
- [x] Answer gist appended under `## Answer` here; Status → resolved; map.md Decisions-so-far updated
- [x] N/A — research ticket, no code (verify_baseline not applicable)


## Answer

Findings at `research/shear-validation.md` (5 survey sections + item-by-item recommendations, all claims cited to primary sources read directly where the network allowed: MEASNET v2/v3.1, IEC 61400-15-1:2025 FDIS + 61400-12-1:2017 previews, DTU reports Kelly E-0121/E-0195, Quick et al. 2025, Wagner et al. 2014/2011, Optis/Bodini, Crippa et al. 2021, Kelly & van der Laan 2023, Bao et al. 2010, windpowerlib/windkit docs). Gist:

1. **Hold-out-layer exam is normative practice**: MEASNET §8.4 sanctions "vertical cross-prediction between different measurement heights" — hold out the top layer for extrapolation, a middle layer for interpolation; metrics = bias + RMSE/MAE at 10-min per height; blocked/chronological folds only (Bodini & Optis 2020; Vassallo et al. 2021); no standards threshold exists (feeds uncertainty budget, not pass/fail).
2. **WS matrix: trim 20 → 16** — drop the "day" time scale (destroys the diurnal signal — the dominant documented α driver (Yang 2024; Yan 2022; Crippa et al. 2021: hour-of-day α beats constant α by 23–33% RMSE) — and has zero literature anchor); keep 10-min/1h/month/whole-series and all 4 layer schemes (each has a distinct anchor: MEASNET representativeness, Kelly E-0195 weights, >50 m surface-layer exclusion per Gryning 2007/Kelly & Troen 2016, all-heights control).
3. **Contradiction flagged**: peer-reviewed comparisons favor log-law over plain power law (Quick 2025; Bodini & Optis 2020; Optis et al. 2021) while MEASNET mandates the power-law kernel — register the law family as a method dimension or the benchmark can't detect it.
4. **WD-extrapolate**: {global, per-sector} × {1h, month, whole-series} constant circular offsets (6 candidates, no 10-min); metric = circular MAE on wrapped (−180°,180°] differences, offsets fitted as circular means; WD selected independently of WS.
5. **Interpolation kept simple**: log-linear in ln(z) default (windpowerlib/windkit default) + two-point power law as single benchmarked competitor via middle-layer hold-out; drop linear-in-z; per-interval parameters are normatively anticipated (MEASNET §9.4); interpolation error ≪ extrapolation error (Kelly E-0195 σ_rep ∝ ln(z_pred/z_obs) only outside span; Wagner 2014 ≤0.5% spread) — spot-check, no full bootstrap.

Feeds tickets 07 (matrix + exam + winner granularity evidence: per mast × target height) and 08 (method set + per-interval artifact + boundary routing).