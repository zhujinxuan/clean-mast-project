# 06 — Benchmark protocol: cross and meso selection

**Type:** grilling

**Status:** resolved

**Blocked by:** None

## Question

Finalize the cross/meso source-and-method selection benchmark beyond the charted baseline (ticket 01: ≥1yr & ≥90% availability → whole-series WS RMSE; otherwise monthly blocked bootstrap, ≥5 folds, exam = 1 month; ε-group sort with ε=0.05 m/s, bias secondary, power RMSE only with configured reference curve, coverage tertiary).

Open details:

1. **Heights of interest for the ≥90% availability rule**: which heights count — config analysis heights, all WS/WD heights of interest, per-mast? Where is this defined?
2. **Fallback chain**: meso sources grouped by dataset (ERA5/MERRA2) → ranked within group → primary + fallback chain (fixes Julia's single-meso-no-fallback hole). Is mixed-source fallback (different meso datasets in one chain) acceptable? Provenance mechanism already exists.
3. **Cross-mast priority score**: Julia uses 0.6·corr + 0.2·dir + 0.2·coverage to pre-rank ordered mast pairs. Keep as a screening pre-rank, or replace with benchmark-derived ranking entirely?
4. **Fallback chain ranking**: same ε-group sort as primary selection, or simpler (availability-weighted)?
5. **Benchmark evidence persistence**: what is kept — fold metrics table, winner summary, per-fold fits (charted: discarded)? Where does it surface — recommend output artifact, report section?

Context: memory `core://agent/4` (O(n²) sources, Julia priority score, merge semantics). Research ticket 02 may sharpen metric choices.

## Answer

Decided 2026-09-01, user-confirmed (grilling round run jointly with ticket 11):

1. **Single protocol.** Blocked subsampling (monthly contiguous blocks, exam = one month per fold, fold rules per ticket 01 §4) for ALL records, any length, any availability. The whole-series path is removed (ticket 01 §4 amendment). No availability-switched protocol fork; a minimum-availability threshold, if kept at all, is a screen threshold — ticket 09's question.
2. **Pre-rank: WS-only.** Plain WS RMSE on the subsampled WS-reference-height pair, cut at `top_k` (required config, recommend seeds 5). Candidate count ≤ `top_k` → no pre-rank, everything benchmarks. WD candidates inherit the WS cut (a good WS pair is almost always a good WD pair); the per-pair feasibility screen still gates the WD track. Julia's `0.6·corr + 0.2·dir + 0.2·coverage` priority score is dropped entirely. Complexity: O(masts + methods × K).
3. **Benchmark proper.** Per variable (WS, WD), each at its own reference height (ticket 11), over the pre-rank survivors. ε-group sort: WS RMSE ascending, adjacent gap < ε = 0.05 m/s groups, bias secondary, power RMSE only with a configured reference curve, coverage tertiary (ticket 01 §5, unchanged).
4. **Winner, no chain.** Each mast associates with exactly one meso source — the benchmark winner; different masts may use different datasets. Fallback chains are rejected (meso datasets are often of equal quality). The Julia single-meso-no-fallback hole is a deliberate choice. Run-phase config carries a single source ref; no `fallback_count`, no chain ref anywhere.
5. **Benchmark is its own phase.** Two commands — `benchmark-horizontal`, `benchmark-vertical` — each with its own config TOML, both seeded by recommend. Recommend is metadata-only (sensor heights, meso inventory). The feasibility screen runs inside the benchmark command (ticket 01 §3 amendment). All defaults are materialized by recommend into required config fields — no optionals, no runtime fallback defaults.
6. **Benchmark artifact.** One TOML per benchmark run: screen table (fillable spans + counts per pair), per-candidate fold metrics (RMSE + bias per fold, per variable), winner summary. Fold fits are discarded (ticket 01 §10). Surfaced as a file in the project output, read directly by the user when reviewing the seeded run config. Not a report section — reporting is out of scope.
7. **Meso↔mast temporal alignment.** Training aligns on the coarser meso hourly grid: mast 10-min aggregated to hourly (WS arithmetic mean, WD vector mean). Predict/fill runs at mast 10-min via up-front linear interpolation of the meso series, then apply the fit (commutes for the linear/piecewise-linear v1 methods). 16-sector assignment uses the meso (source) WD — at predict time only the source direction exists; preserves Julia parity. The 行标 mast-direction variant is ticket 12's additive method.

## Acceptance

- [x] Full protocol recorded under `## Answer`, implementable without further decisions
- [x] Interactions with tickets 09 (screen) and 11 (reference height) consistent
- [x] Map Decisions-so-far updated
- [x] N/A — decision ticket, no code (verify_baseline not applicable)

## Comments

- 2026-08-31 research (ticket 02, `research/mcp-benchmarking.md`): the charted ≥90% availability gate is stricter than gap-impact evidence requires — FGW 80% is a documented option. Decide whether the gate is config (default 90%, 80% option) rather than fixed.
- 2026-08-31 research (ticket 03, `research/shear-validation.md`): Quick-2025 cautions on RMSE-based selection — read the flagged tension before locking the ε-group sort's primary metric.
- 2026-09-01 (surfaced during ticket 05 grilling): **meso↔mast temporal alignment rule** needs deciding here — training aligns on the coarser (meso hourly) grid; prediction/fill runs at mast 10-min resolution via up-front linear interpolation of the meso series (valid because OLS/VR/16-sector are linear-or-piecewise-linear, so interpolation commutes with prediction). Open details: which direction field drives 16-sector assignment (meso WD vs mast WD), aggregation statistic for mast→hourly.
- 2026-09-01 (grilling round, user decisions): **benchmark is its own phase — two commands, two configs.** `benchmark-horizontal` + `benchmark-horizontal.toml`; `benchmark-vertical` + `benchmark-vertical.toml`. Recommend seeds both and stays metadata-only (sensor heights, meso inventory). Each command writes its own benchmark artifact; the horizontal artifact seeds the run-phase strategy config, the vertical artifact seeds the fill-heights strategy. Rationale: the two benchmarks differ in selection unit, exam design, anchor, inputs, winner granularity, and pipeline timing (vertical needs only clean mast data — unblocks reconstruct-single/fill-heights earlier). Shared protocol machinery (blocked bootstrap, ε-group sort, bias secondary) lives in library code and recommend-seeded config values, not in the CLI.
- 2026-09-01: **ticket-01 amendment.** The feasibility screen (ticket 01 §3, "computed inside recommend") moves into the benchmark command. Recommend no longer touches data overlaps; screen fillable spans are recorded in the benchmark artifact, where they gate which pairs get benchmarked.
- 2026-09-01: **no-optional-fields principle applies to benchmark config.** ε, top_k, min_availability, fallback_count, fold rules are all required config fields, seeded by recommend (seed values pending confirmation of Q4/Q5/Q8).
- 2026-09-01 (Q4+Q7, user decisions): **Julia priority score dropped entirely** — not even as pre-rank; `0.6·corr + 0.2·dir + 0.2·coverage` is too complex for what it buys. Pre-rank instead: **subsampling-based WS RMSE** over all candidates, take top 5 (`top_k` required config, seeded 5). If the candidate count ≤ top_k, no pre-rank — everything goes to the full benchmark. Complexity: O(masts + methods × K).
- 2026-09-01 (user): **single-protocol amendment (ticket 01 §4).** Blocked subsampling is the golden standard for ALL records — no whole-series path, no availability-switched protocol fork. Consequence: the ≥90% availability gate loses its protocol-switch role; whether a minimum-availability threshold survives as a *screen* threshold moves to ticket 09.
- 2026-09-01 (Q4a, user decision): **pre-rank is WS-only.** One subsampling engine: pre-rank = plain WS RMSE sort on the subsampled WS-reference-height pair, cut at `top_k` (seeded 5); no ε-group, no bias secondary, no WD pre-rank. Rationale: a good WS mast pair is almost always a good WD mast pair — WD candidates inherit the WS pre-rank cut. The full benchmark (ε-group sort, bias secondary) runs per variable at its own reference height on the survivors.
- 2026-09-01 (Q6+Q8, user decision): **no fallback chains — rejected.** Each mast associates with exactly one meso source (the benchmark winner); different masts may associate with different datasets. Rationale: meso datasets are often of equal quality, so a chain buys little. The Julia single-meso-no-fallback hole is accepted as a deliberate design choice, not an oversight. Consequences: Q6 (mixed-source chains) and Q8 (chain ranking) are moot; the `fallback_count` config field is deleted from the design; the benchmark artifact records a winner, not a chain; ticket 13's reconstruction-set config carries a single source ref, no chain ref.
- 2026-09-01 (Q10, user decision): **meso↔mast temporal alignment settled.** Training aligns on the coarser meso hourly grid: mast 10-min data aggregated to hourly (WS arithmetic mean, WD vector mean). Predict/fill runs at mast 10-min resolution via up-front linear interpolation of the meso series, then apply the fit (valid: OLS/VR/16-sector are linear or piecewise-linear, so interpolation commutes with prediction). 16-sector assignment uses the meso (source) WD — at predict time only the source direction exists; this also preserves Julia parity. The 行标 mast-direction variant is ticket 12's additive method.
