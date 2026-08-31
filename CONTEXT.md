# CleanMast

Wind energy meteorological tower (mast) data processing toolkit: from raw logger files to bankable wind resource assessment report.

## Language

**Mast**:
A meteorological measurement tower; the primary observation unit.
_Avoid_: tower (ambiguous with turbine tower), station

**Sensor**:
A named measurement channel on a mast, with metadata (height, type, statistic). Never pattern-match raw column strings.
_Avoid_: column, channel (bare)

**Experiment**:
A full CleanMast run from preprocessed mast/meso data to report.

### Reconstruction

**Method**:
A named reconstruction algorithm identified by id in config, benchmark records, and fit artifacts (e.g. `ols-16sector`). Refers to the algorithm only, never a trained object.
_Avoid_: model (reserved for Pydantic config IR)

**Fit**:
A trained artifact produced by fitting a method to a source×target pair over a timerange; persisted as TOML. Follows the `FillHeightFitResult` precedent.
_Avoid_: model, trained model

**Predict**:
The operator `fit × source data × timerange → full synthetic target series`, independent of observed target values. Always produces a full series — evaluation and representative-year both need full synthesis.

**Fill**:
The operator `fit × source × observed target × timerange → target series with gaps filled`. Missing-only policy: predict restricted to observed gaps.

**Reconstruction set**:
One configured reconstruction job: source, target, method, timerange, heights. The unit of run-phase strategy; config carries an explicit strategy per set.

**Feasibility screen**:
The recommend-stage computation of which (method × source × target) pairs can reconstruct anything, recorded as fillable spans + counts. Infeasible pairs are skipped downstream.

**Benchmark**:
The selection procedure ranking (source × method) candidates: whole-series WS RMSE for adequate records (≥1 year, ≥90% availability on heights of interest), monthly blocked bootstrap otherwise. The winner seeds the recommended strategy; it is not the mandate.
