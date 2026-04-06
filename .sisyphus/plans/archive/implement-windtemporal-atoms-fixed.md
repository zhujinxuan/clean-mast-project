# Work Plan: Implement WindTemporal Atoms (FIXED)

## TL;DR

Implement temporal pattern atoms: time series, daily patterns, monthly patterns, and 3x4 monthly-daily grids.

---

## Context

WindTemporal analysis generates time-based patterns:
- Full time series (line chart)
- Daily 24-hour patterns (line chart)
- Monthly patterns (grouped bar)
- Monthly-daily combined (3x4 faceted grids)
- Both wind speed AND wind power versions

**Atoms** (7 total):
1. SingleMastWindTimeseriesAtom
2. SingleMastDailyPatternAtom
3. SingleMastDailyPowerPatternAtom
4. SingleMastMonthlyPatternAtom
5. SingleMastMonthlyPowerPatternAtom
6. SingleMastMonthlyDailyWindAtom
7. SingleMastMonthlyDailyPowerAtom

**Source**: Julia `WindTemporal.jl` (714 lines)

### ⚠️ CRITICAL: Folder Location per ddd-t-002

Per `ddd-t-002-entities-value-objects`, **ReportAtoms ARE ENTITIES** (not Value Objects):
- They have identity (content hash)
- They belong in `entities/` folder
- **NOT** in `value_objects/` folder

All 7 atoms in this plan must be created in:
```
packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/
```

NOT in `value_objects/single_mast/` (where some atoms are currently misplaced).

---

## Work Objectives

### Deliverables
1. TemporalPatternSchema
2. WindTemporalAnalyzer
3. 7 ReportAtoms
4. Converter
5. Tests

---

## Task Dependency Graph

| Task | Depends On | Reason |
|------|-----------|--------|
| 1. TemporalPatternSchema | None | Independent |
| 2. WindTemporalAnalyzer | Task 1 | Uses schema |
| 3-9. All Atoms | Tasks 1,2 | Need schema + analyzer |
| 10. Converter | Tasks 3-9 | Needs all atoms |
| 11. Tests | Tasks 1-10 | Tests everything |

## Parallel Execution Graph

```
Wave 1 (Foundation):
├── Task 1: TemporalPatternSchema [quick]
└── Task 2: WindTemporalAnalyzer [unspecified-high]
    (depends: 1)

Wave 2 (Basic Atoms - Parallel):
├── Task 3: WindTimeseriesAtom [visual-engineering]
├── Task 4: DailyPatternAtom [visual-engineering]
├── Task 5: DailyPowerAtom [visual-engineering]
├── Task 6: MonthlyPatternAtom [visual-engineering]
└── Task 7: MonthlyPowerAtom [visual-engineering]
    (depends: 1,2)

Wave 3 (Grid Atoms - Parallel):
├── Task 8: MonthlyDailyWindAtom [visual-engineering]
└── Task 9: MonthlyDailyPowerAtom [visual-engineering]
    (depends: 1,2)

Wave 4 (Integration):
├── Task 10: Converter [quick]
│   (depends: 3-9)
└── Task 11: Tests [unspecified-high]
    (depends: 1-10)

Critical Path: 1 → 2 → (3-9 parallel) → 10 → 11
Parallel Speedup: 60% (Waves 2-3)
Max Concurrent: 5 (Wave 2)
```

## Agent Dispatch Summary

| Wave | Tasks | Agent Profile |
|------|-------|---------------|
| 1 | 2 | quick, unspecified-high |
| 2 | 5 | visual-engineering x5 |
| 3 | 2 | visual-engineering x2 |
| 4 | 2 | quick, unspecified-high |

---

## TODOs

- [x] 1. TemporalPatternSchema
  **File**: `packages/cleanmast/src/cleanmast/subdomains/reporting/value_objects/single_mast/schemas.py`
  **Category**: `quick`
  **QA**: Verify schema fields

- [x] 2. WindTemporalAnalyzer
  **File**: `packages/cleanmast/src/cleanmast/subdomains/analysis/services/wind_temporal_analyzer.py`
  **Category**: `unspecified-high`
  **QA**: Test daily aggregation (24 points), monthly (12 points)

- [x] 3. SingleMastWindTimeseriesAtom
  **File**: `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/timeseries.py`
  **Category**: `visual-engineering`
  **QA**: Multi-line chart renders
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [x] 4. SingleMastDailyPatternAtom
  **File**: `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/daily_pattern.py`
  **Category**: `visual-engineering`
  **QA**: 24-hour line chart
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [x] 5. SingleMastDailyPowerPatternAtom
  **File**: `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/daily_power_pattern.py`
  **Category**: `visual-engineering`
  **QA**: Power version renders
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [x] 6. SingleMastMonthlyPatternAtom
  **File**: `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/monthly_pattern.py`
  **Category**: `visual-engineering`
  **QA**: Grouped bar chart (12 months)
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [x] 7. SingleMastMonthlyPowerPatternAtom
  **File**: `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/monthly_power_pattern.py`
  **Category**: `visual-engineering`
  **QA**: Power bar chart
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [x] 8. SingleMastMonthlyDailyWindAtom
  **File**: `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/monthly_daily_wind.py`
  **Category**: `visual-engineering`
  **QA**: 3x4 faceted grid renders, 1200x900px
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [x] 9. SingleMastMonthlyDailyPowerAtom
  **File**: `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/monthly_daily_power.py`
  **Category**: `visual-engineering`
  **QA**: Power grid renders
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [x] 10. WindTemporalAnalysisToAtoms
  **File**: `packages/cleanmast/src/cleanmast/subdomains/reporting/services/wind_temporal_converter.py`
  **Category**: `quick`
  **QA**: Creates 7 atoms from result

- [x] 11. Tests
  **Files**: `packages/cleanmast/tests/analysis/test_wind_temporal_analyzer.py`, `packages/cleanmast/tests/report/test_wind_temporal_atoms.py`
  **Category**: `unspecified-high`
  **QA**: All tests pass, >90% coverage

---

## QA Scenarios

```
Scenario: Daily aggregation produces 24 hours
  Tool: Bash (pytest)
  Steps:
    1. uv run pytest tests/analysis/test_wind_temporal_analyzer.py::TestDailyPattern::test_24_hours -v
  Expected: len(result) == 24
  Evidence: pytest output

Scenario: Monthly aggregation produces 12 months
  Tool: Bash (pytest)
  Steps:
    1. uv run pytest tests/analysis/test_wind_temporal_analyzer.py::TestMonthlyPattern::test_12_months -v
  Expected: len(result) == 12
  Evidence: pytest output

Scenario: 3x4 grid has correct dimensions
  Tool: Python REPL
  Steps:
    1. from PIL import Image
    2. img = Image.open("monthly_daily.png")
    3. assert img.size == (1200, 900)
  Expected: Assertions pass
  Evidence: Terminal output

Scenario: All 7 atoms render successfully
  Tool: Bash (pytest)
  Steps:
    1. uv run pytest tests/report/test_wind_temporal_atoms.py -v
  Expected: 21 tests pass (3 per atom)
  Evidence: pytest output
```

---

## Final Verification Wave

- [ ] F1. **Plan Compliance** (oracle)
- [ ] F2. **Code Quality** (unspecified-high)
- [ ] F3. **Visual QA** (unspecified-high)
- [ ] F4. **Integration** (deep)

---

## Success Criteria

- [ ] All 7 atoms implemented
- [ ] **CORRECT LOCATION**: All atoms in `entities/single_mast/` (NOT `value_objects/`)
- [ ] Daily aggregation: 24 points
- [ ] Monthly aggregation: 12 points
- [ ] 3x4 grid renders correctly
- [ ] Tests >90% coverage

### Location Verification QA
```
Scenario: Atoms in correct folder (entities/)
  Tool: Bash
  Steps:
    1. ls packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/
    2. ls packages/cleanmast/src/cleanmast/subdomains/reporting/value_objects/single_mast/ | grep -E "(timeseries|daily|monthly)"
  Expected: 
    - entities/single_mast/ has: timeseries.py, daily_pattern.py, daily_power_pattern.py, monthly_pattern.py, monthly_power_pattern.py, monthly_daily_wind.py, monthly_daily_power.py
    - value_objects/single_mast/ does NOT have these files
  Evidence: ls output

Scenario: Can import from correct location
  Tool: Python REPL
  Steps:
    1. from cleanmast.subdomains.reporting.entities.single_mast import SingleMastDailyPatternAtom
    2. from cleanmast.subdomains.reporting.entities.single_mast import SingleMastMonthlyPatternAtom
  Expected: No ImportError
  Evidence: REPL output
```
