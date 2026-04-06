# Work Plan: Implement WindFrequency Atoms

## TL;DR

Implement wind speed and power frequency distribution atoms with grouped bar charts and summary tables.

**Dependencies**: PRD created (`.sisyphus/notepads/prds/windfrequency-analysis-migration.md`)

---

## Context

WindFrequency analysis calculates distribution across speed bins:
- Wind speed frequency by 1 m/s bins (0-28 m/s)
- Wind power frequency (energy contribution by bin)
- Occurrence hours (frequency * 8760)
- 3-25 m/s range summary

Atoms:
1. SingleMastWindFrequencyTableAtom
2. SingleMastWindPowerFrequencyTableAtom
3. SingleMastWindFrequencyDistributionAtom
4. SingleMastWindRangeSummaryAtom

### ⚠️ CRITICAL: Folder Location per ddd-t-002

Per `ddd-t-002-entities-value-objects`, **ReportAtoms ARE ENTITIES** (not Value Objects):
- They have identity (content hash)
- They belong in `entities/` folder
- **NOT** in `value_objects/` folder

All 4 atoms in this plan must be created in:
```
packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/
```

---

## Work Objectives

### Deliverables
1. WindFrequencySchema
2. WindFrequencyCalculator
3. 4 ReportAtoms
4. Converter
5. Tests

---

## Execution Strategy

### Wave 1: Foundation
- Task 1: WindFrequencySchema
- Task 2: WindFrequencyCalculator (histogram, power calc)

### Wave 2: Atoms (Parallel)
- Task 3: SingleMastWindFrequencyTableAtom
- Task 4: SingleMastWindPowerFrequencyTableAtom
- Task 5: SingleMastWindFrequencyDistributionAtom
- Task 6: SingleMastWindRangeSummaryAtom

### Wave 3: Integration
- Task 7: WindFrequencyAnalysisToAtoms converter
- Task 8: Tests

---

## TODOs

- [ ] 1. WindFrequencySchema
  **Files**: `value_objects/schemas/wind_frequency.py`
  **Fields**: height, bin_start, bin_end, bin_center, frequency, occurrence_hours, power_frequency, power_hours

- [ ] 2. WindFrequencyCalculator
  **Files**: `services/wind_frequency_calculator.py`
  **Methods**: calculate_histogram(), calculate_power_frequency(), calculate_range_summary()
  **Formula**: P = 0.5 * ρ * v³

- [ ] 3. SingleMastWindFrequencyTableAtom
  **Files**: `entities/single_mast/wind_frequency_table.py`
  **Renders**: Typst table with multi-height columns
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [ ] 4. SingleMastWindPowerFrequencyTableAtom
  **Files**: `entities/single_mast/wind_power_frequency_table.py`
  **Renders**: Typst table with power frequencies
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [ ] 5. SingleMastWindFrequencyDistributionAtom
  **Files**: `entities/single_mast/wind_frequency_distribution.py`
  **Renders**: Grouped bar chart (speed freq vs power freq) with Altair
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [ ] 6. SingleMastWindRangeSummaryAtom
  **Files**: `entities/single_mast/wind_range_summary.py`
  **Renders**: 3-25 m/s summary table
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [ ] 7. WindFrequencyAnalysisToAtoms
  **Files**: `services/wind_frequency_converter.py`

- [ ] 8. Tests
  **Files**: `tests/analysis/test_wind_frequency_calculator.py`, `tests/report/test_wind_frequency_atoms.py`

---

## Key Formulas

### Wind Power Density
```
P = 0.5 * ρ * v³
```

### Frequency
```
frequency = count_bin / total_count
```

### Power Frequency
```
power_frequency = sum(power_in_bin) / total_power
```

---

## Success Criteria

- [ ] Frequencies sum to 1.0 (within epsilon)
- [ ] Power frequencies sum to 1.0
- [ ] Hours calculation correct (frequency * 8760)
- [ ] Grouped bar chart renders correctly
- [ ] All 4 atoms functional
- [ ] Tests pass
