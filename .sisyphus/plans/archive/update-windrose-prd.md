# Work Plan: Update WindRose PRD with Additional Atoms

## TL;DR

Review the existing WindRose PRD and add **missing atom types** identified from Julia code analysis. WindRose and WindTemporal already have some Python implementation - we need to ensure the PRD matches what's there and adds what's missing.

**Source PRD**: `.sisyphus/notepads/prds/windrose-analysis-migration.md`

---

## Context

The existing WindRose PRD was drafted based on Julia code analysis. However, some atoms may already be partially implemented in Python. This task is to:

1. Review existing Python implementation in `packages/cleanmast/`
2. Compare with Julia `WindRose.jl` functionality
3. Identify gaps between PRD and implementation
4. Update PRD to reflect actual needed atoms

### Already Implemented (check first)

Look in:
- `packages/cleanmast/src/cleanmast/subdomains/reporting/value_objects/single_mast/`
- `packages/cleanmast/src/cleanmast/subdomains/analysis/services/wind_rose_calculator.py`

---

## Work Objectives

### Deliverable
Updated PRD file with complete atom specification

### Must Include
1. **Audit existing implementation** - What's already there?
2. **Gap analysis** - What's missing vs Julia code?
3. **Updated atom list** - Complete specification
4. **New atoms to add** (if any):
   - Monthly wind rose grids (3x4)
   - Per-height wind roses
   - Combined frequency+power sections

### Definition of Done
```bash
# PRD is updated
head -100 .sisyphus/notepads/prds/windrose-analysis-migration.md

# Shows updated atom specifications
# Lists all required atoms with render methods
```

---

## Verification Strategy

Review-based verification:
- Check Python implementation exists
- Verify Julia feature parity
- Ensure all render methods specified

---

## Execution Strategy

Sequential tasks:

### Wave 1: Audit & Update
- Task 1: Audit existing Python implementation
- Task 2: Update PRD with missing atoms

---

## TODOs

- [ ] 1. Audit existing WindRose Python implementation

  **What to do**:
  - Read `packages/cleanmast/src/cleanmast/subdomains/reporting/value_objects/single_mast/wind_rose.py`
  - Read `packages/cleanmast/src/cleanmast/subdomains/analysis/services/wind_rose_calculator.py`
  - Read `packages/cleanmast/tests/report/test_atoms.py` (wind rose tests)
  - List all currently implemented atoms
  - Document their render methods
  - Note what's missing vs Julia code

  **Must NOT do**:
  - Implement anything (audit only)
  - Delete existing code

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 2
  - **Blocked By**: None

  **References**:
  - Julia source: `CleanMastProject/src/ReportTimeSeries/WindRose.jl`
  - Python atoms: `packages/cleanmast/src/cleanmast/subdomains/reporting/value_objects/single_mast/`
  - Tests: `packages/cleanmast/tests/report/test_atoms.py`

  **Acceptance Criteria**:
  - [ ] List of existing atoms documented
  - [ ] Render methods for each identified
  - [ ] Gap analysis completed
  - [ ] Missing atoms identified

  **QA Scenarios**:
  ```
  Scenario: Verify audit completion
    Tool: Bash
    Steps:
      1. grep -n "class.*Atom" packages/cleanmast/src/cleanmast/subdomains/reporting/value_objects/single_mast/wind_rose.py
      2. Count existing atom classes
      3. Compare with Julia functionality
    Expected Result: Complete inventory of existing vs needed
    Evidence: Document listing gaps
  ```

  **Commit**: NO (audit is research, not implementation)

- [ ] 2. Update WindRose PRD with additional atoms

  **What to do**:
  - Edit `.sisyphus/notepads/prds/windrose-analysis-migration.md`
  - Add missing atom specifications:
    * `SingleMastMonthlyWindRoseGridAtom` - 3x4 monthly grid
    * `SingleMastWindRoseSummaryAtom` - Text summary
    * Any other gaps identified in audit
  - Update render method specifications
  - Add analysis → atom conversion logic
  - Ensure consistency with existing Python code

  **Must NOT do**:
  - Remove existing specifications
  - Change already-implemented interfaces

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: None
  - **Blocked By**: Task 1

  **References**:
  - Audit results from Task 1
  - Julia: `CleanMastProject/src/ReportTimeSeries/WindRose.jl`
  - Existing PRD: `.sisyphus/notepads/prds/windrose-analysis-migration.md`

  **Acceptance Criteria**:
  - [ ] PRD updated with all missing atoms
  - [ ] Render methods specified for each
  - [ ] Conversion logic documented
  - [ ] Consistency with existing code verified

  **QA Scenarios**:
  ```
  Scenario: Verify PRD completeness
    Tool: Bash
    Steps:
      1. grep "class.*Atom" .sisyphus/notepads/prds/windrose-analysis-migration.md | wc -l
      2. Check each atom has renderImage, renderTable, renderSummary
    Expected Result: All atoms fully specified
    Evidence: grep output showing complete methods
  ```

  **Commit**: YES
  - Message: `docs(prd): update windrose analysis with complete atom specifications`
  - Files: `.sisyphus/notepads/prds/windrose-analysis-migration.md`
  - Pre-commit: None (documentation)

---

## Final Verification Wave

- [ ] F1. **Plan Compliance** - All atoms from Julia accounted for
- [ ] F2. **Consistency Check** - PRD matches existing Python
- [ ] F3. **Completeness** - All render methods specified
- [ ] F4. **Ready for Implementation** - PRD is actionable

---

## Commit Strategy

- **1**: `docs(prd): update windrose analysis with complete atom specifications` - Updated PRD

---

## Success Criteria

- [ ] Audit identifies all gaps
- [ ] PRD updated with missing atoms
- [ ] Specification is complete and consistent
- [ ] Ready for implementation work
