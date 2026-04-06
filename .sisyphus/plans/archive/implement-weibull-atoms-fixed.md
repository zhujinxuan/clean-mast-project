# Work Plan: Implement Weibull Atoms (FIXED)

## TL;DR

Implement Weibull distribution fitting atoms with MLE, Method of Moments fallback, and multi-height visualizations.

---

## Context

Weibull analysis fits probability distributions to wind speed data:
- MLE for shape (k) and scale (c) parameters
- Method of Moments fallback when MLE fails
- Histogram + fitted PDF overlay
- Multi-height comparison plots

**Source**: Julia `Weibull.jl` (337 lines)

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
1. `WeibullSchema` - dataframely schema
2. `WeibullFitter` - domain service with MLE + MoM
3. `SingleMastWeibullParametersAtom` - parameter table
4. `SingleMastWeibullDistributionAtom` - histogram + PDF per height
5. `SingleMastWeibullMultiHeightAtom` - combined distribution plot
6. `WeibullAnalysisToAtoms` - converter
7. Tests

---

## Verification Strategy

TDD: Test fitting algorithms, fallback logic, visualization generation.

---

## Task Dependency Graph

| Task | Depends On | Reason |
|------|-----------|--------|
| 1. WeibullSchema | None | Independent |
| 2. WeibullFitter | Task 1 | Uses schema for validation |
| 3. SingleMastWeibullParametersAtom | Tasks 1,2 | Needs schema + fitter |
| 4. SingleMastWeibullDistributionAtom | Tasks 1,2 | Needs schema + fitter |
| 5. SingleMastWeibullMultiHeightAtom | Tasks 1,2 | Needs schema + fitter |
| 6. WeibullAnalysisToAtoms | Tasks 3-5 | Needs all atoms |
| 7. Tests | Tasks 1-6 | Tests all components |

## Parallel Execution Graph

```
Wave 1 (Foundation - Sequential):
├── Task 1: WeibullSchema [quick]
└── Task 2: WeibullFitter [unspecified-high]
    (depends: 1)

Wave 2 (Atoms - Parallel):
├── Task 3: SingleMastWeibullParametersAtom [quick]
├── Task 4: SingleMastWeibullDistributionAtom [visual-engineering]
└── Task 5: SingleMastWeibullMultiHeightAtom [visual-engineering]
    (depends: 1,2)

Wave 3 (Integration - Sequential):
├── Task 6: WeibullAnalysisToAtoms [quick]
│   (depends: 3,4,5)
└── Task 7: Tests [unspecified-high]
    (depends: 1-6)

Wave FINAL (Verification - Parallel):
├── F1: Plan compliance [oracle]
├── F2: Code quality [unspecified-high]
├── F3: Visual QA [unspecified-high]
└── F4: Integration [deep]

Critical Path: 1 → 2 → (3,4,5 parallel) → 6 → 7
Parallel Speedup: 40% (Wave 2)
Max Concurrent: 3 (Wave 2)
```

## Agent Dispatch Summary

| Wave | Tasks | Agent Profile |
|------|-------|---------------|
| 1 | 2 | quick → unspecified-high |
| 2 | 3 | quick, visual-engineering x2 |
| 3 | 2 | quick, unspecified-high |
| FINAL | 4 | oracle, unspecified-high x2, deep |

---

## TODOs

- [x] 1. WeibullSchema

  **What to do**:
  Add Weibull schema to `packages/cleanmast/src/cleanmast/subdomains/reporting/value_objects/single_mast/schemas.py`.

  ```python
  class WeibullSchema(dy.Schema):
      """Schema for Weibull distribution fitting results."""
      height: dy.Float64() = dy.Field(ge=0)
      interpolation_marker: dy.String() | None
      shape_k: dy.Float64() = dy.Field(ge=0)
      scale_c: dy.Float64() = dy.Field(ge=0)
      mean_speed: dy.Float64() = dy.Field(ge=0)
      bin_centers: dy.List(dy.Float64())
      observed_density: dy.List(dy.Float64())
      fitted_density: dy.List(dy.Float64())
  ```

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 2
  - **Blocked By**: None

  **Acceptance Criteria**:
  - [ ] Schema class defined with all fields
  - [ ] Constraints (ge=0) applied

  **QA Scenario**:
  ```
  Scenario: Schema validation
    Tool: Python REPL
    Steps:
      1. from cleanmast.subdomains.reporting.value_objects.single_mast.schemas import WeibullSchema
      2. assert WeibullSchema.height.dtype == dy.Float64()
    Expected: No ImportError
    Evidence: REPL output
  ```

  **Commit**: YES - `feat(schemas): add WeibullSchema`

- [x] 2. WeibullFitter

  **What to do**:
  Create `packages/cleanmast/src/cleanmast/subdomains/analysis/services/weibull_fitter.py`.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Tasks 3-7
  - **Blocked By**: Task 1

  **Acceptance Criteria**:
  - [ ] MLE fitting with scipy.optimize
  - [ ] MoM fallback implemented
  - [ ] Returns AnalysisResult[WeibullSchema]

  **QA Scenarios**:
  ```
  Scenario: MLE fitting accuracy
    Tool: Bash (pytest)
    Steps:
      1. uv run pytest tests/analysis/test_weibull_fitter.py::TestWeibullFitter::test_mle_fitting -v
    Expected: k, c within 5% of expected values
    Evidence: pytest output

  Scenario: MoM fallback
    Tool: Bash (pytest)
    Steps:
      1. uv run pytest tests/analysis/test_weibull_fitter.py::TestWeibullFitter::test_method_of_moments_fallback -v
    Expected: Fallback triggers, returns valid params
    Evidence: pytest output

  Scenario: Insufficient data
    Tool: Bash (pytest)
    Steps:
      1. uv run pytest tests/analysis/test_weibull_fitter.py::TestWeibullFitter::test_insufficient_data -v
    Expected: Returns None for < 10 points
    Evidence: pytest output
  ```

  **Commit**: YES - `feat(analysis): add WeibullFitter`

- [x] 3. SingleMastWeibullParametersAtom

  **What to do**:
  Create `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/weibull_parameters.py`.
  
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

  **Recommended Agent Profile**:
  - **Category**: `quick`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with 4,5)
  - **Blocked By**: Tasks 1,2

  **QA Scenario**:
  ```
  Scenario: Parameters table
    Tool: Bash (pytest)
    Steps:
      1. uv run pytest tests/report/test_weibull_atoms.py::TestParametersAtom::test_render_table -v
    Expected: Valid Typst #table markup
    Evidence: pytest output
  ```

  **Commit**: YES - `feat(reporting): add Weibull parameters atom`

- [x] 4. SingleMastWeibullDistributionAtom

  **What to do**:
  Create `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/weibull_distribution.py`.
  
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with 3,5)
  - **Blocked By**: Tasks 1,2

  **QA Scenario**:
  ```
  Scenario: Distribution plot
    Tool: Bash (pytest)
    Steps:
      1. uv run pytest tests/report/test_weibull_atoms.py::TestDistributionAtom::test_render_image -v
    Expected: PNG created with histogram + line
    Evidence: pytest output + file check
  ```

  **Commit**: YES - `feat(reporting): add Weibull distribution atom`

- [x] 5. SingleMastWeibullMultiHeightAtom

  **What to do**:
  Create `packages/cleanmast/src/cleanmast/subdomains/reporting/entities/single_mast/weibull_multi.py`.
  
  **Note**: Per ddd-t-002, ReportAtoms ARE ENTITIES → belongs in `entities/`

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with 3,4)
  - **Blocked By**: Tasks 1,2

  **QA Scenario**:
  ```
  Scenario: Multi-height plot
    Tool: Bash (pytest)
    Steps:
      1. uv run pytest tests/report/test_weibull_atoms.py::TestMultiHeightAtom::test_render_image -v
    Expected: PNG with multiple lines, legend
    Evidence: pytest output + file check
  ```

  **Commit**: YES - `feat(reporting): add Weibull multi-height atom`

- [x] 6. WeibullAnalysisToAtoms

  **What to do**:
  Create `packages/cleanmast/src/cleanmast/subdomains/reporting/services/weibull_converter.py`.

  **Recommended Agent Profile**:
  - **Category**: `quick`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 7
  - **Blocked By**: Tasks 3,4,5

  **QA Scenario**:
  ```
  Scenario: Converter
    Tool: Bash (pytest)
    Steps:
      1. uv run pytest tests/report/test_weibull_converter.py -v
    Expected: 3 atoms from AnalysisResult
    Evidence: pytest output
  ```

  **Commit**: YES - `feat(reporting): add Weibull converter`

- [x] 7. Tests

  **What to do**:
  Create test files in `packages/cleanmast/tests/`.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: Tasks 1-6

  **QA Scenario**:
  ```
  Scenario: Full test suite
    Tool: Bash
    Steps:
      1. uv run pytest packages/cleanmast/tests/analysis/test_weibull_fitter.py -v
      2. uv run pytest packages/cleanmast/tests/report/test_weibull_atoms.py -v
    Expected: All pass, >90% coverage
    Evidence: pytest output
  ```

  **Commit**: YES - `test(weibull): add test suite`

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit** (oracle)
- [ ] F2. **Code Quality Review** (unspecified-high)
- [ ] F3. **Visual QA** (unspecified-high)
- [ ] F4. **Integration Check** (deep)

---

## Commit Strategy

1. `feat(schemas): add WeibullSchema`
2. `feat(analysis): add WeibullFitter`
3. `feat(reporting): add Weibull parameters atom`
4. `feat(reporting): add Weibull distribution atom`
5. `feat(reporting): add Weibull multi-height atom`
6. `feat(reporting): add Weibull converter`
7. `test(weibull): add test suite`

---

## Success Criteria

- [ ] MLE fitting converges
- [ ] MoM fallback works
- [ ] All 3 atoms render correctly
- [ ] Tests >90% coverage
