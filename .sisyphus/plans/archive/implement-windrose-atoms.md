# Work Plan: Implement WindRose Atoms

## TL;DR

Implement all WindRose-related ReportAtoms based on the updated PRD. This includes frequency roses, power roses, and monthly grids.

**Dependencies**: WindRose PRD must be updated first

---

## Context

WindRose analysis produces directional statistics:
- 16-sector wind frequency roses
- 16-sector wind power roses  
- Monthly breakdowns (3x4 grids)
- Multi-height overlays

Atoms needed:
1. SingleMastMonthlyWindFrequencyRoseAtom
2. SingleMastWindPowerRoseAtom
3. SingleMastMonthlyWindRoseGridAtom

---

## Work Objectives

### Deliverables
1. AnalysisResult schema (WindRoseSchema)
2. WindRoseCalculator domain service
3. 3 ReportAtom classes
4. Analysis → Atom converter
5. Tests

---

## Execution Strategy

### Wave 1: Foundation
- Task 1: Create WindRoseSchema with dataframely
- Task 2: Implement WindRoseCalculator

### Wave 2: Atoms (Parallel)
- Task 3: SingleMastMonthlyWindFrequencyRoseAtom
- Task 4: SingleMastWindPowerRoseAtom
- Task 5: SingleMastMonthlyWindRoseGridAtom

### Wave 3: Integration
- Task 6: WindRoseAnalysisToAtoms converter
- Task 7: Tests

---

## TODOs

- [ ] 1. Create WindRoseSchema
  **What**: dataframely schema with sector, frequency, power fields
  **Files**: `value_objects/schemas/wind_rose.py`

- [ ] 2. Implement WindRoseCalculator
  **What**: Domain service calculating directional statistics
  **Files**: `services/wind_rose_calculator.py`

- [ ] 3. SingleMastMonthlyWindFrequencyRoseAtom
  **What**: Polar chart + table for wind frequency
  **Files**: `value_objects/single_mast/wind_rose_frequency.py`

- [ ] 4. SingleMastWindPowerRoseAtom
  **What**: Polar chart with power density coloring
  **Files**: `value_objects/single_mast/wind_rose_power.py`

- [ ] 5. SingleMastMonthlyWindRoseGridAtom
  **What**: 3x4 grid of monthly roses
  **Files**: `value_objects/single_mast/wind_rose_grid.py`

- [ ] 6. WindRoseAnalysisToAtoms
  **What**: Converter from AnalysisResult to atoms
  **Files**: `services/wind_rose_converter.py`

- [ ] 7. Tests
  **What**: Unit + integration tests
  **Files**: `tests/analysis/test_wind_rose_calculator.py`, `tests/report/test_wind_rose_atoms.py`

---

## Success Criteria

- [ ] All 3 atoms implemented
- [ ] Polar charts render correctly
- [ ] Tables generate valid Typst
- [ ] Tests pass
- [ ] Feature parity with Julia
