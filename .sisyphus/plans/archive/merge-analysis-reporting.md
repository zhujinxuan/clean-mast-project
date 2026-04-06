# Work Plan: Merge Analysis and Reporting Subdomains into Assessment

## TL;DR

> **Merge** the tightly-coupled `analysis` and `reporting` subdomains into a unified `assessment` subdomain. 
> 
> **Why**: Analysis has only one consumer (reporting), changes to `AnalysisResult[T]` break 12+ files, and they form a single business capability (wind resource assessment).
>
> **Deliverables**: New `assessment/` subdomain with reorganized entities, value objects, domain services, and application layer. Clean deletion of old `analysis/` and `reporting/` directories.
>
> **Estimated Effort**: Medium (1-2 days)
> **Parallel Execution**: YES - 4 waves with 5-8 tasks each
> **Critical Path**: Wave 1 scaffolding → Wave 2 domain migration → Wave 3 service migration → Wave 4 integration & tests

---

## Context

### Original Request
User wants to merge `analysis` and `reporting` subdomains due to:
1. Tight coupling - `AnalysisResult[T]` changes cascade to 12+ reporting files
2. One-way dependency - only reporting consumes analysis output
3. Conceptual unity - they form a complete wind resource assessment workflow

### Interview Summary
**Confirmed Decisions**:
- Scope: Python only (`packages/cleanmast/src/cleanmast/subdomains/`)
- New name: `assessment`
- Backward compatibility: NO (clean cutover)
- Testing: Comprehensive (all tests must pass)

### Research Findings
**Analysis Subdomain** (`subdomains/analysis/`):
- Services: 10 calculators (wind_rose, weibull, turbulence, frequency, temporal, vertical_profile, monthly_stats, monthly_power, air_density)
- Value Objects: `AnalysisResult[T]`, schemas, inputs, metadata

**Reporting Subdomain** (`subdomains/reporting/`):
- Entities: 25+ `ReportAtom` types, `ReportSection`
- Services: Converters (6), `ReportBuilder`, `Renderer`, `Compiler`
- Protocols: `Section` interface

**Coupling Evidence**:
- `reporting/services/wind_rose_converter.py` imports `AnalysisResult`
- `reporting/entities/single_mast/*.py` imports schemas from analysis
- Application layer (`generate_report.py`) imports both

### Oracle Review
**Recommendation**: MERGE into `assessment` subdomain
**Rationale**: They represent sequential phases of the same bounded context (wind resource assessment), not independent contexts.

---

## Work Objectives

### Core Objective
Create a unified `assessment` subdomain that combines calculation (analysis) and presentation (reporting) into a cohesive wind resource assessment capability.

### Concrete Deliverables
1. **New directory structure**: `subdomains/assessment/` with clean DDD layers
2. **Domain layer**: Entities (`AssessmentReport`, `ReportAtom`), Value Objects (`AnalysisResult`, schemas), Domain Services (calculators + builders)
3. **Service layer**: `ReportGenerationService` coordinating pipelines + builders (thin orchestration)
4. **Application layer**: `AssessmentWorkflow` thin orchestrator calling service methods
5. **Infrastructure layer**: Renderers, compilers, templates
6. **Test migration**: All existing tests updated to new imports
7. **Cleanup**: Remove old `analysis/` and `reporting/` directories

### Definition of Done
- [ ] `uv run pytest packages/cleanmast/tests/assessment/` - ALL pass
- [ ] `uv run pytest packages/cleanmast/tests/report/` - ALL pass (migrated)
- [ ] `uv run pytest packages/cleanmast/tests/analysis/` - ALL pass (migrated)
- [ ] `uv run ty check packages/cleanmast` - no type errors
- [ ] Old directories deleted, no broken imports in codebase

### Must Have
- [ ] All calculators migrated (`WindRoseCalculator`, `WeibullFitter`, etc.)
- [ ] All converters migrated (transformed into builders)
- [ ] All entities migrated (`ReportAtom`, `ReportSection`)
- [ ] All value objects migrated (`AnalysisResult`, schemas)
- [ ] **Service Layer created** coordinating pipelines + builders
- [ ] Application use case updated (`generate_report.py`) - thin orchestrator
- [ ] All 100+ test files updated with new imports

### Must NOT Have (Guardrails)
- [ ] NO backward compatibility shims (clean cutover)
- [ ] NO Julia code changes (Python only)
- [ ] NO changes to `subdomains/dataingestion/` or other subdomains except imports
- [ ] NO logic changes - this is pure reorganization
- [ ] NO breaking of calculator purity (calculators remain stateless)

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest configured)
- **Automated tests**: Comprehensive (all existing tests must pass)
- **Framework**: pytest
- **If TDD**: N/A (migration, not new feature)

### QA Policy
Every task includes agent-executed QA scenarios:
- **Type checking**: `uv run ty check packages/cleanmast`
- **Unit tests**: `uv run pytest packages/cleanmast/tests/path/to/test.py -v`
- **Import verification**: Python can import all modules without errors
- **Evidence**: Screenshots of test results saved to `.sisyphus/evidence/`

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately - Foundation):
├── Task 1: Create assessment/ directory structure [quick]
├── Task 2: Migrate analysis value objects [quick]
├── Task 3: Migrate reporting value objects [quick]
└── Task 4: Create assessment __init__.py exports [quick]

Wave 2 (After Wave 1 - Domain Layer):
├── Task 5: Migrate calculator services [quick]
├── Task 6: Migrate and rename converters → builders [quick]
├── Task 7: Migrate ReportAtom entities [quick]
└── Task 8: Migrate ReportSection and related entities [quick]

Wave 3 (After Wave 2 - Application & Infrastructure):
├── Task 9: Migrate application use case [quick]
├── Task 10: Migrate infrastructure (renderers, compilers) [quick]
├── Task 11: Update imports in dataingestion [quick]
└── Task 12: Update imports in other subdomains [quick]

Wave 4 (After Wave 3 - Tests & Cleanup):
├── Task 14: Migrate analysis tests [unspecified-high]
├── Task 15: Migrate reporting tests [unspecified-high]
├── Task 16: Delete old analysis/ directory [git]
└── Task 17: Delete old reporting/ directory [git]

Wave FINAL (After ALL tasks - Verification):
├── Task F1: Run comprehensive test suite [unspecified-high]
├── Task F2: Type check entire package [unspecified-high]
└── Task F3: Import verification (all modules) [quick]

Critical Path: Task 1 → Task 2+3 → Task 5+6+7+8 → Task 9+10+11+12+13 → Task 14+15 → Task 16+17 → F1+F2+F3
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 4 (Wave 2 & 3)
```

### Dependency Matrix

| Task | Dependencies | Blocks |
|------|--------------|--------|
| 1 | None | 2, 3, 4 |
| 2 | 1 | 5, 6 |
| 3 | 1 | 6, 7 |
| 4 | 1, 2, 3 | 5, 6, 7, 8 |
| 5 | 2, 4 | 9, 12 |
| 6 | 2, 3, 4 | 9, 10, 11 |
| 7 | 3, 4 | 9, 10, 11 |
| 8 | 3, 4 | 9, 10, 11 |
| 9 | 5, 6, 7, 8 | 10, 14 |
| 10 | 9 | 14, 15 |
| 11 | 6, 7, 8 | 15, 16 |
| 12 | 5 | 16, 17 |
| 13 | 5, 6 | 16, 17 |
| 14 | 9, 10 | F1, F2, F3 |
| 15 | 9, 10 | F1, F2, F3 |
| 16 | 11, 12, 13 | F1, F2, F3 |
| 17 | 11, 12, 14 | F1, F2, F3 |
| F1-F3 | 14, 15, 16, 17 | None |

### Agent Dispatch Summary

- **Wave 1**: 4 tasks → `quick` agents
- **Wave 2**: 4 tasks → `quick` agents
- **Wave 3**: 4 tasks → `quick` agents
- **Wave 4**: 4 tasks → `unspecified-high` (tests) + `git` (deletion)
- **FINAL**: 3 tasks → `unspecified-high` (verification)

---

## TODOs

- [x] 1. Create assessment/ directory structure

  **What to do**:
  - Create directory: `packages/cleanmast/src/cleanmast/subdomains/assessment/`
  - Create subdirectories: `domain/`, `application/`, `infrastructure/`
  - Under `domain/`: `entities/`, `value_objects/`, `services/`
  - Under `domain/services/`: `calculators/`, `builders/`, `compilers/`
  - Under `domain/entities/`: `single_mast/`
  - Create empty `__init__.py` files in all directories

  **Must NOT do**:
  - NO file content yet (just structure)
  - NO migration of actual code

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Simple directory creation, low complexity

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 2, 3, 4
  - **Blocked By**: None

  **References**:
  - Target structure: See "Proposed Directory Structure" in Context section

  **Acceptance Criteria**:
  - [ ] All directories exist with `__init__.py` files
  - [ ] `python -c "import cleanmast.subdomains.assessment"` succeeds (empty module)

  **QA Scenarios**:
  ```
  Scenario: Directory structure created
    Tool: Bash
    Steps:
      1. ls packages/cleanmast/src/cleanmast/subdomains/assessment/
      2. ls packages/cleanmast/src/cleanmast/subdomains/assessment/domain/
      3. ls packages/cleanmast/src/cleanmast/subdomains/assessment/domain/services/calculators/
    Expected Result: All directories exist, __init__.py files present
    Evidence: .sisyphus/evidence/task-1-structure.png
  ```

  **Commit**: YES
  - Message: `chore(assessment): create subdomain directory structure`
  - Files: All new directories and __init__.py files

- [x] 2. Migrate analysis value objects

  **What to do**:
  - Copy from: `subdomains/analysis/value_objects/`
  - Copy to: `subdomains/assessment/domain/value_objects/`
  - Files to migrate:
    - `analysis_result.py` → keep name
    - `analysis_input.py` → keep name
    - `analysis_metadata.py` → keep name
    - `analysis_parameters.py` → keep name
    - `schemas.py` → keep name
    - `air_density.py` → keep name
    - `column_utils.py` → keep name
    - `hash_utils.py` → keep name
    - `analysis_node.py` → keep name
  - Update internal imports to use new paths
  - Update ADR-GUARDRAILS comments to reference assessment

  **Must NOT do**:
  - NO logic changes
  - NO renaming of classes/functions
  - NO changes to schemas

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: File copy with import updates

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 3)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 5, 6
  - **Blocked By**: Task 1

  **References**:
  - Source: `subdomains/analysis/value_objects/`
  - Target: `subdomains/assessment/domain/value_objects/`

  **Acceptance Criteria**:
  - [ ] All 9 files copied to new location
  - [ ] Internal imports updated (e.g., `from .analysis_metadata` works)
  - [ ] `python -c "from cleanmast.subdomains.assessment.domain.value_objects import AnalysisResult"` succeeds

  **QA Scenarios**:
  ```
  Scenario: Value objects importable
    Tool: Bash (Python)
    Steps:
      1. python -c "from cleanmast.subdomains.assessment.domain.value_objects import AnalysisResult, WindRoseSchema"
      2. python -c "from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import SingleMastAnalysisInput"
    Expected Result: No ImportError
    Evidence: .sisyphus/evidence/task-2-imports.txt
  ```

  **Commit**: YES (group with Tasks 2-4)
  - Message: `refactor(assessment): migrate analysis value objects`

- [x] 3. Migrate reporting value objects

  **What to do**:
  - Copy from: `subdomains/reporting/value_objects/`
  - Copy to: `subdomains/assessment/domain/value_objects/`
  - Files to migrate:
    - `collections/` → `collections/`
    - `report_config.py` → keep name
    - `rep_ts_report_config.py` → keep name
    - `meta.py` → `report_meta.py` (avoid conflict)
    - `single_mast/` → `single_mast/`
  - Update internal imports
  - Resolve any naming conflicts with analysis VO

  **Must NOT do**:
  - NO logic changes
  - NO breaking changes to report config schemas

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: File copy with minor naming adjustments

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 2)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 6, 7
  - **Blocked By**: Task 1

  **References**:
  - Source: `subdomains/reporting/value_objects/`
  - Target: `subdomains/assessment/domain/value_objects/`

  **Acceptance Criteria**:
  - [ ] All value objects copied
  - [ ] Naming conflicts resolved (e.g., `meta.py` → `report_meta.py`)
  - [ ] Imports work correctly

  **QA Scenarios**:
  ```
  Scenario: Reporting VOs importable
    Tool: Bash (Python)
    Steps:
      1. python -c "from cleanmast.subdomains.assessment.domain.value_objects import SingleMastMeta"
      2. python -c "from cleanmast.subdomains.assessment.domain.value_objects.collections import AtomCollection"
    Expected Result: No ImportError
    Evidence: .sisyphus/evidence/task-3-imports.txt
  ```

  **Commit**: YES (group with Tasks 2-4)
  - Message: `refactor(assessment): migrate reporting value objects`

- [x] 4. Create assessment __init__.py exports

  **What to do**:
  - Create `assessment/__init__.py` with public API exports
  - Create `assessment/domain/__init__.py`
  - Create `assessment/domain/value_objects/__init__.py` with exports
  - Create `assessment/domain/entities/__init__.py` with exports
  - Create `assessment/domain/services/__init__.py` with exports
  - Define clear public API surface

  **Must NOT do**:
  - NO circular imports
  - NO exporting internal/private modules

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Module organization, export management

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 2, 3)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 5, 6, 7, 8
  - **Blocked By**: Task 1

  **References**:
  - Pattern: `subdomains/reporting/__init__.py`
  - Pattern: `subdomains/analysis/__init__.py`

  **Acceptance Criteria**:
  - [ ] All `__init__.py` files created with exports
  - [ ] `from cleanmast.subdomains.assessment import X` works for all public types
  - [ ] No circular import errors

  **QA Scenarios**:
  ```
  Scenario: Public API accessible
    Tool: Bash (Python)
    Steps:
      1. python -c "from cleanmast.subdomains.assessment import AnalysisResult, ReportAtom"
      2. python -c "from cleanmast.subdomains.assessment.domain.services.calculators import WindRoseCalculator"
    Expected Result: All imports succeed
    Evidence: .sisyphus/evidence/task-4-api.txt
  ```

  **Commit**: YES (group with Tasks 2-4)
  - Message: `refactor(assessment): setup public API exports`

- [x] 5. Migrate calculator services

  **What to do**:
  - Copy from: `subdomains/analysis/services/`
  - Copy to: `subdomains/assessment/domain/services/calculators/`
  - Files to migrate (10 calculators):
    - `wind_rose_calculator.py`
    - `weibull_fitter.py`
    - `turbulence_calculator.py`
    - `wind_frequency_calculator.py`
    - `wind_temporal_analyzer.py`
    - `vertical_profile_analyzer.py`
    - `monthly_stats_calculator.py`
    - `monthly_power_calculator.py`
    - `air_density_calculator.py`
    - `__init__.py`
  - Update imports to use new value object paths
  - Keep ADR-GUARDRAILS comments updated

  **Must NOT do**:
  - NO logic changes to calculators
  - NO renaming calculator classes

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: File copy with import path updates

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 6-8)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 9, 11
  - **Blocked By**: Tasks 2, 4

  **References**:
  - Source: `subdomains/analysis/services/`
  - Import pattern: `from ...value_objects.analysis_result import AnalysisResult`

  **Acceptance Criteria**:
  - [ ] All 10 calculator files migrated
  - [ ] All imports updated to new paths
  - [ ] Calculators remain stateless (no side effects)
  - [ ] Type annotations preserved

  **QA Scenarios**:
  ```
  Scenario: Calculators work correctly
    Tool: Bash (pytest)
    Steps:
      1. uv run pytest packages/cleanmast/tests/analysis/test_wind_rose_calculator.py -v
      2. uv run pytest packages/cleanmast/tests/analysis/test_weibull_fitter.py -v
    Expected Result: Tests pass with new import paths
    Evidence: .sisyphus/evidence/task-5-calculators.txt
  ```

  **Commit**: YES (group with Tasks 5-8)
  - Message: `refactor(assessment): migrate calculator services`

- [x] 6. Migrate and rename converters → builders

  **What to do**:
  - Copy from: `subdomains/reporting/services/*_converter.py`
  - Copy to: `subdomains/assessment/domain/services/builders/`
  - Rename files:
    - `wind_rose_converter.py` → `wind_rose_builder.py`
    - `weibull_converter.py` → `weibull_builder.py`
    - `turbulence_converter.py` → `turbulence_builder.py`
    - `wind_frequency_converter.py` → `wind_frequency_builder.py`
    - `wind_temporal_converter.py` → `wind_temporal_builder.py`
    - `vertical_profile_converter.py` → `vertical_profile_builder.py`
  - Rename classes:
    - `WindRoseAnalysisToAtoms` → `WindRoseSectionBuilder`
    - Similar pattern for others
  - Update imports to use assessment paths
  - Update ADR-GUARDRAILS comments

  **Must NOT do**:
  - NO logic changes (renaming only)
  - NO changes to conversion algorithms

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: File copy + systematic renaming

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 5, 7, 8)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 9, 10
  - **Blocked By**: Tasks 2, 3, 4

  **References**:
  - Source: `subdomains/reporting/services/*_converter.py`
  - Naming pattern: `XConverter` → `XBuilder`

  **Acceptance Criteria**:
  - [ ] All 6 converter files migrated and renamed
  - [ ] Class names updated consistently
  - [ ] All imports updated

  **QA Scenarios**:
  ```
  Scenario: Builders importable and functional
    Tool: Bash (Python)
    Steps:
      1. python -c "from cleanmast.subdomains.assessment.domain.services.builders import WindRoseSectionBuilder"
      2. python -c "from cleanmast.subdomains.assessment.domain.services.builders import WeibullSectionBuilder"
    Expected Result: No ImportError, classes instantiable
    Evidence: .sisyphus/evidence/task-6-builders.txt
  ```

  **Commit**: YES (group with Tasks 5-8)
  - Message: `refactor(assessment): migrate converters as builders`

- [x] 7. Migrate ReportAtom entities

  **What to do**:
  - Copy from: `subdomains/reporting/entities/`
  - Copy to: `subdomains/assessment/domain/entities/`
  - Files to migrate:
    - `report_atom.py` (base class)
    - `single_mast/wind_rose.py`
    - `single_mast/timeseries.py`
    - `single_mast/monthly_pattern.py`
    - `single_mast/daily_pattern.py`
    - `single_mast/weibull_distribution.py`
    - `single_mast/turbulence_intensity.py`
    - `single_mast/wind_frequency_table.py`
    - `single_mast/vertical_profile.py`
    - `single_mast/wind_shear_table.py`
    - And 15+ more atom files
  - Update imports to use assessment VO paths

  **Must NOT do**:
  - NO changes to ReportAtom base class
  - NO changes to atom schemas

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: File copy with import updates

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 5, 6, 8)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 9, 10
  - **Blocked By**: Tasks 3, 4

  **References**:
  - Source: `subdomains/reporting/entities/`
  - Count: ~25 entity files

  **Acceptance Criteria**:
  - [ ] All entity files migrated
  - [ ] Imports updated to use assessment paths
  - [ ] `ReportAtom` base class imports work

  **QA Scenarios**:
  ```
  Scenario: ReportAtoms importable
    Tool: Bash (Python)
    Steps:
      1. python -c "from cleanmast.subdomains.assessment.domain.entities import ReportAtom"
      2. python -c "from cleanmast.subdomains.assessment.domain.entities.single_mast import SingleMastWindRoseAtom"
    Expected Result: No ImportError
    Evidence: .sisyphus/evidence/task-7-atoms.txt
  ```

  **Commit**: YES (group with Tasks 5-8)
  - Message: `refactor(assessment): migrate ReportAtom entities`

- [x] 8. Migrate ReportSection and related entities

  **What to do**:
  - Copy from: `subdomains/reporting/services/sections/`
  - Copy to: `subdomains/assessment/domain/services/sections/`
  - Files:
    - `wind_rose.py` → section implementation
    - `turbulence_subsection.py`
    - `weibull_subsection.py`
    - `wind_frequency_subsection.py`
    - `wind_temporal_subsection.py`
    - `vertical_profile_subsection.py`
    - `representative_wind_speed.py`
    - `representative_wind_power.py`
  - Also migrate protocols: `subdomains/reporting/protocols/section.py` → `assessment/domain/protocols/`
  - Update imports

  **Must NOT do**:
  - NO changes to Section protocol
  - NO changes to section logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: File copy with import updates

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 5-7)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 9, 10
  - **Blocked By**: Tasks 3, 4

  **References**:
  - Source: `subdomains/reporting/services/sections/`
  - Source: `subdomains/reporting/protocols/`

  **Acceptance Criteria**:
  - [ ] All section files migrated
  - [ ] Protocols migrated
  - [ ] Section imports work

  **QA Scenarios**:
  ```
  Scenario: Sections importable
    Tool: Bash (Python)
    Steps:
      1. python -c "from cleanmast.subdomains.assessment.domain.protocols import Section"
      2. python -c "from cleanmast.subdomains.assessment.domain.services.sections import WindRoseSection"
    Expected Result: No ImportError
    Evidence: .sisyphus/evidence/task-8-sections.txt
  ```

  **Commit**: YES (group with Tasks 5-8)
  - Message: `refactor(assessment): migrate section entities and protocols`

- [x] 9. Create Service Layer (pipelines + builders coordination)

  **What to do**:
  - Create: `subdomains/assessment/application/services/report_generation_service.py`
  - Create: `subdomains/assessment/application/services/__init__.py`
  - Implement `ReportGenerationService` class that:
    - Encapsulates pipeline transformation + builder assembly
    - Provides high-level methods like `generate_wind_rose_section()`, `generate_monthly_stats_section()`
    - Keeps orchestrator thin (just calls service methods)
  - Service internally coordinates:
    - Pipeline: raw data → processed DataFrame
    - Builder: AnalysisResult + meta → ReportAtom
    - Returns: Ready-to-use Section

  **Must NOT do**:
  - NO business logic (keep in domain calculators)
  - NO report structure knowledge (keep in builders)
  - Service ONLY coordinates, doesn't transform

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: New component design, needs careful API design

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 10, 11, 12)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 13 (old task 9 - application use case)
  - **Blocked By**: Tasks 5, 6, 7, 8

  **References**:
  - Pattern: See discussion in plan - Service coordinates pipelines + builders
  - Current logic: `application/usecases/generate_report.py` lines 55-217

  **Acceptance Criteria**:
  - [ ] Service class created with methods for each report section type
  - [ ] Service imports work: `from cleanmast.subdomains.assessment.application.services import ReportGenerationService`
  - [ ] Service has thin API: `service.generate_wind_rose_section(df, sensors, meta) -> WindRoseSection`

  **QA Scenarios**:
  ```
  Scenario: Service Layer works
    Tool: Bash (Python)
    Steps:
      1. python -c "from cleanmast.subdomains.assessment.application.services import ReportGenerationService"
      2. python -c "service = ReportGenerationService(); print(dir(service))"
    Expected Result: Service imports, has generate_* methods
    Evidence: .sisyphus/evidence/task-9-service.txt
  ```

  **Commit**: YES (group with Tasks 9-12)
  - Message: `feat(assessment): create service layer coordinating pipelines and builders`

- [x] 10. Refactor application use case to use Service Layer

  **What to do**:
  - Update: `application/usecases/generate_report.py`
  - Replace inline pipeline + builder logic with Service calls:
    ```python
    # OLD: Inline processing
    monthly_wind_df = process_monthly_wind_data(df, sensors)
    monthly_wind_atom = SingleMastMonthlyWindAtom.create(...)
    
    # NEW: Service call
    section = service.generate_monthly_wind_section(df, sensors, meta)
    ```
  - Make orchestrator thin - just coordinates service calls and assembles final report

  **Must NOT do**:
  - NO inline data processing logic (move to service)
  - NO direct builder calls (go through service)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: Refactoring logic to service

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 9)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 14, 15
  - **Blocked By**: Task 9

  **References**:
  - File: `application/usecases/generate_report.py`
  - Service: `assessment/application/services/report_generation_service.py`

  **Acceptance Criteria**:
  - [ ] Use case imports and uses ReportGenerationService
  - [ ] Inline `process_*` functions removed from use case
  - [ ] Orchestrator is thin (<50 lines of coordination code)
  - [ ] `uv run ty check` passes

  **QA Scenarios**:
  ```
  Scenario: Thin orchestrator
    Tool: Bash (wc + ty)
    Steps:
      1. wc -l packages/cleanmast/src/cleanmast/application/usecases/generate_report.py
      2. uv run ty check packages/cleanmast/src/cleanmast/application/usecases/generate_report.py
    Expected Result: File significantly smaller, no type errors
    Evidence: .sisyphus/evidence/task-10-refactor.txt
  ```

  **Commit**: YES (group with Tasks 9-12)
  - Message: `refactor(assessment): thin orchestrator using service layer`

- [x] 11. Migrate infrastructure (renderers, compilers)

  **What to do**:
  - Copy from: `subdomains/reporting/services/renderer.py`, `compiler.py`, `report_builder.py`
  - Copy to: `subdomains/assessment/infrastructure/`
  - Files:
    - `renderer.py` → TypstRenderer
    - `compiler.py` → TypstCompiler
    - `report_builder.py` → AssessmentReportBuilder
  - Update imports to use assessment domain paths

  **Must NOT do**:
  - NO changes to rendering logic
  - NO changes to compilation logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: File copy with import updates

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 9, 10, 12)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 15, 16
  - **Blocked By**: Tasks 6, 7, 8

  **References**:
  - Source: `subdomains/reporting/services/renderer.py`
  - Source: `subdomains/reporting/services/compiler.py`
    - Source: `subdomains/reporting/services/report_builder.py`

  **Acceptance Criteria**:
  - [ ] Infrastructure files migrated
  - [ ] Imports updated
  - [ ] TypstRenderer still functional

  **QA Scenarios**:
  ```
  Scenario: Infrastructure imports work
    Tool: Bash (Python)
    Steps:
      1. python -c "from cleanmast.subdomains.assessment.infrastructure import TypstRenderer, TypstCompiler"
    Expected Result: No ImportError
    Evidence: .sisyphus/evidence/task-11-infra.txt
  ```

  **Commit**: YES (group with Tasks 9-12)
  - Message: `refactor(assessment): migrate infrastructure layer`

- [x] 12. Update imports in dataingestion

  **What to do**:
  - Search for: `from cleanmast.subdomains.analysis` in `dataingestion/`
  - Search for: `from cleanmast.subdomains.reporting` in `dataingestion/`
  - Update to: `from cleanmast.subdomains.assessment`
  - Files likely affected: Any that import `AnalysisResult` or schemas

  **Must NOT do**:
  - NO logic changes

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Import path updates across files

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 9, 10, 11)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 16, 17
  - **Blocked By**: Task 5

  **References**:
  - Search: `grep -r "from cleanmast.subdomains.analysis" packages/cleanmast/src/cleanmast/subdomains/dataingestion/`

  **Acceptance Criteria**:
  - [ ] All dataingestion imports updated
  - [ ] `uv run ty check packages/cleanmast/src/cleanmast/subdomains/dataingestion/` passes

  **QA Scenarios**:
  ```
  Scenario: Dataingestion imports updated
    Tool: Bash (ty)
    Steps:
      1. uv run ty check packages/cleanmast/src/cleanmast/subdomains/dataingestion/
    Expected Result: No type errors
    Evidence: .sisyphus/evidence/task-12-dataingestion.txt
  ```

  **Commit**: YES (group with Tasks 9-12)
  - Message: `refactor(assessment): update dataingestion imports`

- [x] 13. Update imports in other subdomains

  **What to do**:
  - Check all other subdomains for analysis/reporting imports
  - Update any remaining imports to use assessment
  - Likely subdomains: `configuration/`, `integration/`

  **Must NOT do**:
  - NO logic changes

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Import path updates

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 9-11)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 15, 16
  - **Blocked By**: Tasks 5, 6

  **References**:
  - Search: `grep -r "from cleanmast.subdomains.analysis\|from cleanmast.subdomains.reporting" packages/cleanmast/src/cleanmast/subdomains/ --include="*.py"`

  **Acceptance Criteria**:
  - [ ] All remaining imports updated
  - [ ] No references to old subdomains except in tests

  **QA Scenarios**:
  ```
  Scenario: All imports updated
    Tool: Bash (grep)
    Steps:
      1. grep -r "from cleanmast.subdomains.analysis" packages/cleanmast/src/ --include="*.py" | grep -v test | grep -v __pycache__
      2. grep -r "from cleanmast.subdomains.reporting" packages/cleanmast/src/ --include="*.py" | grep -v test | grep -v __pycache__
    Expected Result: No matches (except in old directories)
    Evidence: .sisyphus/evidence/task-12-remaining.txt
  ```

  **Commit**: YES (group with Tasks 9-12)
  - Message: `refactor(assessment): update remaining subdomain imports`

- [x] 14. Migrate analysis tests

  **What to do**:
  - Move from: `packages/cleanmast/tests/analysis/`
  - Move to: `packages/cleanmast/tests/assessment/`
  - Update all imports in test files
  - Update test configuration if needed (conftest.py)
  - Ensure test data paths still work

  **Must NOT do**:
  - NO changes to test logic
  - NO changes to test assertions

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: Test migration requires care to preserve behavior

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 14)
  - **Parallel Group**: Wave 4
  - **Blocks**: Tasks F1, F2, F3
  - **Blocked By**: Tasks 9, 10

  **References**:
  - Source: `packages/cleanmast/tests/analysis/`
  - Count: ~20 test files

  **Acceptance Criteria**:
  - [ ] All analysis tests moved
  - [ ] All imports updated
  - [ ] `uv run pytest packages/cleanmast/tests/assessment/ -v` passes

  **QA Scenarios**:
  ```
  Scenario: Analysis tests pass
    Tool: Bash (pytest)
    Steps:
      1. uv run pytest packages/cleanmast/tests/assessment/ -v --tb=short 2>&1 | head -100
    Expected Result: All tests pass (0 failures)
    Evidence: .sisyphus/evidence/task-13-tests.txt
  ```

  **Commit**: YES (group with Tasks 13-14)
  - Message: `refactor(assessment): migrate analysis tests`

- [x] 15. Migrate reporting tests

  **What to do**:
  - Move from: `packages/cleanmast/tests/report/`
  - Move to: `packages/cleanmast/tests/assessment/`
  - Update all imports in test files
  - Resolve any test file naming conflicts
  - Update conftest.py

  **Must NOT do**:
  - NO changes to test logic
  - NO changes to test assertions

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: Test migration requires care

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 13)
  - **Parallel Group**: Wave 4
  - **Blocks**: Tasks F1, F2, F3
  - **Blocked By**: Tasks 9, 10

  **References**:
  - Source: `packages/cleanmast/tests/report/`
  - Count: ~20 test files

  **Acceptance Criteria**:
  - [ ] All reporting tests moved
  - [ ] All imports updated (converters → builders)
  - [ ] `uv run pytest packages/cleanmast/tests/assessment/ -v` passes

  **QA Scenarios**:
  ```
  Scenario: Reporting tests pass
    Tool: Bash (pytest)
    Steps:
      1. uv run pytest packages/cleanmast/tests/assessment/test_report* -v --tb=short 2>&1 | head -100
    Expected Result: All tests pass (0 failures)
    Evidence: .sisyphus/evidence/task-14-tests.txt
  ```

  **Commit**: YES (group with Tasks 13-14)
  - Message: `refactor(assessment): migrate reporting tests`

- [x] 16. Delete old analysis/ directory

  **What to do**:
  - Delete: `packages/cleanmast/src/cleanmast/subdomains/analysis/`
  - Verify no imports remain in non-test code
  - Ensure git tracks the deletion

  **Must NOT do**:
  - DO NOT delete if any imports still exist (check first!)

  **Recommended Agent Profile**:
  - **Category**: `git`
  - **Reason**: Git operations, deletion
  - **Load Skills**: `git-master`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 16)
  - **Parallel Group**: Wave 4
  - **Blocks**: Tasks F1, F2, F3
  - **Blocked By**: Tasks 11, 12, 13

  **References**:
  - Directory: `packages/cleanmast/src/cleanmast/subdomains/analysis/`

  **Acceptance Criteria**:
  - [ ] Directory deleted
  - [ ] Git shows deletion in status
  - [ ] No broken imports in codebase

  **QA Scenarios**:
  ```
  Scenario: Analysis directory removed
    Tool: Bash
    Steps:
      1. ls packages/cleanmast/src/cleanmast/subdomains/analysis/ 2>&1
      2. git status | grep analysis
    Expected Result: "No such file or directory", deletion shown in git
    Evidence: .sisyphus/evidence/task-15-deletion.txt
  ```

  **Commit**: YES (group with Tasks 15-16)
  - Message: `refactor(assessment): remove old analysis subdomain`

- [x] 17. Delete old reporting/ directory

  **What to do**:
  - Delete: `packages/cleanmast/src/cleanmast/subdomains/reporting/`
  - Verify no imports remain in non-test code
  - Ensure git tracks the deletion

  **Must NOT do**:
  - DO NOT delete if any imports still exist (check first!)

  **Recommended Agent Profile**:
  - **Category**: `git`
  - **Reason**: Git operations, deletion
  - **Load Skills**: `git-master`

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 15)
  - **Parallel Group**: Wave 4
  - **Blocks**: Tasks F1, F2, F3
  - **Blocked By**: Tasks 11, 12, 14

  **References**:
  - Directory: `packages/cleanmast/src/cleanmast/subdomains/reporting/`

  **Acceptance Criteria**:
  - [ ] Directory deleted
  - [ ] Git shows deletion in status
  - [ ] No broken imports in codebase

  **QA Scenarios**:
  ```
  Scenario: Reporting directory removed
    Tool: Bash
    Steps:
      1. ls packages/cleanmast/src/cleanmast/subdomains/reporting/ 2>&1
      2. git status | grep reporting
    Expected Result: "No such file or directory", deletion shown in git
    Evidence: .sisyphus/evidence/task-16-deletion.txt
  ```

  **Commit**: YES (group with Tasks 15-16)
  - Message: `refactor(assessment): remove old reporting subdomain`

---

## Final Verification Wave

- [x] F1. Run comprehensive test suite

  **What to do**:
  - Run: `uv run pytest packages/cleanmast/tests/assessment/ -v`
  - Run: `uv run pytest packages/cleanmast/tests/ -k assessment -v`
  - Verify all tests pass (0 failures)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: Comprehensive verification

  **Parallelization**:
  - **Blocked By**: Tasks 13, 14, 15, 16

  **Acceptance Criteria**:
  - [ ] All assessment tests pass
  - [ ] No test failures

  **QA Scenarios**:
  ```
  Scenario: Full test suite passes
    Tool: Bash (pytest)
    Steps:
      1. uv run pytest packages/cleanmast/tests/assessment/ --tb=short 2>&1 | tail -50
    Expected Result: "passed" count matches total, "failed" = 0
    Evidence: .sisyphus/evidence/final-f1-tests.txt
  ```

- [x] F2. Type check entire package

  **What to do**:
  - Run: `uv run ty check packages/cleanmast`
  - Fix any type errors
  - Ensure no regressions

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Reason**: Type safety verification

  **Parallelization**:
  - **Blocked By**: Tasks 13, 14, 15, 16

  **Acceptance Criteria**:
  - [ ] Type check passes with 0 errors

  **QA Scenarios**:
  ```
  Scenario: Type check passes
    Tool: Bash (ty)
    Steps:
      1. uv run ty check packages/cleanmast 2>&1 | tail -20
    Expected Result: "0 errors", "0 warnings" (or only pre-existing warnings)
    Evidence: .sisyphus/evidence/final-f2-typecheck.txt
  ```

- [x] F3. Import verification (all modules)

  **What to do**:
  - Verify all assessment modules can be imported
  - Run: `python -c "import cleanmast.subdomains.assessment"`
  - Test key imports from new subdomain

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Reason**: Quick smoke test

  **Parallelization**:
  - **Blocked By**: Tasks 13, 14, 15, 16

  **Acceptance Criteria**:
  - [ ] Main module imports successfully
  - [ ] Key classes importable

  **QA Scenarios**:
  ```
  Scenario: All imports work
    Tool: Bash (Python)
    Steps:
      1. python -c "from cleanmast.subdomains.assessment import AnalysisResult, ReportAtom, WindRoseCalculator"
      2. python -c "from cleanmast.subdomains.assessment.domain.services.builders import WindRoseSectionBuilder"
      3. python -c "from cleanmast.subdomains.assessment.infrastructure import TypstRenderer"
    Expected Result: All imports succeed
    Evidence: .sisyphus/evidence/final-f3-imports.txt
  ```

---

## Commit Strategy

| Wave | Commit Message | Files |
|------|---------------|-------|
| 1 | `chore(assessment): create subdomain directory structure` | assessment/** init files |
| 1 | `refactor(assessment): migrate value objects and exports` | Tasks 2, 3, 4 combined |
| 2 | `refactor(assessment): migrate domain services` | Tasks 5, 6, 7, 8 combined |
| 3 | `refactor(assessment): migrate application and infrastructure` | Tasks 9, 10, 11, 12 combined |
| 4 | `refactor(assessment): migrate tests` | Tasks 13, 14 combined |
| 4 | `refactor(assessment): remove old subdomains` | Tasks 15, 16 combined |

---

## Success Criteria

### Verification Commands

```bash
# All tests pass
uv run pytest packages/cleanmast/tests/assessment/ -v

# Type check passes
uv run ty check packages/cleanmast

# Imports work
python -c "from cleanmast.subdomains.assessment import AnalysisResult, ReportAtom"

# Old directories removed
ls packages/cleanmast/src/cleanmast/subdomains/analysis/  # Should fail
ls packages/cleanmast/src/cleanmast/subdomains/reporting/  # Should fail
```

### Final Checklist

- [ ] All 50+ files migrated from analysis/ → assessment/
- [ ] All 60+ files migrated from reporting/ → assessment/
- [ ] All imports updated across codebase
- [ ] All tests pass (100%)
- [ ] Type check passes (0 errors)
- [ ] Old directories deleted
- [ ] No broken references in codebase
- [ ] Git history shows clean migration

---

## Rollback Strategy

If issues arise:

1. **DO NOT DELETE OLD DIRECTORIES UNTIL TASKS F1-F3 PASS**
2. Keep old `analysis/` and `reporting/` until final verification complete
3. Git commits allow reverting any wave
4. Tests can be run against old directories as reference

**Emergency rollback**:
```bash
# Revert to pre-migration state
git reset --hard HEAD~6  # Adjust based on number of commits
```

**Partial rollback** (specific wave failed):
```bash
# Revert specific commit
git revert <commit-hash>
# Fix issues and retry
```

---

*Plan generated by Prometheus for subdomain merge: analysis + reporting → assessment*
