# Technical Debt Register

> Tracked issues found during planning/analysis that are out of scope for current work
> but must not be forgotten. Each entry has a source, priority, and suggested timing.

---

## Import Architecture

### TD-001: Upstream Re-export Chain Not Broken
- **Priority**: Medium
- **Found by**: Metis (entities-import-refactor review)
- **Description**: `subdomains/__init__.py` → `dataingestion/__init__.py` → `entities/__init__.py` re-export chain still provides `from cleanmast.subdomains import TimeSeriesData`. After entities refactor, this chain remains as a bypass for the `entities-package-marker-banned` lint rule.
- **Impact**: The import gate can be trivially bypassed via `from cleanmast.subdomains import TimeSeriesData`
- **Suggested timing**: After entities-import-refactor plan completes
- **Action**: Clean up `subdomains/__init__.py` and `dataingestion/__init__.py` re-exports, add `entities-package-marker-banned` coverage for these paths

### TD-002: report_generation_service Reassembly Pattern — CLOSED
Resolved by report-gen-service-refactor plan. TimeSeriesData now passed directly via TYPE_CHECKING import.

### TD-003: Future Reconstruction Module Whitelist
- **Priority**: Low
- **Found by**: User (discussion)
- **Description**: When reconstruction is implemented, it will need to create `TimeSeriesData` objects as pipeline output. It will need to be added to the `timeseriesdata-creation-gate` whitelist.
- **Impact**: New reconstruction code will fail linter until whitelisted
- **Suggested timing**: When reconstruction module is built
- **Action**: Add reconstruction module to `source_modules` in `timeseriesdata-creation-gate` contract

### TD-004: single_mast/__init__.py Sub-package Re-exports — CLOSED
Resolved by entities-import-refactor plan. Re-exports cleaned, package markers only.

---

## Code Quality

### TD-005: turbulence_subsection.py Imports from Sub-package Marker — CLOSED
Resolved by entities-import-refactor plan. Imports converted to direct module paths.

### TD-006: Pre-existing Calculator Bugs
- **Priority**: Medium
- **Found by**: rep-ts-refactor work
- **Description**: Several calculators have bugs:
  - `wind_frequency_calculator.py` — Polars schema mixing "内插" string
  - `turbulence_calculator.py` — similar Polars schema mixing
  - `WindTemporalAnalyzer` — missing `analyze_time_series` method
- **Impact**: Sections fail to generate in rep-ts report
- **Suggested timing**: When respective report sections are needed
- **Action**: Fix each calculator individually

### TD-007: Typst Template Syntax Errors — CLOSED
Resolved by td007-typst-fix plan. Fixed Chinese commas in header (line 59) and trailing comma pattern (line 51) in turbulence_sector.py. Added Typst compilation validation tests with golden snapshot regression testing.

**Fixed files:**
- `packages/cleanmast/src/cleanmast/subdomains/assessment/domain/entities/single_mast/turbulence_sector.py`

**Added files:**
- `packages/cleanmast/tests/assessment/test_typst_compilation.py`
- `packages/cleanmast/tests/assessment/snapshots/*.typ` (5 golden snapshot files)

### TD-011: turbulence_summary.py — Incorrect TI Threshold Comparisons
- **Priority**: Medium
- **Found by**: User review (typecheck-quickwins follow-up)
- **Description**: `turbulence_summary.py:142-143` uses hardcoded thresholds `avg_mean_ti > 0.15`, `> 0.12`, `> 0.16` for turbulence intensity classification. These comparisons are incorrect — TI should be referenced against IEC standard at 15 m/s, not compared as raw averages.
 Incorrect business logic, not type error.
- **Impact**: Summary text gives misleading turbulence level classification
- **Suggested timing**: When turbulence reporting accuracy is needed
- **Action**: Rewrite renderSummary thresholds to use IEC 15 m/s reference turbulence intensity
- **Files**: `packages/cleanmast/src/cleanmast/subdomains/assessment/domain/entities/single_mast/turbulence_summary.py` (lines 142-143)

### TD-012: turbulence_sector.py — Incorrect TI Percentage Display
- **Priority**: Medium
- **Found by**: User review (typecheck-quickwins follow-up)
- **Description**: `turbulence_sector.py:146` computes `avg_ti * 100` and displays as percentage. This is incorrect — TI should be referenced against IEC standard at 15 m/s, not displayed as a raw percentage of average. Incorrect business logic, not type error.
- **Impact**: Summary text gives misleading turbulence percentage
- **Suggested timing**: When turbulence reporting accuracy is needed
- **Action**: Rewrite renderSummary to use IEC 15 m/s reference turbulence intensity
- **Files**: `packages/cleanmast/src/cleanmast/subdomains/assessment/domain/entities/single_mast/turbulence_sector.py` (line 146)

### TD-015: Deprecated Polars .melt() Call — CLOSED
Resolved by commit `6344f68`. Replaced with .unpivot() using updated parameter names (index/on). in wind_frequency_distribution.py.

---

### TD-008: Inconsistent Subdomain Documentation — CLOSED
Resolved. structure-001 ADR updated to document 3 actual patterns (layered, organized-flat, minimal-flat) with concrete examples. Path fixed.

### TD-009: Phantom reporting Subdomain — CLOSED
Resolved. The imports were confirmed to be stale references from pre-entities-import-refactor architecture. The affected files have been updated to remove the phantom `cleanmast.subdomains.reporting` imports. The `reporting` domain no longer exists as a subdomain — functionality has been reorganized under `assessment` and `pipeline` domains.

---

## Infrastructure

### TD-010: from __future__ import annotations Adoption
- **Priority**: Low
- **Found by**: Entities refactor discussion
- **Description**: Only 6 files currently have `from __future__ import annotations`. After TYPE_CHECKING pattern is introduced, ~17 more files will get it. Consider broader adoption for consistency.
- **Impact**: Inconsistent pattern — some files need quoted type hints, others don't
- **Suggested timing**: Low priority, opportunistically
- **Action**: Consider project-wide adoption or a lint rule for it

---

## Changelog

| Date | Entry |
|------|-------|
| 2026-04-02 | Created. TD-001 through TD-010 from Metis review and prior work. |
| 2026-04-03 | Added TD-011, TD-012: Incorrect turbulence summary thresholds (should reference IEC 15m/s standard). |
| 2026-04-03 | Closed TD-008: structure-001 ADR updated with 3 patterns (layered, organized-flat, minimal-flat). |
