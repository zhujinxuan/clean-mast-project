# Master Plan: Section/Subsection Integration

## TL;DR

Update the existing timeseries report section to use the new atom-based architecture with 6 optional subsections (WindRose, WindTemporal, Weibull, WindFrequency, Turbulence, VerticalProfile).

**This is the integration layer** that connects all atom implementations to the final report generation.

---

## Context

### Current State
The codebase has:
- Existing timeseries report generation (Julia-based)
- New atom architecture (partially implemented)
- 6 analysis types each with multiple atoms (~25 total)

### Target State
- Single `TimeSeriesReportSection` with 6 optional subsections
- Each subsection configurable (on/off in config)
- Each subsection aggregates relevant atoms
- All rendering through atom.render() methods

---

## Architecture

```
TimeSeriesReportSection (main section)
├── WindRoseSubsection (optional)
│   ├── SingleMastMonthlyWindFrequencyRoseAtom
│   ├── SingleMastWindPowerRoseAtom
│   └── SingleMastMonthlyWindRoseGridAtom
├── WindTemporalSubsection (optional)
│   ├── SingleMastWindTimeseriesAtom
│   ├── SingleMastDailyPatternAtom
│   ├── SingleMastMonthlyPatternAtom
│   └── SingleMastMonthlyDailyWindAtom
├── WeibullSubsection (optional)
│   ├── SingleMastWeibullParametersAtom
│   ├── SingleMastWeibullDistributionAtom
│   └── SingleMastWeibullMultiHeightAtom
├── WindFrequencySubsection (optional)
│   ├── SingleMastWindFrequencyTableAtom
│   └── SingleMastWindFrequencyDistributionAtom
├── TurbulenceSubsection (optional)
│   ├── SingleMastTurbulenceIntensityAtom
│   ├── SingleMastTurbulenceSectorAtom
│   └── SingleMastTurbulenceMultiHeightAtom
└── VerticalProfileSubsection (optional)
    ├── SingleMastVerticalProfileAtom
    ├── SingleMastWindShearTableAtom
    └── SingleMastWindShearExponentAtom
```

---

## Work Objectives

### Deliverables
1. Configuration schema for subsection toggles
2. TimeSeriesReportSection (main orchestrator)
3. 6 Subsection classes
4. Report generation command
5. Tests

### Definition of Done
```python
# Can generate report with selective subsections
config = ReportConfig(
    windrose=True,      # Include
    windtemporal=True,  # Include
    weibull=False,      # Exclude
    windfrequency=True,
    turbulence=False,
    verticalprofile=True,
)

section = TimeSeriesReportSection(mast_data, config)
typst_content = section.render(output_dir)
```

---

## Execution Strategy

### Prerequisites
All atom implementation plans must be complete:
- ✅ WindRose atoms (`.sisyphus/plans/implement-windrose-atoms.md`)
- ✅ Weibull atoms (`.sisyphus/plans/implement-weibull-atoms.md`)
- ✅ Turbulence atoms (`.sisyphus/plans/implement-turbulence-atoms.md`)
- ✅ WindFrequency atoms (`.sisyphus/plans/implement-windfrequency-atoms.md`)
- ✅ WindTemporal atoms (`.sisyphus/plans/implement-windtemporal-atoms.md`)
- ✅ VerticalProfile atoms (`.sisyphus/plans/implement-verticalprofile-atoms.md`)

### Wave 1: Configuration
- Task 1: ReportConfig with subsection toggles

### Wave 2: Subsections (Parallel)
- Task 2: WindRoseSubsection
- Task 3: WindTemporalSubsection
- Task 4: WeibullSubsection
- Task 5: WindFrequencySubsection
- Task 6: TurbulenceSubsection
- Task 7: VerticalProfileSubsection

### Wave 3: Main Section + Command
- Task 8: TimeSeriesReportSection (orchestrator)
- Task 9: Report generation command

### Wave 4: Tests
- Task 10: Integration tests
- Task 11: End-to-end report generation test

---

## TODOs

- [ ] 1. ReportConfig Schema
  **What**: Configuration dataclass with subsection toggles
  **Files**: `subdomains/reporting/value_objects/report_config.py`
  **Fields**:
  ```python
  @dataclass
  class ReportSubsectionConfig:
      windrose: bool = True
      windtemporal: bool = True
      weibull: bool = True
      windfrequency: bool = True
      turbulence: bool = True
      verticalprofile: bool = True
  ```

- [ ] 2. WindRoseSubsection
  **What**: Aggregates wind rose atoms, generates subsection content
  **Files**: `subdomains/reporting/services/sections/wind_rose_subsection.py`
  **Renders**:
  - Overall frequency rose
  - Overall power rose (if air density)
  - Monthly frequency grid
  - Monthly power grid (if air density)

- [ ] 3. WindTemporalSubsection
  **Files**: `subdomains/reporting/services/sections/wind_temporal_subsection.py`
  **Renders**: Timeseries, daily, monthly, monthly-daily grid

- [ ] 4. WeibullSubsection
  **Files**: `subdomains/reporting/services/sections/weibull_subsection.py`
  **Renders**: Parameters table, distribution plots per height, multi-height plot

- [ ] 5. WindFrequencySubsection
  **Files**: `subdomains/reporting/services/sections/wind_frequency_subsection.py`
  **Renders**: Frequency tables, distribution charts, 3-25m/s summary

- [ ] 6. TurbulenceSubsection
  **Files**: `subdomains/reporting/services/sections/turbulence_subsection.py`
  **Renders**: TI charts with IEC bands, sector analysis, Meteodyn export

- [ ] 7. VerticalProfileSubsection
  **Files**: `subdomains/reporting/services/sections/vertical_profile_subsection.py`
  **Renders**: Profile plot, shear table, shear matrix

- [ ] 8. TimeSeriesReportSection (Main)
  **Files**: `subdomains/reporting/services/sections/timeseries_report_section.py`
  **What**: Main orchestrator that:
  - Reads config
  - Instantiates enabled subsections
  - Runs analyses
  - Converts to atoms
  - Renders each subsection
  - Combines into final Typst document

- [ ] 9. Report Generation Command
  **Files**: `application/commands/generate_timeseries_report.py`
  **What**: CLI entry point for report generation
  **Interface**:
  ```bash
  cleanmast report timeseries \
    --config report_config.yaml \
    --output ./reports/
  ```

- [ ] 10. Integration Tests
  **Files**: `tests/report/test_subsections.py`
  **What**: Test each subsection independently

- [ ] 11. End-to-End Test
  **Files**: `tests/report/test_full_report.py`
  **What**: Generate complete report, verify Typst output

---

## Configuration File Format

```yaml
# report_config.yaml
mast_name: "M01"
input_data: "./data/m01.parquet"

subsections:
  windrose:
    enabled: true
    include_power: true
  windtemporal:
    enabled: true
    include_power: true
  weibull:
    enabled: true
  windfrequency:
    enabled: true
    include_power: true
  turbulence:
    enabled: false  # Skip turbulence
  verticalprofile:
    enabled: true

air_density:
  method: "constant"
  value: 1.225

output:
  directory: "./reports/M01"
  format: "typst"
```

---

## Section Rendering Flow

```python
class TimeSeriesReportSection:
    def __init__(self, mast_data, config):
        self.mast_data = mast_data
        self.config = config
        self.subsections = self._instantiate_subsections()
    
    def _instantiate_subsections(self):
        subsections = []
        if self.config.windrose:
            subsections.append(WindRoseSubsection(self.mast_data))
        if self.config.windtemporal:
            subsections.append(WindTemporalSubsection(self.mast_data))
        # ... etc
        return subsections
    
    def render(self, output_dir: Path) -> str:
        """Generate complete Typst document."""
        lines = []
        
        # Document header
        lines.append(f"= 测风塔{self.mast_data.name}分析报告")
        lines.append("")
        
        # Render each subsection
        for subsection in self.subsections:
            subsection_content = subsection.render(output_dir)
            lines.append(subsection_content)
            lines.append("")
        
        return "\n".join(lines)
```

---

## Typst Output Structure

```typst
= 测风塔M01分析报告

== 风向风能分布
#figure(image("windrose_xxx.png"), caption: [...])
#table(...)
...

== 风速时序分析
#figure(image("timeseries_xxx.png"), caption: [...])
...

== Weibull分布拟合
...

== 风速频率分析
...

== 湍流强度分析
...

== 垂直风廓线
...
```

---

## Dependencies Between Tasks

```
Task 1 (Config) -> Tasks 2-7 (Subsections)
Tasks 2-7 -> Task 8 (Main Section)
Task 8 -> Task 9 (Command)
Task 9 -> Tasks 10-11 (Tests)

All atom implementations must be complete before Task 2.
```

---

## Success Criteria

- [ ] All 6 subsections implemented
- [ ] Each subsection can be enabled/disabled via config
- [ ] Main section orchestrates correctly
- [ ] Typst output is valid and renders
- [ ] Report generation command works end-to-end
- [ ] Integration tests pass
- [ ] At least one full report generated successfully
- [ ] Performance: Report generates in <30 seconds for typical dataset

---

## Execution Order

**Phase 1**: Execute all atom implementation plans first
- Run: `/start-work implement-windrose-atoms`
- Run: `/start-work implement-weibull-atoms`
- Run: `/start-work implement-turbulence-atoms`
- Run: `/start-work implement-windfrequency-atoms`
- Run: `/start-work implement-windtemporal-atoms`
- Run: `/start-work implement-verticalprofile-atoms`

**Phase 2**: Execute this master plan
- Run: `/start-work section-subsection-integration`

**Parallelism**: Phase 1 can run in parallel (6 separate work sessions). Phase 2 must wait for all Phase 1 completion.
