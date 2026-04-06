# Work Plan: Implement VerticalProfile Atoms

## TL;DR

Implement vertical wind profile atoms with power law fitting, shear analysis, and shear exponent matrix.

**Dependencies**: PRD created (`.sisyphus/notepads/prds/verticalprofile-analysis-migration.md`)

---

## Context

VerticalProfile analysis examines wind speed vs height:
- Power law fitting: v = v_ref * (h/h_ref)^α
- Wind shear between height pairs
- Shear exponent matrix (all pairs)
- Vertical profile plots

Atoms:
1. SingleMastVerticalProfileAtom
2. SingleMastWindShearTableAtom
3. SingleMastWindShearExponentAtom

---

## Work Objectives

### Deliverables
1. VerticalProfileSchema + WindShearSchema
2. VerticalProfileAnalyzer
3. 3 ReportAtoms
4. Converter
5. Tests

---

## Execution Strategy

### Wave 1: Foundation
- Task 1: VerticalProfileSchema + WindShearSchema
- Task 2: VerticalProfileAnalyzer (power law fit, shear calc)

### Wave 2: Atoms (Parallel)
- Task 3: SingleMastVerticalProfileAtom
- Task 4: SingleMastWindShearTableAtom
- Task 5: SingleMastWindShearExponentAtom

### Wave 3: Integration
- Task 6: VerticalProfileAnalysisToAtoms converter
- Task 7: Tests

---

## TODOs

- [ ] 1. VerticalProfileSchema
  **Files**: `value_objects/schemas/vertical_profile.py`
  **Fields**: height, mean_wind_speed, power_law_alpha, r_squared

- [ ] 2. WindShearSchema
  **Files**: `value_objects/schemas/wind_shear.py`
  **Fields**: height_pair, lower_height, upper_height, mean_alpha, std_alpha

- [ ] 3. VerticalProfileAnalyzer
  **Files**: `services/vertical_profile_analyzer.py`
  **Methods**: fit_power_law(), calculate_wind_shear(), calculate_shear_matrix()
  **Algorithm**: Log-linear regression (scipy.stats.linregress)

- [ ] 4. SingleMastVerticalProfileAtom
  **Files**: `value_objects/single_mast/vertical_profile.py`
  **Renders**: Scatter points (measured) + fit line (log-log scale)

- [ ] 5. SingleMastWindShearTableAtom
  **Files**: `value_objects/single_mast/wind_shear_table.py`
  **Renders**: Table of shear stats by height pair

- [ ] 6. SingleMastWindShearExponentAtom
  **Files**: `value_objects/single_mast/wind_shear_matrix.py`
  **Renders**: Matrix table (rows=from, cols=to, values=α, diagonal="◦")

- [ ] 7. VerticalProfileAnalysisToAtoms
  **Files**: `services/vertical_profile_converter.py`

- [ ] 8. Tests
  **Files**: `tests/analysis/test_vertical_profile_analyzer.py`, `tests/report/test_vertical_profile_atoms.py`

---

## Key Formulas

### Power Law
```
v = v_ref * (h / h_ref)^α
```

### Log-Linear Regression
```
log(v) = log(v_ref) + α * log(h)
```
Fit: log_speed ~ log_height, extract α = slope

### Wind Shear (per timestamp)
```
α = ln(v2/v1) / ln(h2/h1)
```

### Shear Matrix
For each pair (i, j):
```
α_ij = ln(v_i/v_j) / ln(h_i/h_j)
```

---

## Typical Alpha Values

| Terrain | Alpha Range |
|---------|-------------|
| Smooth (water) | 0.10-0.12 |
| Open (grassland) | 0.12-0.16 |
| Rough (suburban) | 0.16-0.25 |
| Very rough (urban) | 0.25-0.40 |

---

## Success Criteria

- [ ] Power law fitting produces valid α
- [ ] R² calculation correct
- [ ] Shear calculations match expected range
- [ ] Matrix table displays correctly
- [ ] All 3 atoms functional
- [ ] Tests pass
