# Reconstruct Migration — Wayfinding Map

## Destination

Decision-complete design for migrating wind-data reconstruction from Julia (`CleanMastProject/`, frozen, maintenance mode) to `packages/cleanmast`, replacing ad-hoc method selection with a benchmarked protocol. Pipeline per standard: data clean → reconstruct-single → reconstruct-cross → reconstruct-meso → representative-year calibration; fill-heights runs after meso and after rep-year, unified into the same fit→predict contract. Done = every decision ticket resolved and the way to implementation is clear; this map ships decisions, not code.

## Notes

- Domain: wind mast data reconstruction / MCP (measure-correlate-predict).
- **Read memory `core://agent/4` before working any ticket** — it holds the verified Julia ground truth (O(n²) sources, 16-sector training, rep-year calibration semantics, merge semantics) and the 2026-08-28 design discussion. Do not re-explore what it records.
- Key Julia sources (read-only reference): `CleanMastProject/src/TrainMeso/`, `CleanMastProject/src/RepresentativeYear/`, `CleanMastProject/src/WindSpeedModels/SectorizedRegressionTraining.jl`.
- Python landing zone: `packages/cleanmast` subdomains. Config IR already exists for reconstruct-meso and representative-year; fill-heights is the recommend/train/execute + TOML-artifact precedent (`FillHeightFitResult`).
- Constraints: dataprocessing must not import from reporting (subdomain isolation, `.importlinter`); fit artifacts are TOML, never JLD2; Pydantic `BaseModel` for all IR; read the co-located `spec.md` before designing any context's piece.
- Skills per ticket type: grilling → `grilling` + `domain-modeling`; research → `research`.
- Working agreement (user, 2026-08-31): implementation tickets change the context's `spec.md` **first**, then code.
- Vocabulary: repo-root `CONTEXT.md` (method / fit / predict / fill / reconstruction set / feasibility screen / benchmark). "Model" is reserved for Pydantic config IR.

## Decisions so far

- [01 — Charting decisions](issues/01-charting-decisions.md) — naming (method/fit/predict/fill), fill-heights unified into the contract, monthly blocked bootstrap, ε-group RMSE sort (ε=0.05), vertical 2×2 method families (WS/WD × interp/extrap), train-on-demand + fit cache, benchmark recommends but run-config strategy per reconstruction set decides, production fits always retrain on full data.
- [02 — Research: MCP benchmarking practice](issues/02-research-mcp-benchmarking.md) — charted protocol evidence-aligned (contiguous monthly blocks, 12-month/90% whole-series norm, WS-RMSE+bias-secondary, no dominant MCP method); two flagged tensions: ≥90% availability gate stricter than gap-impact evidence (FGW 80% option), 16-sector ≥5-point fallback vs literature ≥20-per-bin precedent.
- [03 — Research: vertical shear validation practice](issues/03-research-shear-validation.md) — hold-out-layer exam is MEASNET-sanctioned "vertical cross-prediction"; WS matrix trimmed 20→16 (drop day scale, keep all 4 layer schemes); law-family (power vs log) flagged as a missing method dimension; WD = {global, per-sector} × {1h, month, whole-series} circular offsets with wrapped-MAE; interpolation = log-linear default + two-point power-law competitor, per-interval params, spot-check only.
- [04 — Operator contract and timerange semantics](issues/04-operator-contract-timerange.md) — partial-series predict; mast entity = one contiguous span (two files → two entities, no naming convention, no site concept); strict-intersection fill; per-mast working windows with explicitly-chosen long meso window and coverage-driven rep-year window; provenance = append-only `{sensor}_flags` columns (minted at clean stage) + per-run span manifest, replacing Julia's dead sidecar CSV; config carries fit identity only (parameters live in the artifact); two reference modes (identity default, explicit-artifact for ad-hoc transfers).

## Not yet specified

- Parallelism/performance design of final fitting and full-series prediction at scale (depends on contract + cache shape).
- GuessMast / multi-mast synthesis interaction with the new fits.
- What benchmark evidence persists and where it surfaces (fold metrics table? plots? recommend output? report section?).
- WD benchmark detail beyond candidate methods (sector-stratified veer? circular metric choice) — partially ticketed in 07, may grow.

## Out of scope

- Data cleaning — cleaning *logic* exists upstream, unchanged. Exception (ticket 04): the clean-stage output schema gains the append-only `{sensor}_flags` columns; the writer change is additive, no cleaning rules change.
- Report rendering / reporting-side statistics migration.
- Julia-side changes — `CleanMastProject/` is frozen.
- Non-reconstruction subdomains.
