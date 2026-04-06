# Windows Path Handling Fix: Full Work Plan

## TL;DR

> **Fix Windows path handling in cleanmast package to use forward slashes consistently.**
>
> **Deliverables**:
> - Create utility module `cleanmast.infrastructure.path_utils` with `to_posix_path()` function
> - Create ADR `platform-001-cross-platform-paths.md` documenting the decision
> - Fix 19 files using `str(path)` instead of `path.as_posix()`
> - Update all path string conversions in configs, CLI output, and error messages
>
> **Estimated Effort**: Medium (2-3 waves, ~15 tasks)
> **Parallel Execution**: YES - independent file fixes
> **Critical Path**: Create utility → Update infrastructure → Update use cases → Update CLI

---

## Context

### Problem Statement
On Windows, `str(Path)` produces backslashes (`\`) which causes issues:
- **Config files**: Paths saved with backslashes break cross-platform compatibility
- **Logs/Output**: Backslashes are confusing and hard to read
- **Error messages**: Inconsistent path formatting
- **External tools**: Some tools expect forward slashes even on Windows

### Root Cause
Python's `pathlib.Path` uses OS-native separators:
- Linux/Mac: `/` (forward slash)
- Windows: `\\` (backslash)

When converting Path to string via `str()`, you get OS-specific separators.

### Solution
Use `path.as_posix()` consistently to ensure forward slashes (`/`) on all platforms.

### Files Affected
19 files found with `str(path)` pattern:
- 11 files in `application/` layer (use cases, commands)
- 5 files in `subdomains/` (infrastructure, configuration)
- 3 files in legacy `report/` directory

---

## Work Objectives

### Core Objective
Ensure all path string representations use forward slashes consistently across platforms by creating a utility function and applying it throughout the cleanmast package.

### Concrete Deliverables
1. Created: `packages/cleanmast/src/cleanmast/infrastructure/path_utils.py` with `to_posix_path()`
2. Created: `packages/cleanmast/adr/platform-001-cross-platform-paths.md`
3. Fixed: All 19 files using `str(path)` → `to_posix_path(path)`
4. Updated: Config serialization to use posix paths
5. Updated: CLI output to display posix paths
6. Updated: Error messages with posix paths

### Definition of Done
- [ ] `to_posix_path()` utility created and tested
- [ ] ADR created and documented
- [ ] All 19 files fixed
- [ ] `uv run pytest packages/cleanmast/tests/ -v` passes
- [ ] `python -c "import cleanmast; print('OK')"` succeeds
- [ ] Paths display with forward slashes on Windows

### Must Have
- Create reusable utility function (not inline fixes)
- Document the decision in an ADR
- Fix all occurrences systematically
- Preserve existing functionality

### Must NOT Have (Guardrails)
- NO changes to file system operations (only string representation)
- NO changes to Path object creation
- NO breaking changes to public APIs
- NO inline `as_posix()` calls (use utility function)

---

## ADR Reference

### Primary ADR
- **platform-001-cross-platform-paths.md** (to be created)
  - Constraint: Always use `as_posix()` for path string representation
  - Rationale: Cross-platform consistency, readability
  - Anti-pattern: `str(path)` for display/config

### Related ADRs
- **persistence-001-parquet-storage.md**: File I/O operations
- **structure-001-subdomain-layout.md**: Where to place utility module

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation - Must Complete First):
├── Task 1: Create path_utils.py utility module
├── Task 2: Create ADR platform-001-cross-platform-paths.md
└── Task 3: Add tests for path_utils

Wave 2 (Infrastructure - Parallel):
├── Task 4: Fix subdomains/assessment/infrastructure/compiler.py
├── Task 5: Fix subdomains/assessment/infrastructure/renderer.py
├── Task 6: Fix subdomains/configuration/value_objects/wt_timeseries_config.py
├── Task 7: Fix subdomains/dataprocessing/commands/recommend.py
└── Task 8: Fix report/compiler.py, report/renderer.py (legacy)

Wave 3 (Application Layer - Parallel):
├── Task 9: Fix application/usecases/recommend_fill_heights.py
├── Task 10: Fix application/usecases/execute_fill_heights.py
├── Task 11: Fix application/usecases/generate_report.py
├── Task 12: Fix application/usecases/recommend_wt_timeseries.py
└── Task 13: Fix application/commands/generate_timeseries_report.py

Wave 4 (CLI & Output - Parallel):
├── Task 14: Fix cli.py
├── Task 15: Fix adapters/cli/ files (4 files)
└── Task 16: Fix wt_timeseries/ files (2 files)

Wave 5 (Final Verification):
├── Task 17: Run full test suite
├── Task 18: Verify paths display correctly
└── Task 19: Type check verification

Wave FINAL (4 Parallel Reviews):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: Task 1-3 → Task 4-8 → Task 9-13 → Task 14-16 → Task 17 → F1-F4
```

### Agent Dispatch Summary

- **Wave 1**: 3 tasks → `deep` (foundation, utility design)
- **Wave 2**: 5 tasks → `quick` (infrastructure fixes)
- **Wave 3**: 5 tasks → `quick` (application layer fixes)
- **Wave 4**: 3 tasks → `quick` (CLI fixes)
- **Wave 5**: 3 tasks → `unspecified-high` (verification)
- **Final**: 4 tasks → `oracle`, `unspecified-high` ×2, `deep`

---

## TODOs

- [x] **1. Create path_utils.py utility module**

  **What to do**:
  - Create `packages/cleanmast/src/cleanmast/infrastructure/path_utils.py`
  - Implement `to_posix_path(path: Union[str, Path]) -> str` function
  - Handle both str and Path inputs
  - Add docstring with examples
  - Add `__all__` export
  
  **Must NOT do**:
  - Do NOT create the module elsewhere (must be in infrastructure/)
  - Do NOT add dependencies beyond pathlib
  
  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Reason**: Designing utility function requires careful API design
  
  **Parallelization**:
  - **Can Run In Parallel**: NO (foundation task)
  - **Blocks**: Task 4-19 (all fixes use this utility)
  
  **References**:
  - ADR: `platform-001-cross-platform-paths.md` (to be created)
  - Pattern: `cleanmast/infrastructure/` for cross-cutting utilities
  
  **Acceptance Criteria**:
  - [ ] Module created at correct path
  - [ ] Function handles str input
  - [ ] Function handles Path input
  - [ ] Function returns forward-slash paths
  - [ ] Docstring with examples
  
  **QA Scenarios**:
  ```python
  # Test cases
  to_posix_path("C:\\Users\\test") -> "C:/Users/test"
  to_posix_path(Path("C:/Users/test")) -> "C:/Users/test"
  to_posix_path(Path("/home/user")) -> "/home/user"
  ```
  
  **Commit**: YES (separate commit for utility)
  - Message: `feat(infrastructure): add to_posix_path utility for cross-platform paths`
  - Files: `packages/cleanmast/src/cleanmast/infrastructure/path_utils.py`

- [x] **2. Create ADR platform-001-cross-platform-paths.md**

  **What to do**:
  - Create ADR documenting cross-platform path decision
  - Follow ADR template from other ADRs
  - Include constraint, rationale, anti-patterns
  - Reference persistence-001 for file operations context
  
  **Must NOT do**:
  - Do NOT skip the ADR (required for architectural decisions)
  
  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Reason**: Documentation task
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 1, 3)
  
  **References**:
  - Template: `packages/cleanmast/adr/persistence-001-parquet-storage.md`
  - Related: `persistence-001` for file operations context
  
  **Acceptance Criteria**:
  - [ ] ADR created with proper format
  - [ ] Constraint documented
  - [ ] Anti-pattern documented (`str(path)`)
  - [ ] Example code provided
  
  **Commit**: YES (separate commit)
  - Message: `docs(adr): add platform-001-cross-platform-paths`
  - Files: `packages/cleanmast/adr/platform-001-cross-platform-paths.md`

- [x] **3. Add tests for path_utils**

  **What to do**:
  - Create `packages/cleanmast/tests/infrastructure/test_path_utils.py`
  - Test all input types (str, Path, Windows, Unix)
  - Test edge cases (empty string, relative paths)
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 1, 2)
  - **Blocked By**: Task 1 (utility must exist)
  
  **Acceptance Criteria**:
  - [ ] Test file created
  - [ ] All test cases pass
  - [ ] Coverage for edge cases
  
  **QA Scenarios**:
  ```bash
  pytest packages/cleanmast/tests/infrastructure/test_path_utils.py -v
  ```
  
  **Commit**: YES (group with Task 1, 2)
  - Message: `test(infrastructure): add tests for path_utils`
  - Files: `packages/cleanmast/tests/infrastructure/test_path_utils.py`

- [x] **4. Fix subdomains/assessment/infrastructure/compiler.py**

  **What to do**:
  - Lines 46, 85, 86: Replace `str(typ_path)` with `to_posix_path(typ_path)`
  - Import `to_posix_path` from `cleanmast.infrastructure.path_utils`
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 5-8)
  - **Blocked By**: Task 1 (utility must exist)
  
  **References**:
  - File: `packages/cleanmast/src/cleanmast/subdomains/assessment/infrastructure/compiler.py`
  - ADR: `platform-001-cross-platform-paths.md`
  
  **Acceptance Criteria**:
  - [ ] Import added
  - [ ] Lines 46, 85, 86 fixed
  - [ ] Tests still pass

- [ ] **5. Fix subdomains/assessment/infrastructure/renderer.py**

  **What to do**:
  - Lines 196, 198, 200: Already use `as_posix()` - verify correct
  - Check if any other locations need fixing
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 4, 6-8)
  
  **Acceptance Criteria**:
  - [ ] File reviewed
  - [ ] Already correct (lines 196, 198, 200) OR fixed
  - [ ] Tests pass

- [ ] **6. Fix subdomains/configuration/value_objects/wt_timeseries_config.py**

  **What to do**:
  - Line 63: Replace `str(config_dir / input_path)` with `to_posix_path(config_dir / input_path)`
  - Add import
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 4-5, 7-8)
  
  **Acceptance Criteria**:
  - [ ] Line 63 fixed
  - [ ] Import added
  - [ ] Tests pass

- [ ] **7. Fix subdomains/dataprocessing/commands/recommend.py**

  **What to do**:
  - Line 135: Replace `str(fill_heights_config_path)` with `to_posix_path(fill_heights_config_path)`
  - Add import
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 4-6, 8)
  
  **Acceptance Criteria**:
  - [ ] Line 135 fixed
  - [ ] Import added
  - [ ] Tests pass

- [ ] **8. Fix report/compiler.py and report/renderer.py (legacy)**

  **What to do**:
  - `report/compiler.py`: Similar fixes as assessment version
  - `report/renderer.py`: Similar fixes as assessment version
  - These are legacy files but still need fixing
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 4-7)
  
  **Acceptance Criteria**:
  - [ ] Both files fixed
  - [ ] Imports added
  - [ ] Tests pass (or legacy failures documented)

- [ ] **9-16. Fix Application Layer and CLI Files**

  **Files to Fix**:
  - Task 9: `application/usecases/recommend_fill_heights.py` (lines 89, 96)
  - Task 10: `application/usecases/execute_fill_heights.py` (lines 54, 56)
  - Task 11: `application/usecases/generate_report.py` (line 84)
  - Task 12: `application/usecases/recommend_wt_timeseries.py` (line 109)
  - Task 13: `application/commands/generate_timeseries_report.py` (line 377)
  - Task 14: `cli.py` (lines 33, 35, 52)
  - Task 15: `adapters/cli/` files (4 files)
  - Task 16: `wt_timeseries/` files (2 files)
  
  **Pattern for all**:
  1. Add import: `from cleanmast.infrastructure.path_utils import to_posix_path`
  2. Replace `str(path_obj)` with `to_posix_path(path_obj)`
  3. Verify tests pass
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (within wave)
  - **Blocked By**: Task 1 (utility must exist)
  
  **Commit Strategy**:
  - Group by layer: `fix(application): use posix paths in use cases`
  - Or individual commits per file

- [ ] **17. Run full test suite**

  **What to do**:
  - Run `uv run pytest packages/cleanmast/tests/ -v`
  - Verify no regressions
  - Document any pre-existing failures
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  
  **Acceptance Criteria**:
  - [ ] Tests pass (or pre-existing failures documented)
  - [ ] No new failures from our changes

- [ ] **18. Verify paths display correctly**

  **What to do**:
  - Run CLI commands to verify path output
  - Check that paths show with forward slashes
  - Example: `python -c "from pathlib import Path; from cleanmast.infrastructure.path_utils import to_posix_path; print(to_posix_path(Path('C:/test/path')))"`
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  
  **Acceptance Criteria**:
  - [ ] Paths display with forward slashes
  - [ ] No backslashes in output

- [ ] **19. Type check verification**

  **What to do**:
  - Run `uv run ty check packages/cleanmast`
  - Verify no type errors from our changes
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  
  **Acceptance Criteria**:
  - [ ] Type check passes (or pre-existing errors documented)

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE.

- [ ] **F1. Plan Compliance Audit** — `oracle`
  
  Verify:
  - Utility module created in correct location
  - ADR created and documented
  - All 19 files fixed
  - Tests pass
  
  Output: `Must Have [6/6] | Must NOT Have [4/4] | VERDICT: APPROVE/REJECT`

- [ ] **F2. Code Quality Review** — `unspecified-high`
  
  Verify:
  - Type hints on utility function
  - Proper docstrings
  - No `str(path)` remaining in fixed files
  - Import style consistent
  
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | VERDICT`

- [ ] **F3. Real Manual QA** — `unspecified-high`
  
  Execute:
  - Run CLI commands with paths
  - Verify output shows forward slashes
  - Check config files use forward slashes
  
  Output: `Scenarios [3/3 pass] | VERDICT`

- [ ] **F4. Scope Fidelity Check** — `deep`
  
  Verify:
  - Only string representation changed
  - File operations unchanged
  - No breaking API changes
  - All path fixes use utility function
  
  Output: `Scope [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

**Wave 1 (Foundation)**:
- Commit 1: `feat(infrastructure): add to_posix_path utility for cross-platform paths`
- Commit 2: `docs(adr): add platform-001-cross-platform-paths`
- Commit 3: `test(infrastructure): add tests for path_utils`

**Wave 2 (Infrastructure)**:
- Commit 4: `fix(infrastructure): use posix paths in assessment compiler and renderer`
- Commit 5: `fix(configuration): use posix paths in wt_timeseries_config`
- Commit 6: `fix(dataprocessing): use posix paths in recommend command`
- Commit 7: `fix(report): use posix paths in legacy report files`

**Wave 3 (Application)**:
- Commit 8: `fix(application): use posix paths in use cases`

**Wave 4 (CLI)**:
- Commit 9: `fix(cli): use posix paths in CLI output and adapters`

---

## Success Criteria

### Verification Commands
```bash
# Test suite
uv run pytest packages/cleanmast/tests/ -v

# Type check
uv run ty check packages/cleanmast

# Import test
python -c "from cleanmast.infrastructure.path_utils import to_posix_path; print('OK')"

# Path verification
python -c "from pathlib import Path; from cleanmast.infrastructure.path_utils import to_posix_path; print(to_posix_path(Path('C:/test')))"
# Expected: C:/test (forward slashes on all platforms)
```

### Final Checklist
- [ ] Utility function created and tested
- [ ] ADR created
- [ ] All 19 files fixed
- [ ] Tests pass
- [ ] Paths display with forward slashes
- [ ] Type check clean
