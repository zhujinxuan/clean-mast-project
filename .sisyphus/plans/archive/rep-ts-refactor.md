# rep-ts Command Refactoring - Work Plan

## TL;DR

> **Quick Summary**: Refactor the rep-ts (representative timeseries) report command to properly wire up all 8 report sections (5 currently unused/missing) and rename CLI commands to `report timeseries` and `recommend report timeseries`.
> 
> **Deliverables**:
> - 2 new service methods (`generate_vertical_profile_section`, `generate_wind_frequency_section`)
> - Config with subsection flags (backward compatible)
> - 8 wired sections in usecase respecting config flags
> - Renamed CLI commands with proper group structure
> 
> **Estimated Effort**: Medium (5-6 tasks, ~2-4 hours)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Config → Service methods → Usecase → CLI rename

---

## Context

### Original Request
Refactor the rep-ts command to:
1. Add missing report sections: Vertical Profile, Wind Frequency
2. Wire up unused sections: Weibull, Turbulence, Temporal
3. Rename CLI commands from `rep-ts` → `timeseries`
4. Properly use analyze→atom→section→report architecture

### Interview Summary
**Key Discussions**:
- Handoff document provides detailed architecture analysis
- Current usecase only calls 3 sections; 3 implemented but unused; 2 missing
- Need to respect config subsection flags

**Research Findings**:
- All builders, sections, calculators exist for missing sections
- Test infrastructure: pytest with 49 test files, run via `uv run pytest packages/cleanmast/tests`
- Current pattern inconsistency: some methods take raw `(df, sensors, meta)`, others take `SingleMastAnalysisInput`

### Metis Review
**Identified Gaps** (addressed in this plan):
- Config backward compatibility: Use `default_factory=ReportSubsectionsConfig` for legacy configs
- Method signature: Standardize new methods on `SingleMastAnalysisInput` pattern
- Section ordering: Define canonical order (Monthly Wind → Power → Rose → Profile → Frequency → Weibull → Turbulence → Temporal)
- CLI deprecation: Document old command names in help text

---

## Work Objectives

### Core Objective
Wire up all 8 report sections in the timeseries report command with config-driven subsection enablement, while renaming CLI commands for better clarity.

### Concrete Deliverables
- `report_generation_service.py` with 2 new methods (`generate_vertical_profile_section`, `generate_wind_frequency_section`)
- `RepTsReportConfig` with `ReportSubsectionsConfig` subsection flags
- `generate_report.py` usecase calling all 8 sections based on config flags
- CLI commands renamed to `report timeseries` and `recommend report timeseries`

### Definition of Done
- [ ] All 8 sections appear in generated reports when enabled
- [ ] Config subsection flags control section generation
- [ ] Old rep-ts-report.toml files work without modification
- [ ] CLI commands renamed and functional
- [ ] All existing tests pass

### Must Have
- Backward compatible config loading (legacy toml files work)
- All 8 sections wired in canonical order
- Config flags control section generation
- CLI command rename with group structure

### Must NOT Have (Guardrails)
- No refactoring of existing working methods (monthly_wind, monthly_power, wind_rose)
- No changes to builders/calculators (they already exist and work)
- No changes to output formats (keep Typst/DOCX/PDF as-is)
- No new report types or features beyond wiring existing sections

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES (pytest with 49 test files)
- **Automated tests**: Tests-after (no TDD - existing infrastructure)
- **Framework**: pytest
- **Test strategy**: Run existing tests to ensure no regression, plus integration verification

### QA Policy
Every task includes agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/`.

- **API/Backend**: Use Bash (pytest, python REPL)
- **CLI**: Use Bash (command execution with `--help`, `--version`)
- **Config**: Use Bash (python REPL to load TOML files)

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — Config + Service):
├── Task 1: Add subsection flags to RepTsReportConfig [quick]
└── Task 2: Add missing service methods [unspecified-high]

Wave 2 (After Wave 1 — Usecase + Wiring):
├── Task 3: Wire all sections in usecase with config flags [unspecified-high]
└── Task 4: Update usecase to create input once per mast [quick]

Wave 3 (After Wave 2 — CLI Rename):
├── Task 5: Rename report CLI command [quick]
├── Task 6: Rename recommend CLI command [quick]
└── Task 7: Update CLI exports and main [quick]

Wave FINAL (After ALL tasks — Verification):
├── Task F1: Run test suite [quick]
├── Task F2: Integration test — verify all sections wired [unspecified-high]
└── Task F3: Verify CLI commands work [quick]
-> Present results -> Get explicit user okay
```

### Dependency Matrix

- **Task 1**: — — Task 2, 3
- **Task 2**: 1 — Task 3, 4
- **Task 3**: 1, 2 — Task 5, 6, 7
- **Task 4**: 2 — Task 3
- **Task 5**: 3 — F2, F3
- **Task 6**: 3 — F2, F3
- **Task 7**: 5, 6 — F2, F3

### Agent Dispatch Summary

- **Wave 1**: **2** tasks → T1 (`quick`), T2 (`unspecified-high`)
- **Wave 2**: **2** tasks → T3 (`unspecified-high`), T4 (`quick`)
- **Wave 3**: **3** tasks → T5-T7 (`quick`)
- **FINAL**: **3** tasks → F1-F3 (`quick`/`unspecified-high`)


- [x] 1. Add subsection flags to RepTsReportConfig

  **What to do**:
  - Add `ReportSubsectionsConfig` class with 8 boolean fields (all default True)
  - Add `subsections: ReportSubsectionsConfig` field to `RepTsReportConfig` with `default_factory`
  - Use `pydantic.Field` for default_factory

  **Must NOT do**:
  - Do NOT change existing `masts` field structure
  - Do NOT remove any existing functionality

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
  - **Reason**: Simple Pydantic model extension with clear pattern

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Task 2, Task 3
  - **Blocked By**: None

  **References**:
  - `packages/cleanmast/src/cleanmast/subdomains/assessment/domain/value_objects/rep_ts_report_config.py:1-33` - Current config structure
  - `packages/cleanmast/src/cleanmast/subdomains/assessment/domain/value_objects/report_config.py` - Example with ReportSubsectionConfig pattern

  **Acceptance Criteria**:
  - [ ] `ReportSubsectionsConfig` class exists with 8 boolean fields
  - [ ] `RepTsReportConfig.subsections` field uses `default_factory=ReportSubsectionsConfig`
  - [ ] Code follows ADR-GUARDRAILS comments format

  **QA Scenarios**:
  ```
  Scenario: Config loads with subsection flags
    Tool: Bash (python REPL)
    Steps:
      1. cd packages/cleanmast && uv run python
      2. from cleanmast.subdomains.assessment.domain.value_objects.rep_ts_report_config import RepTsReportConfig, ReportSubsectionsConfig
      3. config = RepTsReportConfig(masts=[])
      4. print(config.subsections.weibull)  # Should be True (default)
    Expected Result: Config loads with default subsection flags
    Evidence: .sisyphus/evidence/task-1-config-load.txt

  Scenario: Legacy config without subsections loads successfully
    Tool: Bash (python REPL)
    Steps:
      1. Create temp toml: echo 'masts = []' > /tmp/test-config.toml
      2. Load: RepTsReportConfig.from_toml(Path('/tmp/test-config.toml'))
    Expected Result: Config loads with default subsection values (backward compatible)
    Evidence: .sisyphus/evidence/task-1-backward-compat.txt
  ```

  **Commit**: YES
  - Message: `feat(assessment): add subsection flags to RepTsReportConfig`
  - Files: `packages/cleanmast/src/cleanmast/subdomains/assessment/domain/value_objects/rep_ts_report_config.py`

- [x] 2. Add missing service methods to ReportGenerationService

  **What to do**:
  - Add `generate_vertical_profile_section(self, input_data, meta)` method
  - Add `generate_wind_frequency_section(self, input_data, meta)` method
  - Import required builders, sections, calculators
  - Follow the pattern from `generate_weibull_section` (uses SingleMastAnalysisInput)

  **Must NOT do**:
  - Do NOT modify existing methods (monthly_wind, monthly_power, wind_rose, weibull, turbulence, temporal)
  - Do NOT change method signatures of existing methods

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []
  - **Reason**: Requires understanding service layer patterns and domain architecture

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 1)
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 3, Task 4
  - **Blocked By**: None (can start immediately)

  **References**:
  - `packages/cleanmast/src/cleanmast/subdomains/assessment/application/services/report_generation_service.py:241-276` - generate_weibull_section pattern
  - `packages/cleanmast/src/cleanmast/subdomains/assessment/domain/services/builders/vertical_profile_builder.py` - Builder for vertical profile
  - `packages/cleanmast/src/cleanmast/subdomains/assessment/domain/services/builders/wind_frequency_builder.py` - Builder for wind frequency
  - `packages/cleanmast/src/cleanmast/subdomains/assessment/domain/services/sections/vertical_profile_subsection.py` - Section class
  - `packages/cleanmast/src/cleanmast/subdomains/assessment/domain/services/sections/wind_frequency_subsection.py` - Section class
  - `packages/cleanmast/src/cleanmast/subdomains/assessment/domain/services/calculators/vertical_profile_analyzer.py` - Calculator for vertical profile
  - `packages/cleanmast/src/cleanmast/subdomains/assessment/domain/services/calculators/wind_frequency_calculator.py` - Calculator for wind frequency

  **Acceptance Criteria**:
  - [ ] `generate_vertical_profile_section` method exists and returns `VerticalProfileSubsection`
  - [ ] `generate_wind_frequency_section` method exists and returns `WindFrequencySubsection`
  - [ ] All required imports added at top of file
  - [ ] Methods follow the same pattern as `generate_weibull_section`

  **QA Scenarios**:
  ```
  Scenario: Service methods exist and are callable
    Tool: Bash (python REPL)
    Steps:
      1. cd packages/cleanmast && uv run python
      2. from cleanmast.subdomains.assessment.application.services.report_generation_service import ReportGenerationService
      3. service = ReportGenerationService()
      4. print(hasattr(service, 'generate_vertical_profile_section'))  # True
      5. print(hasattr(service, 'generate_wind_frequency_section'))   # True
    Expected Result: Both methods exist on service instance
    Evidence: .sisyphus/evidence/task-2-methods-exist.txt

  Scenario: Methods have correct signatures
    Tool: Bash (python)
    Steps:
      1. import inspect
      2. sig = inspect.signature(service.generate_vertical_profile_section)
      3. print(list(sig.parameters.keys()))  # ['self', 'input_data', 'meta']
    Expected Result: Methods accept (self, input_data, meta) parameters
    Evidence: .sisyphus/evidence/task-2-signatures.txt
  ```

  **Commit**: YES
  - Message: `feat(assessment): add vertical profile and wind frequency section generators`
  - Files: `packages/cleanmast/src/cleanmast/subdomains/assessment/application/services/report_generation_service.py`
  - Pre-commit: `uv run pyright packages/cleanmast/src/cleanmast/subdomains/assessment/application/services/report_generation_service.py`

- [x] 3. Wire all sections in usecase with config flags

  **What to do**:
  - Import `ReportSubsectionsConfig` from rep_ts_report_config
  - For each mast, create `SingleMastAnalysisInput` once (outside section loops)
  - For each section, check config flag before generating:
    - `if config.subsections.monthly_wind:` generate_monthly_wind_section
    - `if config.subsections.monthly_power:` generate_monthly_power_section
    - `if config.subsections.wind_rose and has_wd_sensors:` generate_wind_rose_section
    - `if config.subsections.vertical_profile:` generate_vertical_profile_section
    - `if config.subsections.wind_frequency:` generate_wind_frequency_section
    - `if config.subsections.weibull:` generate_weibull_section
    - `if config.subsections.turbulence:` generate_turbulence_section
    - `if config.subsections.temporal:` generate_temporal_section
  - Add sections to builder in canonical order

  **Must NOT do**:
  - Do NOT change section generation logic (just add flag checks)
  - Do NOT change wind_rose conditional (keep WD sensor check)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []
  - **Reason**: Complex orchestration logic with multiple conditions

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 1, Task 2)
  - **Blocked By**: Task 1, Task 2
  - **Blocks**: Task 5, 6, 7

  **References**:
  - `packages/cleanmast/src/cleanmast/application/usecases/generate_report.py:1-122` - Current usecase implementation
  - `packages/cleanmast/src/cleanmast/subdomains/assessment/application/services/report_generation_service.py:241-344` - Service methods to call

  **Acceptance Criteria**:
  - [ ] All 8 sections are conditionally generated based on config flags
  - [ ] `SingleMastAnalysisInput` created once per mast (efficiency fix)
  - [ ] Sections added in canonical order
  - [ ] Wind rose still conditional on WD sensors

  **QA Scenarios**:
  ```
  Scenario: All sections enabled generates all sections
    Tool: Bash (python REPL)
    Steps:
      1. Mock service methods to track calls
      2. Create config with all subsections True
      3. Call generate_report logic
      4. Verify all 8 section methods called
    Expected Result: All 8 section methods invoked
    Evidence: .sisyphus/evidence/task-3-all-sections.txt

  Scenario: Disabled sections are skipped
    Tool: Bash (python REPL)
    Steps:
      1. Create config with subsections.weibull = False
      2. Call generate_report logic
      3. Verify generate_weibull_section NOT called
    Expected Result: Disabled sections skipped
    Evidence: .sisyphus/evidence/task-3-disabled-sections.txt
  ```

  **Commit**: YES
  - Message: `feat(report): wire all 8 sections in timeseries report usecase`
  - Files: `packages/cleanmast/src/cleanmast/application/usecases/generate_report.py`

- [x] 4. Refactor usecase to create input once per mast

  **What to do**:
  - Move `service._create_analysis_input(df, sensors, meta)` call outside section generation loop
  - Pass the same `input_data` to all section methods that need it
  - Update calls to generate_weibull_section, generate_turbulence_section, generate_temporal_section to use pre-created input_data
  - Keep monthly_wind, monthly_power, wind_rose with their current signatures (they create input internally)

  **Must NOT do**:
  - Do NOT change signatures of monthly_wind, monthly_power, wind_rose methods
  - Do NOT change behavior, only efficiency

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
  - **Reason**: Simple refactoring to avoid redundant work

  **Parallelization**:
  - **Can Run In Parallel**: NO (part of Task 3)
  - **Blocked By**: Task 2
  - **Blocks**: Task 3 completion

  **References**:
  - `packages/cleanmast/src/cleanmast/application/usecases/generate_report.py:96-110` - Current section generation loop
  - `packages/cleanmast/src/cleanmast/subdomains/assessment/application/services/report_generation_service.py:112-129` - _create_analysis_input pattern

  **Acceptance Criteria**:
  - [ ] `SingleMastAnalysisInput` created once per mast
  - [ ] Same input_data passed to weibull, turbulence, temporal, vertical_profile, wind_frequency sections
  - [ ] No redundant DataFrame processing

  **QA Scenarios**:
  ```
  Scenario: Input created once per mast
    Tool: Bash (python REPL)
    Steps:
      1. Patch service._create_analysis_input to count calls
      2. Run usecase with 2 masts
      3. Verify _create_analysis_input called exactly 2 times
    Expected Result: One input per mast, not per section
    Evidence: .sisyphus/evidence/task-4-efficiency.txt
  ```

  **Commit**: YES (can group with Task 3)
  - Message: `refactor(report): create analysis input once per mast`
  - Files: `packages/cleanmast/src/cleanmast/application/usecases/generate_report.py`

- [x] 5. Rename report CLI command from rep-ts to timeseries

  **What to do**:
  - Change `@click.command("rep-ts")` to `@click.command("timeseries")` in adapters/cli/generate_report.py
  - Update function name from `report_rep_ts` to `report_timeseries` (optional but recommended)
  - Keep all options (--no-pdf, --no-docx) and functionality identical

  **Must NOT do**:
  - Do NOT change option names or functionality
  - Do NOT change error handling logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
  - **Reason**: Simple command rename

  **Parallelization**:
  - **Can Run In Parallel**: NO (after Task 3)
  - **Blocked By**: Task 3
  - **Blocks**: Task 7

  **References**:
  - `packages/cleanmast/src/cleanmast/adapters/cli/generate_report.py:15` - Current command name
  - `packages/cleanmast/src/cleanmast/cli.py:85` - Where command is registered

  **Acceptance Criteria**:
  - [ ] Command name changed to "timeseries"
  - [ ] All options preserved
  - [ ] Functionality unchanged

  **QA Scenarios**:
  ```
  Scenario: CLI command renamed
    Tool: Bash
    Steps:
      1. uv run cleanmast report --help | grep timeseries
    Expected Result: "timeseries" appears in help output
    Evidence: .sisyphus/evidence/task-5-cli-rename.txt
  ```

  **Commit**: YES
  - Message: `refactor(cli): rename rep-ts command to timeseries`
  - Files: `packages/cleanmast/src/cleanmast/adapters/cli/generate_report.py`

- [x] 6. Rename recommend CLI command from rep-ts-report to timeseries

  **What to do**:
  - Change `@click.command("rep-ts-report")` to `@click.command("timeseries")` in adapters/cli/recommend_report.py
  - Update the group structure: command should be under `recommend report` group, not directly under `recommend`
  - Update next steps message (line 30) to reference new command name
  - Update function name from `recommend_rep_ts_report` to `recommend_timeseries_report` (optional)

  **Must NOT do**:
  - Do NOT change config file name (keep rep-ts-report.toml)
  - Do NOT change the actual recommendation logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
  - **Reason**: Command rename with group restructure

  **Parallelization**:
  - **Can Run In Parallel**: NO (after Task 3)
  - **Blocked By**: Task 3
  - **Blocks**: Task 7

  **References**:
  - `packages/cleanmast/src/cleanmast/adapters/cli/recommend_report.py:15` - Current command name
  - `packages/cleanmast/src/cleanmast/adapters/cli/recommend_report.py:30` - Next steps message
  - `packages/cleanmast/src/cleanmast/cli.py:73` - Where command is registered

  **Acceptance Criteria**:
  - [ ] Command renamed to "timeseries" under "recommend report" group
  - [ ] Next steps message updated
  - [ ] Group structure: `cleanmast recommend report timeseries`

  **QA Scenarios**:
  ```
  Scenario: Recommend command renamed and grouped
    Tool: Bash
    Steps:
      1. uv run cleanmast recommend report --help | grep timeseries
    Expected Result: "timeseries" appears under recommend report group
    Evidence: .sisyphus/evidence/task-6-recommend-rename.txt
  ```

  **Commit**: YES
  - Message: `refactor(cli): rename rep-ts-report to recommend report timeseries`
  - Files: `packages/cleanmast/src/cleanmast/adapters/cli/recommend_report.py`

- [x] 7. Update CLI exports and main registration

  **What to do**:
  - Update `adapters/cli/__init__.py` to export new function names if changed
  - Update `cli.py`:
    - Change `recommend.add_command(recommend_rep_ts_report, "rep-ts-report")` to use new group structure
    - Change `report.add_command(report_rep_ts, "rep-ts")` to use "timeseries"
    - Update imports if function names changed
  - Update error message in usecase/generate_report.py (line 62) to reference new command

  **Must NOT do**:
  - Do NOT break other CLI commands
  - Do NOT change config file paths

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
  - **Reason**: Update registration and exports

  **Parallelization**:
  - **Can Run In Parallel**: NO (after Task 5, 6)
  - **Blocked By**: Task 5, Task 6
  - **Blocks**: Final verification

  **References**:
  - `packages/cleanmast/src/cleanmast/adapters/cli/__init__.py:1-20` - Current exports
  - `packages/cleanmast/src/cleanmast/cli.py:73,85` - Command registrations
  - `packages/cleanmast/src/cleanmast/application/usecases/generate_report.py:62` - Error message

  **Acceptance Criteria**:
  - [ ] All exports updated
  - [ ] cli.py registrations updated
  - [ ] Error message updated
  - [ ] Both commands work: `report timeseries` and `recommend report timeseries`

  **QA Scenarios**:
  ```
  Scenario: Both CLI commands work end-to-end
    Tool: Bash
    Steps:
      1. uv run cleanmast report timeseries --help
      2. uv run cleanmast recommend report timeseries --help
    Expected Result: Both commands show help without errors
    Evidence: .sisyphus/evidence/task-7-cli-complete.txt
  ```

  **Commit**: YES (can group with Tasks 5-6)
  - Message: `refactor(cli): update exports and registrations for timeseries commands`
  - Files: 
    - `packages/cleanmast/src/cleanmast/adapters/cli/__init__.py`
    - `packages/cleanmast/src/cleanmast/cli.py`
    - `packages/cleanmast/src/cleanmast/application/usecases/generate_report.py`

---

## Final Verification Wave

> 3 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user.

- [x] F1. **Run Test Suite** — `quick`
  Run `uv run pytest packages/cleanmast/tests -v` and verify all tests pass.
  Output: `Tests [N pass/N fail] | VERDICT: PASS/FAIL`

- [x] F2. **Integration Test — All Sections Wired** — `unspecified-high`
  Create a test script that:
  1. Creates a mock config with all subsections enabled
  2. Mocks the service and verifies all 8 section methods are called
  3. Verifies sections are added in correct order
  Save evidence to `.sisyphus/evidence/f2-integration-test.txt`
  Output: `Sections [8/8 wired] | Order [CORRECT/INCORRECT] | VERDICT`

- [x] F3. **Verify CLI Commands** — `quick`
  Run:
  - `uv run cleanmast report --help` → verify "timeseries" appears
  - `uv run cleanmast recommend report --help` → verify "timeseries" appears
  - `uv run cleanmast report timeseries --help` → verify command works
  Save evidence to `.sisyphus/evidence/f3-cli-commands.txt`
  Output: `Commands [2/2 renamed] | VERDICT`

---

## Commit Strategy

- **Task 1**: `feat(assessment): add subsection flags to RepTsReportConfig`
- **Task 2**: `feat(assessment): add vertical profile and wind frequency section generators`
- **Task 3**: `feat(report): wire all 8 sections in timeseries report usecase`
- **Task 4**: `refactor(report): create analysis input once per mast`
- **Task 5-7**: `refactor(cli): rename rep-ts commands to timeseries`

---

## Success Criteria

### Verification Commands
```bash
# Test suite passes
uv run pytest packages/cleanmast/tests -v
# Expected: All tests pass

# CLI commands work
uv run cleanmast report timeseries --help
uv run cleanmast recommend report timeseries --help
# Expected: Help text displayed without errors

# Config loads with defaults
uv run python -c "from cleanmast.subdomains.assessment.domain.value_objects.rep_ts_report_config import RepTsReportConfig; c = RepTsReportConfig(masts=[]); print(c.subsections.weibull)"
# Expected: True
```

### Final Checklist
- [ ] All 8 sections can be generated (when enabled in config)
- [ ] Config subsection flags control which sections appear
- [ ] Old rep-ts-report.toml files load without errors
- [ ] CLI commands renamed to `report timeseries` and `recommend report timeseries`
- [ ] All existing tests pass
- [ ] Integration test verifies section wiring
