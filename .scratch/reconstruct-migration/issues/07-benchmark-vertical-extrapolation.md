# 07 — Benchmark: vertical extrapolation (WS and WD)

**Type:** grilling

**Status:** resolved

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

## Answer

Decided 2026-09-01, user-confirmed (grilling, one round after a wait-what re-pitch):

1. **Command scope: one command, two ceremonies.** `benchmark-vertical` runs both exam types: extrapolation gets the full monthly blocked bootstrap; interpolation gets a light middle-layer hold-out spot-check (2 candidates, near-tie expected — interpolation error ≪ extrapolation error, research §5/R4). One vertical artifact seeds the fill-heights strategy config, which needs both a method per mode.
2. **Candidate matrix: already fixed by ticket 05's v1 cut** — 16 WS (`vertical.ws.extrapolate.powerlaw.<top3|dist-weighted|above50m|all>.<10min|1h|month|series>`), 6 WD (`vertical.wd.extrapolate.<global|sector>.<1h|month|series>`), 2 WS-interpolate laws, 1 WD-interpolate. No further trim here; the day-scale drop and log-law exclusion were settled in 05.
3. **Winner granularity (Q1): one winner per (mast × sensor type × mode).** The extrapolation winner is ranked on the top-layer hold-out exam; leave-one-out exams at other eligible layers (≥2 layers below) run and are recorded as diagnostics only. Per-(mast × target height) rejected: every above-top target collapses onto the same top-layer exam, so the finer granularity has no examable evidence — it would only bite between layers, which is interpolation's domain. (Research R2 leaned per-target-height; resolved in favor of what the exam can actually evidence.) Vocabulary: "variable" renamed **sensor type** (`CONTEXT.md` updated; method ids unchanged — the segment values were always `ws`/`wd`).
4. **Exam mechanics.** Extrapolation exam: hold out layer h, train on layers strictly below h, predict h; monthly blocked folds per tickets 01/06. The WD exam holds out the top **WD** layer (WD sensors sit at their own heights — never assumed to match WS), reference direction = the next WD layer below, per-sector offsets = 16 sectors of the reference direction, `min_points_per_sector` = 20 (ticket 05).
5. **Derived exam plan (per mast).** The benchmark derives which modes each mast needs by comparing configured target heights against the observed layer inventory: any target above the top observed layer → extrapolation exam (requires ≥3 WS layers: hold out top, ≥2 below to fit shear); all targets bracketed (e.g. a lidar mast taller than the ~160 m hub) → extrapolation **not needed**, no exam. The artifact distinguishes `not needed — default seeded` from `unbenchmarkable (<3 layers) — default seeded`, so the reviewer sees *why* no winner exists.
6. **Defaults seeded wherever no exam crowns a winner** (not needed or unbenchmarkable): WS extrapolate `vertical.ws.extrapolate.powerlaw.all.series`; WD extrapolate `vertical.wd.extrapolate.global.series`; WS interpolate `vertical.ws.interpolate.powerlaw` (规范-consistent — the same rule that excluded log-law from v1; log-linear stays a benchmarked candidate where an exam exists); WD interpolate `vertical.wd.interpolate.circular`. Defaults still land in the strategy config even when extrapolation is "not needed": fill works per timestamp, and lidar high-layer dropouts make extrapolation necessary at partial-missing timestamps. When it never fires it costs nothing.
7. **Interpolation exam range.** `interpolation_exam_range` (required benchmark-config field, [low, high] in meters, seeded `[125.0, 160.0]` by recommend): only middle layers inside the range that keep bracketing sensors after hold-out serve as interpolation exam targets. No qualifying middle layer → no interpolation exam → default seed.
8. **Trimmable candidate sets.** Four required benchmark-config lists — `ws_extrapolate_candidates`, `wd_extrapolate_candidates`, `ws_interpolate_candidates`, `wd_interpolate_candidates` — seeded full by recommend, user-trimmable (e.g. a single-100 m mast drops layer-hungry schemes like `top3`). The artifact records the candidate list actually run, so the evidence trail shows the trim.
9. **WD metric and selection (Q2).** Wrapped-MAE primary — mean |wrap(θ−θ̂)| on (−180°, 180°], computed only over timestamps with **ws ≥ 3 m/s** (MEASNET §9.4 low-speed exclusion; below it the vane reading is unreliable and the direction carries no energy; filter source = nearest-in-height WS sensor to the WD layer). **No speed weighting** — it would make the fit a weighted circular mean and complicate training; deferred to the backlog. ε-group at **ε = 2°** (smaller gaps are below direction-sensor accuracy ≈ noise); circular-mean bias secondary; circular RMSE recorded as diagnostic. Offsets fitted as plain circular means, never arithmetic means of raw angles. WD is selected **independently** of WS — veer error and shear error do not trade off, and no literature supports a joint objective (research R3).
10. **Boundary composition (Q3): per-timestamp routing by availability, not a fixed height boundary.** At timestamp t, for target height z: if an **observed** layer exists above z → interpolate between the bracketing observed layers; otherwise → extrapolate, **anchored at the highest observed layer below z at t** (u_pred(z) = u_anchor·(z/z_anchor)^α-style). The top measured layer itself is always extrapolation territory — nothing above it can interpolate it (user correction to the initial "targets above the top sensor" framing). The anchor moves with availability (top sensor missing at t → anchor drops to the next observed layer below). **Filled values never anchor** — an above-top target and a missing top sensor at the same timestamp both extrapolate from the same observed layer below; no error cascade, clean provenance. When the top sensor is observed, the prediction equals it at z = z_top — continuous at the seam by construction. No blend zone (no literature anchor; a third mechanism to validate). Exam consistency: the top-layer hold-out exam is exactly the "fill the top layer from below" task, so the seam case is covered by the benchmark evidence.
11. **P90|bias| diagnostic (Q5).** Recorded per candidate per sensor type in the artifact alongside the per-fold RMSE/bias table (Quick et al. 2025: MAE/RMSE alone don't reward longer records). Computation: per fold, `bias_f = mean(predicted − observed)` over the exam month's timestamps (wrapped signed degrees for WD, same ws < 3 m/s exclusion); then P90|bias| = 90th percentile of |bias_f| across folds, nearest-rank, no interpolation. Reads as "in 90% of exam months the systematic error stays within ±X" — a stability-across-seasons check. It informs the human's review of the seeded config; the decided ε-group sort is untouched (with the 5-fold minimum, nearest-rank P90 ≈ the worst fold — too coarse to sort on).

Routings: interpolation method-set detail (WD wraparound spec, per-interval artifact shape) stays with ticket 08; screen feasibility inputs (≥3 WS layers for extrapolation exam, qualifying middle layer for interpolation exam, research R2's height-ratio guard z_pred/z_obs ≲ 2) feed ticket 09.

## Acceptance

- [x] Candidate matrix + exam design recorded under `## Answer`
- [x] Winner granularity decided
- [x] Map Decisions-so-far updated
- [x] N/A — decision ticket, no code (verify_baseline not applicable)

## Comments

- 2026-08-31 research (ticket 03, `research/shear-validation.md`) sharpens this ticket: WS matrix trimmed 20→16 (drop the day scale; keep all 4 layer schemes); **law-family (power-law vs log-law) is a missing candidate dimension** to add; WD candidates = {global, per-sector} × {1h, month, whole-series} circular veer offsets, metric = wrapped-MAE; hold-out-layer exam is MEASNET-sanctioned "vertical cross-prediction". Tension flagged: log-law evidence vs MEASNET power-law mandate.
