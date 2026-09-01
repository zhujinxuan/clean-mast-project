# 01 — Charting decisions

**Type:** grilling

**Status:** resolved

**Blocked by:** None

## Question

Settle the baseline decisions for this map, from the 2026-08-31 charting round (building on the 2026-08-28 design discussion in memory `core://agent/4`).

## Answer

Decided 2026-08-31, user-confirmed:

1. **Destination/scope**: decision-complete design for the reconstruction migration; data-clean out, report rendering out, Julia frozen; representative-year in scope only as a consumer of the new fits.
2. **Naming**: **method** = algorithm id; **fit** = trained TOML artifact (follows `FillHeightFitResult` precedent); operators **fit() / predict() / fill()**. "Model" stays reserved for Pydantic config IR. Fill-heights is unified into the same fit→predict contract — no separate vertical machinery.
3. **Feasibility screen**: computed inside recommend; recorded as fillable spans + counts in the recommendation artifact; not a standalone persisted product; reconstruct consumes it to skip hopeless pairs.
4. **Short-record benchmark**: contiguous monthly blocks; exam = one month per fold; folds = each month (≤12) when overlap ≥12 months, else ≥5 equal contiguous folds; train = complement. Never row-level resampling (autocorrelation).
5. **Selection sort**: sort by WS RMSE ascending; group candidates where adjacent RMSE gaps < ε (ε = 0.05 m/s); within a group, sort by secondary criterion. Secondary = WS bias by default; wind-power RMSE only when a reference turbine curve is configured; coverage tertiary. Chaining caveat (A≈B≈C across a group) accepted — grouping is by adjacent gaps, order within group is well-defined.
6. **Vertical methods**: per (variable × mode) families — WS-extrapolate, WS-interpolate, WD-extrapolate, WD-interpolate. Interpolate ≠ extrapolate; interpolation shear may differ per height interval. Same families serve reconstruct-single and both fill-heights pipeline points (one selected fit per mast, missing-only fill).
7. **Train-on-demand + cache**: deterministic fit cache keyed by (method, source, target, timerange, config hash); no separate train command; "train in advance" = running reconstruct once.
8. **Map location**: `cleanmast-developing/.scratch/reconstruct-migration/`.
9. **Benchmark recommends, config decides**: the run-phase config carries an explicit strategy per reconstruction set; the benchmark winner is the seeded default, user-overridable.
10. **Production fits retrain on full data**: fold fits from bootstrap benchmarking are benchmark evidence only — never averaged, never production artifacts. Same rule for the whole-timeseries selection path (which has no folds anyway). One canonical fit per (method, source, target, timerange).

Veto procedure: comment on this ticket and reopen (Status: ready-for-human) if any decision needs revisiting.

## Amendments

- 2026-09-01 (user): **decision 3 amended** — the feasibility screen is not computed inside recommend. It runs inside the `benchmark-horizontal` / `benchmark-vertical` commands (benchmark became its own phase, two commands + two configs; recommend stays metadata-only). Screen fillable spans are recorded in the benchmark artifact. See ticket 06 comments.
- 2026-09-01 (user): **decision 4 amended** — the two-tier protocol is removed. No whole-series RMSE path for ≥1yr & ≥90% availability. **Blocked subsampling (monthly contiguous blocks) is the single golden standard for all records**, any availability. Rationale: one protocol to implement, validate, and read; subsampling is never wrong where whole-series would have been allowed.

## Acceptance

- [x] Decisions recorded above; map.md Decisions-so-far points here
- [x] Vocabulary captured in repo-root `CONTEXT.md`
- [x] N/A — decision ticket, no code (verify_baseline not applicable)
