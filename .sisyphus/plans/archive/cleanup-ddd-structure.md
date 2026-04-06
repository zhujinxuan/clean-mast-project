# DDD Architecture Cleanup: Remove Orphaned Code & Align Test Structure

## TL;DR

> **Clean up legacy artifacts from DDD migration !82 and align test structure with subdomain architecture.**
>
> **Deliverables**:
> - Delete orphaned `fill_heights/` and `io/` source directories
> - Move `wt_timeseries/` to subdomain structure (or delete if unused)
> - Reorganize test directories to mirror DDD subdomain structure
> - Update imports in ONE file (`generate_timeseries_report.py`)
>
> **Estimated Effort**: Medium (3-4 waves, ~15 tasks)
> **Parallel Execution**: YES - independent deletions and moves
> **Critical Path**: Fix import → Delete orphaned → Move tests → Verify

---

## Context

### Original Discovery
During the recent `analysis`/`reporting` → `assessment` subdomain merge, we discovered the DDD architecture has legacy artifacts from migration `!82` ("refactor: Waves 1-10 - DDD structure migration"):

1. **Orphaned Source Directories**: `fill_heights/`, `io/` exist at top-level but are NOT imported anywhere
2. **Duplicate Code**: `io/` is identical to `subdomains/dataingestion/infrastructure/`
3. **Misaligned Test Structure**: Tests exist in legacy locations (`tests/fill_heights/`, `tests/io/`, `tests/models/`) instead of matching DDD structure
4. **Facade Ambiguity**: `wt_timeseries/` imports FROM subdomains but its role is unclear

### Metis Validation
- ✅ Confirmed: Only ONE file imports from `cleanmast.io` (fixable)
- ✅ Confirmed: ZERO imports from `cleanmast.fill_heights`
- ⚠️ Unknown: Need to verify `wt_timeseries` import status before deciding fate

---

## Work Objectives

### Core Objective
Eliminate architectural drift by removing orphaned code and aligning all tests with the established DDD subdomain structure.

### Concrete Deliverables
1. Deleted: `packages/cleanmast/src/cleanmast/fill_heights/` (entire directory)
2. Deleted: `packages/cleanmast/src/cleanmast/io/` (entire directory)
3. Resolved: `packages/cleanmast/src/cleanmast/wt_timeseries/` (delete OR move to subdomains)
4. Moved: `tests/fill_heights/` → `tests/subdomains/dataprocessing/services/height_filling/`
5. Moved: `tests/io/` → `tests/subdomains/dataingestion/infrastructure/`
6. Moved: `tests/models/` → `tests/subdomains/configuration/` and `tests/subdomains/dataingestion/`
7. Created: Missing test directory structure for `configuration/`, `pipeline/`, `application/`, `adapters/`
8. Fixed: Import in `generate_timeseries_report.py:18`

### Definition of Done
- [ ] `uv run pytest packages/cleanmast/tests/ -v` passes (all 594 tests)
- [ ] `uv run ty check packages/cleanmast` shows zero import errors
- [ ] `python -c "import cleanmast; print('OK')"` succeeds
- [ ] Git status shows only expected deletions and moves (no untracked orphaned files)

### Must Have
- Preserve all test functionality (tests move, not deleted)
- Preserve conftest.py fixtures when moving test directories
- Fix the ONE breaking import BEFORE deleting io/

### Must NOT Have (Guardrails)
- NO logic changes to working code (pure reorganization)
- NO test deletions (only moves)
- NO import changes beyond the ONE required fix
- NO changes to `tests/assessment/` (already correctly structured)

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest already configured)
- **Automated tests**: Tests-after (moving existing tests)
- **Framework**: pytest
- **Test count**: 1039 test cases across 49 files

### QA Policy
Every task MUST include agent-executed QA scenarios:
- **File operations**: Verify files exist at destination, don't exist at source
- **Import checks**: `python -c "import X"` must succeed after moves
- **Test execution**: `pytest path/to/tests -v` must pass
- **Type checking**: `ty check` must pass after import changes

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Discovery - Must Complete First):
├── Task 1: Verify wt_timeseries import status
├── Task 2: Compare io/ modules for differences
└── Task 3: Inventory test fixtures (conftest.py files)

Wave 2 (Fix Import - SINGLE CRITICAL PATH):
└── Task 4: Fix generate_timeseries_report.py import

Wave 3 (Delete Orphaned - Parallel):
├── Task 5: Delete src/fill_heights/
├── Task 6: Delete src/io/
└── Task 7: Handle src/wt_timeseries/ (delete OR move)

Wave 4 (Move Tests - Parallel Groups):
├── Task 8: Move tests/fill_heights/ → subdomains/dataprocessing/
├── Task 9: Move tests/io/ → subdomains/dataingestion/
└── Task 10: Move tests/models/ → appropriate subdomains/

Wave 5 (Create Structure - Parallel):
├── Task 11: Create tests/subdomains/configuration/
├── Task 12: Create tests/subdomains/pipeline/
├── Task 13: Create tests/application/
└── Task 14: Create tests/adapters/

Wave 6 (Final Verification):
├── Task 15: Run full test suite
├── Task 16: Type check verification
└── Task 17: Import smoke test

Wave FINAL (4 Parallel Reviews):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: Task 1-3 → Task 4 → Task 5-7 → Task 8-10 → Task 15 → F1-F4
```

### Agent Dispatch Summary

- **Wave 1**: 3 tasks → `deep` (discovery)
- **Wave 2**: 1 task → `quick` (single file edit)
- **Wave 3**: 3 tasks → `quick` (deletions)
- **Wave 4**: 3 tasks → `quick` (moves, but careful with conftest.py)
- **Wave 5**: 4 tasks → `quick` (directory creation)
- **Wave 6**: 3 tasks → `unspecified-high` (verification)
- **Final**: 4 tasks → `oracle`, `unspecified-high` ×2, `deep`

---

## TODOs

- [x] **1. DISCOVERY: Verify wt_timeseries import status**

  **What to do**:
  - Run grep to find ANY imports from `cleanmast.wt_timeseries`
  - Run grep to find ANY relative imports of `wt_timeseries`
  - Check CLI registration in `cli.py` for wt_timeseries commands
  
  **Must NOT do**:
  - Do NOT delete or move wt_timeseries yet (decision pending discovery)
  
  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Reason**: Investigation task requiring careful analysis
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 2, 3)
  - **Blocks**: Task 7 (wt_timeseries handling)
  
  **References**:
  - `packages/cleanmast/src/cleanmast/cli.py` - Check command registration
  - `packages/cleanmast/src/cleanmast/wt_timeseries/` - Check imports
  
  **Acceptance Criteria**:
  - [ ] Document: Count of imports from `cleanmast.wt_timeseries`
  - [ ] Document: CLI commands registered from wt_timeseries
  - [ ] Decision input: Keep as facade, move to subdomains, or delete
  
  **QA Scenarios**:
  ```
  Scenario: Verify wt_timeseries import status
    Tool: Bash (grep)
    Steps:
      1. grep -r "from cleanmast.wt_timeseries" packages/cleanmast/src
      2. grep -r "import cleanmast.wt_timeseries" packages/cleanmast/src
      3. grep -r "wt_timeseries" packages/cleanmast/src/cleanmast/cli.py
    Expected Result: Document findings for decision
  ```
  
  **Commit**: NO (discovery only)

- [x] **2. DISCOVERY: Compare io/ modules for differences**

  **What to do**:
  - Run diff between `cleanmast/io/timeseries_io.py` and `subdomains/dataingestion/infrastructure/timeseries_io.py`
  - Verify the ONLY difference is import style (relative vs absolute)
  - Check if any other files exist in io/ that don't exist in subdomain
  
  **Must NOT do**:
  - Do NOT assume they are identical without checking
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Simple comparison task
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 1, 3)
  - **Blocks**: Task 6 (delete io/)
  
  **References**:
  - `packages/cleanmast/src/cleanmast/io/timeseries_io.py`
  - `packages/cleanmast/src/cleanmast/subdomains/dataingestion/infrastructure/timeseries_io.py`
  
  **Acceptance Criteria**:
  - [ ] Diff output shows only import path differences
  - [ ] Document: Confirmation that io/ can be safely deleted
  
  **QA Scenarios**:
  ```
  Scenario: Compare io modules
    Tool: Bash (diff)
    Steps:
      1. diff packages/cleanmast/src/cleanmast/io/timeseries_io.py packages/cleanmast/src/cleanmast/subdomains/dataingestion/infrastructure/timeseries_io.py
    Expected Result: Only import statement differences
  ```
  
  **Commit**: NO (discovery only)

- [x] **3. DISCOVERY: Inventory test fixtures (conftest.py files)**

  **What to do**:
  - Find all `conftest.py` files in test directories being moved
  - Check for fixture dependencies between test directories
  - Document which fixtures need to be preserved/moved
  
  **Must NOT do**:
  - Do NOT move tests without preserving conftest.py
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: File inventory task
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 1, 2)
  - **Blocks**: Task 8, 9, 10 (test moves)
  
  **References**:
  - `packages/cleanmast/tests/fill_heights/conftest.py`
  - `packages/cleanmast/tests/wt_timeseries/conftest.py`
  - `packages/cleanmast/tests/conftest.py` (root level - stays)
  
  **Acceptance Criteria**:
  - [ ] Document: All conftest.py files found
  - [ ] Document: Fixtures defined in each
  - [ ] Document: Cross-directory fixture dependencies
  
  **QA Scenarios**:
  ```
  Scenario: Inventory conftest files
    Tool: Bash (find + grep)
    Steps:
      1. find packages/cleanmast/tests -name "conftest.py"
      2. grep -h "^def " packages/cleanmast/tests/fill_heights/conftest.py
    Expected Result: Complete inventory list
  ```
  
  **Commit**: NO (discovery only)

- [x] **4. CRITICAL: Fix generate_timeseries_report.py import**

  **What to do**:
  - Edit `packages/cleanmast/src/cleanmast/application/commands/generate_timeseries_report.py:18`
  - Change: `from cleanmast.io.timeseries_io import load_timeseries`
  - To: `from cleanmast.subdomains.dataingestion.infrastructure import load_timeseries`
  - Verify import path is correct by checking subdomain exports
  
  **Must NOT do**:
  - Do NOT delete io/ directory BEFORE this fix
  - Do NOT change any other imports
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Single file edit, well-defined
  
  **Parallelization**:
  - **Can Run In Parallel**: NO (must complete before Task 6)
  - **Blocked By**: Task 2 (verify io/ is duplicate)
  - **Blocks**: Task 6 (delete io/)
  
  **References**:
  - `packages/cleanmast/src/cleanmast/application/commands/generate_timeseries_report.py:18`
  - `packages/cleanmast/src/cleanmast/subdomains/dataingestion/infrastructure/__init__.py` - verify load_timeseries is exported
  
  **Acceptance Criteria**:
  - [ ] Import statement updated
  - [ ] `python -c "from cleanmast.application.commands.generate_timeseries_report import *"` succeeds
  - [ ] `ty check packages/cleanmast/src/cleanmast/application/commands/generate_timeseries_report.py` passes
  
  **QA Scenarios**:
  ```
  Scenario: Import fix verification
    Tool: Bash
    Steps:
      1. python -c "from cleanmast.application.commands.generate_timeseries_report import generate_timeseries_report"
      2. uv run ty check packages/cleanmast/src/cleanmast/application/commands/generate_timeseries_report.py
    Expected Result: Both commands succeed
  ```
  
  **Commit**: YES
  - Message: `fix(commands): update import from cleanmast.io to subdomain`
  - Files: `packages/cleanmast/src/cleanmast/application/commands/generate_timeseries_report.py`

- [x] **5. DELETE: Remove orphaned src/fill_heights/ directory**

  **What to do**:
  - Verify NO imports from `cleanmast.fill_heights` anywhere in codebase
  - Delete entire `packages/cleanmast/src/cleanmast/fill_heights/` directory
  - Verify deletion with git status
  
  **Must NOT do**:
  - Do NOT delete if any imports found (verify first)
  - Do NOT delete tests (Task 8 handles test moves)
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Simple deletion after verification
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 6, 7)
  - **Blocked By**: None (verification independent)
  
  **References**:
  - `packages/cleanmast/src/cleanmast/fill_heights/` (entire directory)
  
  **Acceptance Criteria**:
  - [ ] Directory deleted
  - [ ] `grep -r "cleanmast.fill_heights" packages/cleanmast/src` returns zero
  - [ ] `python -c "import cleanmast"` still succeeds
  
  **QA Scenarios**:
  ```
  Scenario: Verify fill_heights deletion
    Tool: Bash
    Steps:
      1. ls packages/cleanmast/src/cleanmast/fill_heights 2>&1 | grep "No such file"
      2. grep -r "from cleanmast.fill_heights" packages/cleanmast/src || echo "No imports found"
      3. python -c "import cleanmast"
    Expected Result: Directory gone, no imports, import succeeds
  ```
  
  **Commit**: YES (group with Task 6)
  - Message: `refactor: remove orphaned fill_heights source directory`
  - Files: `packages/cleanmast/src/cleanmast/fill_heights/`

- [x] **6. DELETE: Remove duplicate src/io/ directory**

  **What to do**:
  - Verify Task 4 is complete (import fixed)
  - Delete entire `packages/cleanmast/src/cleanmast/io/` directory
  - Verify no remaining imports to cleanmast.io
  
  **Must NOT do**:
  - Do NOT delete before Task 4 (would break imports)
  - Do NOT delete tests (Task 9 handles test moves)
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Simple deletion
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 5, 7)
  - **Blocked By**: Task 4 (import fix)
  
  **References**:
  - `packages/cleanmast/src/cleanmast/io/` (entire directory)
  
  **Acceptance Criteria**:
  - [ ] Directory deleted
  - [ ] `grep -r "cleanmast.io" packages/cleanmast/src` returns zero
  - [ ] `python -c "import cleanmast"` succeeds
  
  **QA Scenarios**:
  ```
  Scenario: Verify io deletion
    Tool: Bash
    Steps:
      1. ls packages/cleanmast/src/cleanmast/io 2>&1 | grep "No such file"
      2. grep -r "from cleanmast.io" packages/cleanmast/src || echo "No imports found"
      3. python -c "from cleanmast.subdomains.dataingestion.infrastructure import load_timeseries; print('OK')"
    Expected Result: Directory gone, no imports, subdomain import works
  ```
  
  **Commit**: YES (group with Task 5)
  - Message: `refactor: remove duplicate io module (using subdomain version)`
  - Files: `packages/cleanmast/src/cleanmast/io/`

- [x] **7. HANDLE: Resolve src/wt_timeseries/ directory**

  **DECISION: KEEP as facade layer**

  **Rationale**:
  wt_timeseries is actively used via CLI but not imported as a module. This is an intentional **facade pattern**:
  - `wt_timeseries/` provides CLI-friendly facade functions (`execute_wt_timeseries_cli`, `recommend_wt_timeseries_cli`)
  - Internal implementation uses subdomains (configuration, dataingestion, dataprocessing)
  - No direct module imports needed - CLI wiring handles access
  - Zero imports from `cleanmast.wt_timeseries` anywhere in codebase (verified)
  - CLI commands registered: `recommend wt-timeseries`, `wt-timeseries` (lines 69-70 in cli.py)

  **Files Verified**:
  - `packages/cleanmast/src/cleanmast/wt_timeseries/core.py` ✓
  - `packages/cleanmast/src/cleanmast/wt_timeseries/config.py` ✓
  - `packages/cleanmast/src/cleanmast/wt_timeseries/turbulence.py` ✓

  **CLI Registration Verified**:
  - Line 13-14: Imports `recommend_wt_timeseries_cli`, `execute_wt_timeseries_cli`
  - Line 69: `recommend.add_command(recommend_wt_timeseries_cli, "wt-timeseries")`
  - Line 70: `main.add_command(execute_wt_timeseries_cli, "wt-timeseries")`

  **Import Test**:
  - `python -c "from cleanmast.wt_timeseries import core"` ✓
  - `python -c "from cleanmast.cli import execute_wt_timeseries_cli"` ✓

  **Acceptance Criteria**:
  - [x] Decision executed (keep as facade)
  - [x] CLI registration confirmed
  - [x] Import tests pass
  - [x] Facade pattern documented

  **No commit needed** (verification only, no changes)

- [x] **8. MOVE: Relocate tests/fill_heights/ to DDD structure**

  **What to do**:
  - Move all files from `tests/fill_heights/` to `tests/subdomains/dataprocessing/services/height_filling/`
  - Preserve conftest.py and all fixtures
  - Update any relative imports if needed
  - Create destination directory structure if needed
  
  **Must NOT do**:
  - Do NOT delete tests (move only)
  - Do NOT lose conftest.py fixtures
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: File move operations
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 9, 10)
  - **Blocked By**: Task 3 (conftest inventory)
  
  **References**:
  - Source: `packages/cleanmast/tests/fill_heights/`
  - Destination: `packages/cleanmast/tests/subdomains/dataprocessing/services/height_filling/`
  
  **Acceptance Criteria**:
  - [ ] All files moved to destination
  - [ ] Source directory empty/deleted
  - [ ] `pytest packages/cleanmast/tests/subdomains/dataprocessing/services/height_filling/ -v` passes
  
  **QA Scenarios**:
  ```
  Scenario: Verify test move
    Tool: Bash
    Steps:
      1. ls packages/cleanmast/tests/subdomains/dataprocessing/services/height_filling/test_strategies.py
      2. pytest packages/cleanmast/tests/subdomains/dataprocessing/services/height_filling/ -v --collect-only | head -20
    Expected Result: Files exist, tests discovered
  ```
  
  **Commit**: YES (group with Task 9, 10)
  - Message: `test: move fill_heights tests to DDD structure`
  - Files: All files in `tests/fill_heights/`

- [x] **9. MOVE: Relocate tests/io/ to DDD structure**

  **What to do**:
  - Move all files from `tests/io/` to `tests/subdomains/dataingestion/infrastructure/`
  - Create destination directory if needed
  - Ensure tests import from subdomain (not old io path)
  
  **Must NOT do**:
  - Do NOT modify test logic (imports should already point to subdomains)
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: File move operations
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 8, 10)
  
  **References**:
  - Source: `packages/cleanmast/tests/io/`
  - Destination: `packages/cleanmast/tests/subdomains/dataingestion/infrastructure/`
  
  **Acceptance Criteria**:
  - [ ] All files moved
  - [ ] Tests pass at new location
  
  **QA Scenarios**:
  ```
  Scenario: Verify io test move
    Tool: Bash
    Steps:
      1. ls packages/cleanmast/tests/subdomains/dataingestion/infrastructure/test_timeseries_io.py
      2. pytest packages/cleanmast/tests/subdomains/dataingestion/infrastructure/ -v
    Expected Result: Files exist, tests pass
  ```
  
  **Commit**: YES (group with Task 8, 10)
  - Message: `test: move io tests to DDD structure`
  - Files: All files in `tests/io/`

- [x] **10. MOVE: Relocate tests/models/ to appropriate subdomains**

  **What to do**:
  - `test_sensor.py` → `tests/subdomains/dataingestion/value_objects/`
  - `test_reconstruct_meso.py` → `tests/subdomains/configuration/`
  - Create destination directories
  - Delete empty `tests/models/` after move
  
  **Must NOT do**:
  - Do NOT modify test files (they already import from subdomains)
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: File moves to different destinations
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 8, 9)
  
  **References**:
  - Source: `packages/cleanmast/tests/models/`
  - Destinations: See above
  
  **Acceptance Criteria**:
  - [ ] Files moved to correct destinations
  - [ ] `tests/models/` empty and deleted
  - [ ] Tests pass at new locations
  
  **QA Scenarios**:
  ```
  Scenario: Verify models test move
    Tool: Bash
    Steps:
      1. ls packages/cleanmast/tests/subdomains/dataingestion/value_objects/test_sensor.py
      2. ls packages/cleanmast/tests/subdomains/configuration/test_reconstruct_meso.py
      3. pytest packages/cleanmast/tests/subdomains/dataingestion/value_objects/test_sensor.py -v
    Expected Result: Files exist, tests pass
  ```
  
  **Commit**: YES (group with Task 8, 9)
  - Message: `test: move models tests to appropriate subdomains`
  - Files: `tests/models/test_sensor.py`, `tests/models/test_reconstruct_meso.py`

- [x] **11. CREATE: tests/subdomains/configuration/ directory structure**

  **What to do**:
  - Create `packages/cleanmast/tests/subdomains/configuration/`
  - Create `__init__.py`
  - Create subdirectories for each layer: `value_objects/`, `services/`
  - Document what tests should go here (from moved files)
  
  **Must NOT do**:
  - Do NOT create placeholder test files (just structure)
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Directory creation
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 12, 13, 14)
  
  **Acceptance Criteria**:
  - [ ] Directory exists
  - [ ] `__init__.py` created
  - [ ] Subdirectories created
  
  **QA Scenarios**:
  ```
  Scenario: Verify directory structure
    Tool: Bash
    Steps:
      1. ls packages/cleanmast/tests/subdomains/configuration/
      2. ls packages/cleanmast/tests/subdomains/configuration/__init__.py
    Expected Result: Directories and __init__.py exist
  ```
  
  **Commit**: YES (group with Task 12, 13, 14)
  - Message: `test: create configuration subdomain test structure`
  - Files: New directories

- [x] **12. CREATE: tests/subdomains/pipeline/ directory structure**

  **What to do**:
  - Create `packages/cleanmast/tests/subdomains/pipeline/`
  - Create `__init__.py`
  - Create subdirectories for layers
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 11, 13, 14)
  
  **Acceptance Criteria**:
  - [ ] Directory and `__init__.py` created
  
  **Commit**: YES (group with Task 11, 13, 14)
  - Message: `test: create pipeline subdomain test structure`

- [x] **13. CREATE: tests/application/ directory structure**

  **What to do**:
  - Create `packages/cleanmast/tests/application/`
  - Create `__init__.py`
  - Create `usecases/` subdirectory
  - Create `commands/` subdirectory
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 11, 12, 14)
  
  **Acceptance Criteria**:
  - [ ] Directory and subdirectories created
  
  **Commit**: YES (group with Task 11, 12, 14)
  - Message: `test: create application layer test structure`

- [x] **14. CREATE: tests/adapters/ directory structure**

  **What to do**:
  - Create `packages/cleanmast/tests/adapters/`
  - Create `__init__.py`
  - Create `cli/` subdirectory
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 11, 12, 13)
  
  **Acceptance Criteria**:
  - [ ] Directory and `__init__.py` created
  
  **Commit**: YES (group with Task 11, 12, 13)
  - Message: `test: create adapters layer test structure`

- [x] **15. VERIFY: Run full test suite**

  **What to do**:
  - Run `uv run pytest packages/cleanmast/tests/ -v`
  - Verify all 1039 tests pass
  - Document any failures
  
  **Must NOT do**:
  - Do NOT skip failing tests without documenting
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: Critical verification step
  
  **Parallelization**:
  - **Can Run In Parallel**: NO (must wait for all moves)
  - **Blocked By**: Task 4-14
  
  **Acceptance Criteria**:
  - [ ] All tests pass (or failures documented as pre-existing)
  - [ ] Test count matches before/after (1039 tests)
  
  **QA Scenarios**:
  ```
  Scenario: Full test suite
    Tool: Bash
    Steps:
      1. uv run pytest packages/cleanmast/tests/ -v --tb=short 2>&1 | tail -50
    Expected Result: All tests pass
  ```
  
  **Commit**: NO (verification only)

- [x] **16. VERIFY: Type check entire package**

  **What to do**:
  - Run `uv run ty check packages/cleanmast`
  - Verify no import errors
  - Document any type errors (may be pre-existing)
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 15)
  
  **Acceptance Criteria**:
  - [ ] Type check completes
  - [ ] No import-related errors
  
  **QA Scenarios**:
  ```
  Scenario: Type check
    Tool: Bash
    Steps:
      1. uv run ty check packages/cleanmast 2>&1 | head -50
    Expected Result: No "Cannot resolve imported module" errors
  ```
  
  **Commit**: NO (verification only)

- [x] **17. VERIFY: Import smoke test**

  **What to do**:
  - Run `python -c "import cleanmast; print('OK')"`
  - Verify clean import with no errors
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  
  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 15, 16)
  
  **Acceptance Criteria**:
  - [ ] Import succeeds
  - [ ] Prints "OK"
  
  **QA Scenarios**:
  ```
  Scenario: Smoke test
    Tool: Bash
    Steps:
      1. python -c "import cleanmast; print('OK')"
    Expected Result: Prints OK
  ```
  
  **Commit**: NO (verification only)

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE.

- [ ] **F1. Plan Compliance Audit** — `oracle`
  
  Read the plan end-to-end. For each "Must Have": verify implementation exists. For each "Must NOT Have": search codebase for forbidden patterns. Check:
  - All orphaned directories deleted
  - All tests moved to DDD structure
  - Import fix applied
  - New test directories created
  
  Output: `Must Have [8/8] | Must NOT Have [4/4] | VERDICT: APPROVE/REJECT`

- [ ] **F2. Code Quality Review** — `unspecified-high`
  
  Run `ty check` + `pytest`. Review for:
  - Import errors
  - Test failures related to moves
  - Missing `__init__.py` files
  
  Output: `Build [PASS/FAIL] | Tests [N pass/N fail] | VERDICT`

- [ ] **F3. Real Manual QA** — `unspecified-high`
  
  Execute verification scenarios from Task 15-17. Verify:
  - Full test suite passes
  - Type check clean
  - Import smoke test succeeds
  
  Save evidence to `.sisyphus/evidence/final-qa/`.
  
  Output: `Scenarios [3/3 pass] | VERDICT`

- [ ] **F4. Scope Fidelity Check** — `deep`
  
  Compare plan vs actual changes:
  - Verify orphaned code deleted (not just moved)
  - Verify tests preserved (not deleted)
  - Verify no logic changes (pure reorganization)
  
  Output: `Scope [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

**Wave 2 (Import Fix)**:
- Commit 1: `fix(commands): update import from cleanmast.io to subdomain`

**Wave 3 (Source Cleanup)**:
- Commit 2: `refactor: remove orphaned fill_heights and io directories`
- Commit 3: `refactor: remove/move wt_timeseries directory`

**Wave 4 (Test Moves)**:
- Commit 4: `test: reorganize tests to match DDD structure`

**Wave 5 (Structure Creation)**:
- Commit 5: `test: add missing test directory structure`

---

## Success Criteria

### Verification Commands
```bash
# Test count preserved
uv run pytest packages/cleanmast/tests/ --collect-only -q | tail -1
# Expected: 1039 tests collected

# No import errors
uv run ty check packages/cleanmast 2>&1 | grep -c "Cannot resolve" || echo "0"
# Expected: 0

# Smoke test
python -c "import cleanmast; print('OK')"
# Expected: OK

# Directory structure verified
ls packages/cleanmast/tests/subdomains/configuration/
ls packages/cleanmast/tests/subdomains/pipeline/
ls packages/cleanmast/tests/application/
ls packages/cleanmast/tests/adapters/
# All should exist
```

### Final Checklist
- [ ] All "Must Have" present (8/8)
- [ ] All "Must NOT Have" absent (4/4)
- [ ] All orphaned source directories deleted
- [ ] All tests moved to DDD structure
- [ ] New test directories created
- [ ] Import fix applied
- [ ] Full test suite passes
- [ ] Type check clean
