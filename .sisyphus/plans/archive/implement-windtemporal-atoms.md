# Work Plan: Implement WindTemporal Atoms

## TL;DR

Implement temporal pattern atoms: time series, daily patterns, monthly patterns, and 3x4 monthly-daily grids.

**Dependencies**: WindTemporal PRD updated

---

## Context

WindTemporal analysis generates time-based patterns:
- Full time series (line chart)
- Daily 24-hour patterns (line chart)
- Monthly patterns (grouped bar)
- Monthly-daily combined (3x4 faceted grids)

Both wind speed AND wind power for each pattern type.

Atoms (7 total):
1. SingleMastWindTimeseriesAtom
2. SingleMastDailyPatternAtom
3. SingleMastDailyPowerPatternAtom
4. SingleMastMonthlyPatternAtom
5. SingleMastMonthlyPowerPatternAtom
6. SingleMastMonthlyDailyWindAtom
7. SingleMastMonthlyDailyPowerAtom

---

## Work Objectives

### Deliverables
1. TemporalPatternSchema
2. WindTemporalAnalyzer
3. 7 ReportAtoms
4. Converter
5. Tests

---

## Execution Strategy

### Wave 1: Foundation
- Task 1: TemporalPatternSchema
- Task 2: WindTemporalAnalyzer (daily/monthly aggregation)

### Wave 2: Basic Atoms (Parallel)
- Task 3: SingleMastWindTimeseriesAtom
- Task 4: SingleMastDailyPatternAtom
- Task 5: SingleMastDailyPowerPatternAtom
- Task 6: SingleMastMonthlyPatternAtom
- Task 7: SingleMastMonthlyPowerPatternAtom

### Wave 3: Grid Atoms (Parallel)
- Task 8: SingleMastMonthlyDailyWindAtom
- Task 9: SingleMastMonthlyDailyPowerAtom

### Wave 4: Integration
- Task 10: WindTemporalAnalysisToAtoms converter
- Task 11: Tests

---

## TODOs

- [ ] 1. TemporalPatternSchema
  **Files**: `value_objects/schemas/temporal_pattern.py`
  **Fields**: timestamp, hour, month, wind_speed, wind_power, height

- [ ] 2. WindTemporalAnalyzer
  **Files**: `services/wind_temporal_analyzer.py`
  **Methods**: analyze_daily_pattern(), analyze_monthly_pattern(), analyze_monthly_daily()
  **Aggregation**: groupby hour/month, calculate means

- [ ] 3. SingleMastWindTimeseriesAtom
  **Files**: `value_objects/single_mast/timeseries.py`
  **Renders**: Multi-line chart (full time range, all heights)

- [ ] 4. SingleMastDailyPatternAtom
  **Files**: `value_objects/single_mast/daily_pattern.py`
  **Renders**: 24-hour line chart

- [ ] 5. SingleMastDailyPowerPatternAtom
  **Files**: `value_objects/single_mast/daily_power_pattern.py`
  **Renders**: 24-hour line chart (power)

- [ ] 6. SingleMastMonthlyPatternAtom
  **Files**: `value_objects/single_mast/monthly_pattern.py`
  **Renders**: Grouped bar chart (12 months)

- [ ] 7. SingleMastMonthlyPowerPatternAtom
  **Files**: `value_objects/single_mast/monthly_power_pattern.py`
  **Renders**: Grouped bar chart (power)

- [ ] 8. SingleMastMonthlyDailyWindAtom
  **Files**: `value_objects/single_mast/monthly_daily_wind.py`
  **Renders**: 3x4 faceted grid (Altair facet)
  **Size**: 1200x900 pixels

- [ ] 9. SingleMastMonthlyDailyPowerAtom
  **Files**: `value_objects/single_mast/monthly_daily_power.py`
  **Renders**: 3x4 faceted grid (power)

- [ ] 10. WindTemporalAnalysisToAtoms
  **Files**: `services/wind_temporal_converter.py`

- [ ] 11. Tests
  **Files**: `tests/analysis/test_wind_temporal_analyzer.py`, `tests/report/test_wind_temporal_atoms.py`

---

## Altair Faceted Grid

```python
chart = alt.Chart(df).mark_line().encode(
    x='hour:O',
    y='wind_speed:Q',
    color='height:N',
    facet=alt.Facet('month_name:N', columns=4)
).properties(
    width=250,
    height=200
)
```

---

## Success Criteria

- [ ] All 7 atoms implemented
- [ ] Daily aggregation correct (24 points)
- [ ] Monthly aggregation correct (12 points)
- [ ] 3x4 grid renders correctly
- [ ] Power calculations use air density
- [ ] Tests pass
