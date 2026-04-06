# Work Plan: Implement VerticalProfile Atoms (FIXED)

## TL;DR

Implement vertical wind profile atoms with power law fitting, shear analysis, and shear exponent matrix.

---

## Context

VerticalProfile analysis examines wind speed vs height:
- Power law fitting: v = v_ref * (h/h_ref)^α
- Log-linear regression
- Wind shear between height pairs
- Shear exponent matrix

**Atoms**:
1. SingleMastVerticalProfileAtom
2. SingleMastWindShearTableAtom
3. SingleMastWindShearExponentAtom

**Source**: Julia `Vertical.jl` (354 lines)

### ⚠️ CRITICAL: Folder Location per ddd-t-002

Per `ddd-t-002-entities-value-objects`, **ReportAtoms ARE ENTITIES** (not Value Objects):
- They have identity (content hash)
- They belong in `entities/` folder
- **NOT** in `value_objects/` folder

All 3 atoms in this plan must be created in:
```
packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/
```

---

## Work Objectives

### Deliverables
1. VerticalProfileSchema + WindShearSchema
2. VerticalProfileAnalyzer
3. 3 ReportAtoms
4. Converter
5. Tests

---

## Task Dependency Graph

| Task | Depends On | Reason |
|------|-----------|--------|
| 1. Schemas | None | Independent |
| 2. Analyzer | Task 1 | Uses schemas |
| 3-5. Atoms | Tasks 1,2 | Need schemas + analyzer |
| 6. Converter | Tasks 3-5 | Needs atoms |
| 7. Tests | Tasks 1-6 | Tests all |

## Parallel Execution Graph

```
Wave 1 (Foundation):
├── Task 1: VerticalProfileSchema + WindShearSchema [quick]
└── Task 2: VerticalProfileAnalyzer [unspecified-high]
    (depends: 1)

Wave 2 (Atoms - Parallel):
├── Task 3: VerticalProfileAtom [visual-engineering]
├── Task 4: WindShearTableAtom [quick]
└── Task 5: WindShearExponentAtom [quick]
    (depends: 1,2)

Wave 3 (Integration):
├── Task 6: Converter [quick]
│   (depends: 3,4,5)
└── Task 7: Tests [unspecified-high]
    (depends: 1-6)

Critical Path: 1 → 2 → (3,4,5 parallel) → 6 → 7
Parallel Speedup: 40% (Wave 2)
Max Concurrent: 3 (Wave 2)
```

## Agent Dispatch Summary

| Wave | Tasks | Agent Profile |
|------|-------|---------------|
| 1 | 2 | quick, unspecified-high |
| 2 | 3 | visual-engineering, quick x2 |
| 3 | 2 | quick, unspecified-high |

---

## TODOs

- [ ] 1. VerticalProfileSchema + WindShearSchema
  **File**: `packages/cleanmast/src/cleanmast/subdomains/reporting/value_objects/single_mast/schemas.py`
  **Category**: `quick`
  **QA**: Verify both schemas defined

- [ ] 2. VerticalProfileAnalyzer
  **File**: `packages/cleanmast/src/cleanmast/subdomains/analysis/services/vertical_profile_analyzer.py`
  **Category**: `unspecified-high`
  **Methods**: fit_power_law(), calculate_wind_shear(), calculate_shear_matrix()
  **QA**: Power law fit produces valid α, R² > 0.9

- [ ] 3. SingleMastVerticalProfileAtom
  **File**: `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/vertical_profile.py`
  **Category**: `visual-engineering`
  **Renders**: Scatter (measured) + line (fit) on log-log scale
  **QA**: Chart shows α and R² in title
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [ ] 4. SingleMastWindShearTableAtom
  **File**: `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/wind_shear_table.py`
  **Category**: `quick`
  **Renders**: Table with height pairs and shear stats
  **QA**: Table includes mean, std, min, max α
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [ ] 5. SingleMastWindShearExponentAtom
  **File**: `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/wind_shear_matrix.py`
  **Category**: `quick`
  **Renders**: Matrix table (rows=from, cols=to, diagonal="◦")
  **QA**: Matrix square, symmetric values
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

- [ ] 6. VerticalProfileAnalysisToAtoms
  **File**: `packages/cleanmast/src/cleanmast/subdomains/reporting/services/vertical_profile_converter.py`
  **Category**: `quick`
  **QA**: Creates 3 atoms from result

- [ ] 7. Tests
  **Files**: `packages/cleanmast/tests/analysis/test_vertical_profile_analyzer.py`, `packages/cleanmast/tests/report/test_vertical_profile_atoms.py`
  **Category**: `unspecified-high`
  **QA**: All tests pass

---

## QA Scenarios

```
Scenario: Power law fit accuracy
  Tool: Bash (pytest)
  Steps:
    1. uv run pytest tests/analysis/test_vertical_profile_analyzer.py::TestPowerLaw::test_fit_accuracy -v
  Expected: α within 0.01 of expected, R² > 0.99
  Evidence: pytest output

Scenario: Shear calculation
  Tool: Python REPL
  Steps:
    1. heights = [100, 120]
    2. speeds = [8.0, 8.5]
    3. α = log(8.5/8.0) / log(120/100)
    4. assert abs(α - 0.304) < 0.001
  Expected: Assertion passes
  Evidence: Terminal output

Scenario: Shear exponent matrix
  Tool: Bash (pytest)
  Steps:
    1. uv run pytest tests/report/test_vertical_profile_atoms.py::TestShearMatrix::test_matrix_format -v
  Expected: Diagonal shows "◦", values symmetric
  Evidence: pytest output

Scenario: Vertical profile plot
  Tool: Bash (pytest)
  Steps:
    1. uv run pytest tests/report/test_vertical_profile_atoms.py::TestVerticalProfileAtom::test_render_image -v
  Expected: PNG created, shows scatter + line
  Evidence: pytest output + file check
```

---

## Key Formulas

### Power Law
```
v = v_ref * (h / h_ref)^α
```

### Log-Linear Regression
```
log(v) = intercept + α * log(h)
```
Fit via scipy.stats.linregress

### Wind Shear (per timestamp)
```
α = ln(v2/v1) / ln(h2/h1)
```

### Shear Matrix
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

## Final Verification Wave

- [ ] F1. **Plan Compliance** (oracle)
- [ ] F2. **Code Quality** (unspecified-high)
- [ ] F3. **Visual QA** (unspecified-high)
- [ ] F4. **Integration** (deep)

---

## Success Criteria

- [ ] Power law fit produces valid α
- [ ] R² calculation correct
- [ ] Shear calculations match expected range
- [ ] Matrix table displays correctly
- [ ] All 3 atoms functional
- [ ] Tests pass
