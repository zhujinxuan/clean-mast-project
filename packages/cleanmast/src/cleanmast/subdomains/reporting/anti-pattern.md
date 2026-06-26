# Anti-Patterns — Reporting Subdomain

Audit date: 2026-06-26. Checked against `reporting/spec.md` and `subdomains/spec.md`.

---

## VIOLATIONS

### V1. `get_height_display_name` DRY violation (RESOLVED)

**Resolution**: Consolidated into `reporting/model/height_label.py` (`consolidate-height-display` plan). All 7 duplicates removed (6 deleted, 1 converted to thin wrapper `_height_label` in wind_frequency). Canonical function now uses unified parentheses format: `"120m(外推)"`. ~50 callers updated.

**Status**: ✅ Done.

### V2. `ExtremeWindSection.from_computed_results` accepts pre-computed DataFrames

**File**: `subdomains/extreme_wind/section.py:100`  
**Rule**: Spec Rule 9 — "pre-computed DataFrame inputs are forbidden"

`from_computed_results` is a public classmethod accepting raw `pl.DataFrame` params. Only called internally by `from_inputs` today, but nothing prevents external bypass.

**Status**: ✅ Done. Method renamed to `_from_computed_results` (privatized).

---

## SMELLS

### S1. `api.py` imports from `dataingestion.infrastructure`

`api.py:16` imports `load_timeseries` from `dataingestion.infrastructure`. Permitted by `subdomains/spec.md` Rule 13 but reaches into a downstream `infrastructure` module.

> **Note**: Low priority — permitted by spec and low risk.


---

## KNOWN DEVIATIONS

### D1. `representative_year` accepts `MesoSectionInput` instead of `SingleMastAnalysisInput`

**File**: `subdomains/representative_year/section.py:52`
**Standard**: All other 8 capabilities accept `list[SingleMastAnalysisInput]` via `from_inputs`; `representative_year` accepts `list[MesoSectionInput]`.

**Consequences**:
- Uses custom intermediate classmethod `from_mast_data` with 5-element tuple `(TimeSeriesData, str, str, datetime, datetime)` instead of the standard `from_time_series` with 2-element tuple.
- Compute takes a custom `RepresentativeYearMastInput` dataclass rather than working from `TimeSeriesData` directly.

**Future fix**: Standardize to `SingleMastAnalysisInput` with meso reference attached. Add 16-sector wind correlation subsection for rep-year calibration. Do NOT propagate this pattern to other capabilities.

**Status**: 🔴 Open — no timeline yet.