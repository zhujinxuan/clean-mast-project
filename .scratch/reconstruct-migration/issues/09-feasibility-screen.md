# 09 — Feasibility screen

**Type:** grilling

**Status:** resolved

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

## Answer

Decided 2026-09-02, user-confirmed (grilling, two rounds):

1. **Granularity and record schema.** The screen is method-independent **data geometry** — one row per (source × target × sensor type), computed at that sensor type's reference height. It never fits anything and contains no skill metric (correlation/RMSE); method comparison belongs to the pre-rank and benchmark proper (ticket 06). Recorded per pair: `overlap_spans` (list of TimeRange, source ∧ target both observed), `overlap_count`, `fillable_spans` (target missing ∧ source observed, list of TimeRange), `fillable_count`, `target_availability` (informational only), and `verdict` ∈ {`benchmarkable`, `forced`, `unbenchmarkable(<reason>)`, `no-fill-value`}. The vertical artifact reuses the same table shape plus ticket 07's exam-plan states; the vertical screen inputs are ticket 07's ladders (≥3 WS layers for an extrapolation exam; the WD 3/2/1-layer ladder; qualifying middle layer for interpolation) plus the height-ratio guard (§6).
2. **Benchmarkability thresholds.** A pair is `benchmarkable` iff ≥5 **valid folds** derive from the overlap; a fold is valid iff source ∧ target are jointly observed ≥ `min_fold_coverage` (required field, seeded 0.5) of its timestamps. `min_overlap_months` is a required field with **default 0** — short masts stay pairable; fold coverage, not record length, gates pairability. Recommend seeds 5 only when every configured target mast's clean-series span exceeds 8 months (metadata-only heuristic, evaluated per benchmark run), else 0. Accepted consequence: with the floor at 0, a ~3-week overlap benchmarks on ~4-day folds — the fold-metrics table makes short-exam noise visible.
3. **No availability gate.** `min_availability` dies as a config field (it was a planned field in ticket 06's no-optional list; deleted before ever existing). Availability survives only as the informational `target_availability` column. Fold coverage (§2) is the real training-quality guard — per ticket 02's gap-impact evidence (30-day gap ≈ 0.01 m/s; FGW 80% precedent), a whole-record percentage gate buys nothing the folds don't already measure.
4. **No fill without benchmark evidence; forcing lives in the benchmark config.** Recommend seeds strategies only for screen-passing pairs. `benchmark-horizontal.toml` carries `forced_pairs` (source ref + target mast + sensor type; seeded empty by recommend): a listed pair enters pre-rank + benchmark regardless of verdict. Forcing bypasses the **gate, not the computation** — the screen still records the pair's full geometry (fill reads the persisted fillable spans at run time), and the verdict reads `forced` so the evidence trail shows what was insisted on. Hard boundary: **zero-overlap pairs stay unbenchmarkable regardless** — no fit is possible without concurrent timestamps. **Amends ticket 04 §3**: the run-phase `screen-override` flag shrinks to method-level overrides (picking a non-winner method on a benchmarked pair, already legal under "benchmark recommends, config decides"); pair-level forcing now happens before the benchmark, so every fill is evidence-backed.
5. **Forced-benchmark mechanics.** Forced pairs keep the 5-fold derivation but **drop the fold-coverage requirement** — every fold scores whatever data it contains; the candidate is marked `forced` with per-fold coverage recorded alongside its metrics. One fold-derivation path, no forced/normal fork. The 5-fold seasonal spread is preserved (that spread is where the evidence value lives); sparse-fold noise is visible in the recorded metrics.
6. **Vertical height-ratio guard.** Above-top targets with z_pred/z_obs > `max_extrapolation_height_ratio` (required field in `benchmark-vertical.toml`, **seeded 2.0 and user-tunable** — 160m-from-100m = 1.6 passes; larger reaches are a config decision, not a code change) are marked `unfillable-by-vertical`, recorded per target height; fill skips them at run time (such heights can still be served horizontally). Interpolation carries **no** ratio guard — the σ_rep ∝ α·ln(z_pred/z_obs) term grows only outside the measured span (Kelly E-0195).
7. **Placement and timing.** One screen engine (span arithmetic, fold derivation, verdicts) lives in **dataprocessing**, consumed by both benchmark commands; `shared/reconstruction/` stays contract-types-only. The screen runs **at benchmark execution time, first**, before the pre-rank — recommend never reads series data. Both benchmark commands get a `--screen-only` preview mode (screen table written, pre-rank/folds skipped) for iterating on thresholds and `forced_pairs` before paying for fits. fill-heights' `check_min_overlap` is subsumed by the engine and deleted when it lands — one overlap convention, not two.

## Acceptance

- [x] Screen definition recorded under `## Answer`
- [x] Consistent with tickets 04, 06, 11
- [x] Map Decisions-so-far updated
- [x] N/A — decision ticket, no code (verify_baseline not applicable)
