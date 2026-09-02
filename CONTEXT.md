# CleanMast

Wind energy meteorological tower (mast) data processing toolkit: from raw logger files to bankable wind resource assessment report.

## Language

**Mast**:
A meteorological measurement tower; the primary observation unit. A mast *entity* spans exactly one contiguous observation period: one raw file ↔ one entity, and a re-deployment after a gap is a separate entity. No naming convention links sibling entities.
_Avoid_: tower (ambiguous with turbine tower), station

**Sensor**:
A named measurement channel on a mast, with metadata (height, type, statistic). Never pattern-match raw column strings. On tower masts, wind-speed and wind-direction sensors are typically mounted at *different* heights to avoid mutual interference — never assume a WS height implies a WD sensor at the same height.
_Avoid_: column, channel (bare)

**Sensor type**:
The quantity a sensor measures; part of its metadata. Reconstruction distinguishes wind speed (`ws`) and wind direction (`wd`) — this is the second segment of a method id. Short forms (`ws`/`wd`) in ids and config, full names in prose.

**Experiment**:
A full CleanMast run from preprocessed mast/meso data to report.

### Reconstruction

**Method**:
A named reconstruction algorithm identified by id in config, benchmark records, and fit artifacts (e.g. `horizontal.ws.ols-16sector`). Refers to the algorithm only, never a trained object. Ids follow the grammar `<scope>.<sensor-type>.<algorithm>[.<variant>...]` with closed per-segment vocabularies; candidate-matrix dimensions (law family, layer scheme, time scale) are id segments, while per-method tuning knobs stay params. Ids are add-only — never renamed or removed.
_Avoid_: model (reserved for Pydantic config IR)

**Horizontal**:
The method scope for series→series reconstruction across locations: cross-mast and meso→mast share it (same algorithms; the source kind is a property of the reconstruction set, not the id). MEASNET's "horizontal cross-prediction between different masts".

**Vertical**:
The method scope for reconstruction across heights within one mast — interpolation between measured layers, extrapolation above the top layer. MEASNET's "vertical cross-prediction between different measurement heights".

**Mode**:
The split of vertical method families by target position relative to the observed layers: **extrapolate** (no observed layer above the target) and **interpolate** (observed layers bracket the target). Routing is per timestamp, by availability: the top measured layer itself is always extrapolation territory. Winner granularity is per (mast × sensor type × mode).

**Fit**:
A trained artifact produced by fitting a method to a source×target pair over a timerange; persisted as TOML. Follows the `FillHeightFitResult` precedent. Config references it by identity (method + refs + training overlap); an explicit-artifact mode (direct path + column mapping) exists for ad-hoc transfers. A method is **fit-free** when predict re-derives everything from observed data at predict time (e.g. per-timestamp two-point interpolation) — no artifact is trained, persisted, or cached for it.
_Avoid_: model, trained model

**Fit transfer**:
Applying a fit trained for one source×target pair to a different pair via the explicit-artifact mode, with a column mapping between sensor setups. Flagged `fit-transferred` in provenance; never benchmark-recommended.

**Predict**:
The operator `fit × source data × timerange → full synthetic target series`, independent of observed target values. Emits a partial series under partial source coverage; predicting outside the training overlap is allowed, flagged `extrapolated-in-time`.

**Fill**:
The operator `fit × source × observed target × timerange → target series with gaps filled`. Strict intersection: target missing ∧ prediction exists ∧ inside the feasibility screen's fillable spans. Missing-only; never overwrites observed; unfeasible cells skipped without computing.

**Working window**:
The per-mast `TimeRange` bounding one reconstruction phase's fill domain for that mast. Derived as fillable spans ∩ the planned window unless declared explicitly; never per-pair.

**Planned window**:
The explicitly chosen reconstruct-meso output window — a deliberately sized subset of meso availability, independent of report and wt-timeseries windows.

**Reconstruction set**:
One configured reconstruction job: source, target, method, timerange, heights. The unit of run-phase strategy; config carries an explicit strategy per set.

**Feasibility screen**:
The benchmark-stage computation of which (method × source × target) pairs can reconstruct anything, recorded as fillable spans + counts in the benchmark artifact. Infeasible pairs are skipped downstream; fill reads the persisted spans at run time.

**Benchmark**:
The selection procedure ranking (source × method) candidates: monthly blocked bootstrap (contiguous blocks, exam = one month per fold) — the single protocol for all records, regardless of length or availability. The winner seeds the recommended strategy; it is not the mandate. Runs as its own phase: `benchmark-horizontal` and `benchmark-vertical` commands, each with its own config, seeded by recommend.

**Exam**:
The hold-out validation inside a benchmark. Horizontal exams withhold a time block (the monthly fold); vertical exams withhold a measurement layer — the top layer for extrapolation, a middle layer for interpolation (MEASNET's vertical cross-prediction). **Train/predict consistency**: an exam replays the production fit/predict geometry exactly — same method, fit rule, layer scheme, and weighting — with the held-out layer or block as the target; no exam-specific fitting paths. A per-mast exam plan (which modes run) is derived from configured target heights vs the observed layer inventory; where no exam can crown a winner, the family default is seeded instead.

**Provenance flags**:
An append-only categorical column `{sensor}_flags` per reconstructed sensor. Grammar: origin flag first (`observed`|`missing`, never removed), then phase flags appended in fixed pipeline order (`clean` < `single` < `cross` < `meso` < `rep-year`), colon-joined, no leading colon. Created on demand by the single append-only writer API. Until the data-clean migration lands, a transitional `mint-flags` command (recommend → config → run) mints them into clean parquets in place — raw is never edited; raw-unavailable degrades to `observed`/`missing`. Readers tolerate missing origins on older outputs.

**Provenance manifest**:
A per-run TOML beside the output parquet: per sensor, filled spans → method, source, fit key, override flags. The audit layer for human overrides of benchmark recommendations.
_Avoid_: sidecar CSV (Julia's write-only per-point export — does not migrate)
