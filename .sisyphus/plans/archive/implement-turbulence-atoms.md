# Work Plan: Implement Turbulence Atoms

## TL;DR

Implement turbulence intensity analysis atoms with IEC category classification and Meteodyn WT export.

**Dependencies**: PRD created (`.sisyphus/notepads/prds/turbulence-analysis-migration.md`)

---

## Context

Turbulence analysis calculates intensity statistics:
- TI = σ / max(μ, 1.0) per timestamp
- Representative TI (P90) = mean + 1.28*std
- IEC category classification (A+, A, B, C)
- Sector-wise analysis
- Meteodyn WT format export

Atoms:
1. SingleMastTurbulenceIntensityAtom - TI vs wind speed with IEC bands
2. SingleMastTurbulenceSectorAtom - Polar chart by direction
3. SingleMastTurbulenceMultiHeightAtom - Combined TI plot
4. SingleMastTurbulenceSummaryAtom - Summary table

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
1. TurbulenceSchema
2. TurbulenceCalculator domain service
3. 4 ReportAtoms
4. Converter
5. Tests

---

## Execution Strategy

### Wave 1: Foundation
- Task 1: TurbulenceSchema + TurbulenceSectorSchema
- Task 2: TurbulenceCalculator (TI calc, IEC categories)

### Wave 2: Atoms (Parallel)
- Task 3: SingleMastTurbulenceIntensityAtom
- Task 4: SingleMastTurbulenceSectorAtom
- Task 5: SingleMastTurbulenceMultiHeightAtom
- Task 6: SingleMastTurbulenceSummaryAtom

### Wave 3: Integration + Export
- Task 7: TurbulenceAnalysisToAtoms converter
- Task 8: Meteodyn WT export format
- Task 9: Tests

---

## TODOs

- [ ] 1. TurbulenceSchema
  **Files**: `value_objects/schemas/turbulence.py`
  **Fields**: wind_speed_bin, height, mean_ti, std_ti, representative_ti, iec_category

- [ ] 2. TurbulenceCalculator
  **Files**: `services/turbulence_calculator.py`
  **Methods**: calculate_ti_series(), calculate_iec_ti(), get_iec_category(), calculate_by_sector()
  **Constants**: IEC_CATEGORIES = {"A": 0.16, "B": 0.14, "C": 0.12}

- [ ] 3. SingleMastTurbulenceIntensityAtom
  **Files**: `entities/single_mast/turbulence_intensity.py`
  **Renders**: Line chart (representative TI) with IEC band fills (Altair area marks)
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [ ] 4. SingleMastTurbulenceSectorAtom
  **Files**: `entities/single_mast/turbulence_sector.py`
  **Renders**: Polar bar chart of TI by sector
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [ ] 5. SingleMastTurbulenceMultiHeightAtom
  **Files**: `entities/single_mast/turbulence_multi.py`
  **Renders**: Combined plot with IEC bands + multi-height TI lines
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [ ] 6. SingleMastTurbulenceSummaryAtom
  **Files**: `entities/single_mast/turbulence_summary.py`
  **Renders**: Summary table (height | wind range | mean TI | rep TI | IEC)
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [ ] 7. TurbulenceAnalysisToAtoms
  **Files**: `services/turbulence_converter.py`

- [ ] 8. Meteodyn WT Export
  **Files**: `infrastructure/meteodyn_exporter.py`
  **Format**: Tab-delimited, 16 sectors, TI matrix

- [ ] 9. Tests
  **Files**: `tests/analysis/test_turbulence_calculator.py`, `tests/report/test_turbulence_atoms.py`

---

## Key Formulas

### Turbulence Intensity
```
TI = σ / max(μ, 1.0)
```

### Representative TI (P90)
```
TI_rep = mean(TI) + 1.28 * std(TI)
```

### IEC Reference TI
```
TI_IEC = I_ref * (0.75 + 5.6/V)
```

---

## Meteodyn WT Format

```
28
2.0	0.12	0.13	...	0.11
3.0	0.11	0.12	...	0.10
...
```

- First line: number of wind speed bins
- Each row: v_max + 16 sector TI values (tab-delimited)

---

## Success Criteria

- [ ] TI calculations match IEC 61400-1
- [ ] IEC category classification correct
- [ ] Meteodyn WT format exports correctly
- [ ] All 4 atoms functional
- [ ] Tests cover edge cases (missing data, low wind speeds)
