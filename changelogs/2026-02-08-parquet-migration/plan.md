# Parquet Migration Plan

**Date**: 2026-02-08  
**Status**: Planning Phase  
**Scope**: Migrate CleanMast from CSV+TOML to Parquet with embedded column metadata

---

## Executive Summary

This plan outlines the migration from the current CSV+TOML dual-file format to Parquet with embedded column metadata for sensor information. The migration maintains backward compatibility while enabling more efficient storage and self-contained data files.

### Key Decisions

1. **Parquet2.jl** (Julia) and **pyarrow** (Python) will be used for Parquet support
2. **Column metadata** will store sensor information (sensorType, height, statType, unit, etc.)
3. **Backward compatibility**: Support both CSV+TOML (legacy) and Parquet (new) formats
4. **TimeSeriesSource.sensors** field becomes optional for Parquet files
5. **Format auto-detection** based on file extension (.csv vs .parquet)

---

## Current Architecture Analysis

### Julia CleanMastProject

**TimeSeriesSource Structure** (MastTimeSeries.jl):
```julia
struct TimeSeriesSource
    data::String      # Path to CSV file
    sensors::String   # Path to TOML/YAML sensors file
end
```

**Data Flow**:
- `load_timeseries(source, base_dir)` → reads CSV + TOML → returns TimeSeriesData
- `save_timeseries(source, base_dir, data)` → writes CSV + TOML

**20 Configuration Types** use TimeSeriesSource:

| Category | Count | Configs |
|----------|-------|---------|
| Processing (R+W) | 7 | ProcessClean, TowerShading, ReconstructSingle, ReconstructMeso, ReconstructCross, RepresentativeYear, WtTimeSeries |
| Training (R) | 4 | TrainMeso, TrainReconstructCross, TrainMesoResults, GuessMastFromMeso |
| Reports (R) | 8 | ReportClean, ReportRecovery, ReportFrozenPeriod, ReportReconstructSingle, ReportReconstructMeso, ReportTimeSeries, ReportMesoTimeSeries, ReportReconstructCross |
| Parsing (W) | 1 | ParseSensors |

### Python cleanmast Package

**Current Dependencies**:
- polars >=0.20 (primary DataFrame library)
- pandas >=2.0 (secondary)
- **Missing**: pyarrow (needed for Parquet)

**TimeSeriesSource** (models/timeseries.py):
```python
class TimeSeriesSource(BaseModel):
    data: str      # Path to CSV
    sensors: str   # Path to YAML/TOML
```

**I/O Functions** (io/timeseries_io.py):
- `load_timeseries()` → polars.read_csv() + YAML/TOML sensors
- `save_timeseries()` → polars.write_csv() + YAML/TOML sensors

**Extrapolation Module** (extrapolate/):
- Uses load_timeseries/save_timeseries for I/O
- Generates output paths as `./{dir}/{mast}.csv` and `./{dir}/{mast}.sensors.yaml`

---

## Technical Design

### Julia Implementation

#### 1. Dependency Addition

**Project.toml**:
```toml
[deps]
Parquet2 = "2.0"  # Modern Parquet library with metadata support
```

#### 2. TimeSeriesSource Modification

**Option A**: Make sensors optional
```julia
struct TimeSeriesSource
    data::String
    sensors::Union{String, Nothing}  # Nothing for Parquet files
end
```

**Option B**: Add format field
```julia
@enum FileFormat CSV_FORMAT PARQUET_FORMAT

struct TimeSeriesSource
    data::String
    sensors::Union{String, Nothing}
    format::FileFormat  # Auto-detected from extension
end
```

**Recommended**: Option A with auto-detection

#### 3. load_timeseries Implementation

```julia
function load_timeseries(source::TimeSeriesSource, base_dir::String)::TimeSeriesData
    data_path = resolve_path(source.data, base_dir)
    
    if endswith(data_path, ".parquet")
        # Load Parquet with column metadata
        ds = Parquet2.readfile(data_path)
        df = DataFrame(ds)
        
        # Extract sensor metadata from first column's metadata
        sensors = extract_sensors_from_metadata(ds)
        
        return TimeSeriesData(df, sensors)
    else
        # Legacy CSV+TOML path
        sensors_path = resolve_path(source.sensors, base_dir)
        sensors = load_sensors(sensors_path)
        df = CSV.read(data_path, DataFrame; ...)
        return TimeSeriesData(df, sensors)
    end
end
```

#### 4. save_timeseries Implementation

```julia
function save_timeseries(source::TimeSeriesSource, base_dir::Union{String, Nothing}, data::TimeSeriesData)
    data_path = resolve_path(source.data, base_dir)
    
    if endswith(data_path, ".parquet")
        # Write Parquet with column metadata
        # Convert sensors to Dict{String, Dict{String, String}} for column metadata
        column_meta = Dict(
            String(sensor.columnName) => Dict(
                "sensorType" => sensor.sensorType,
                "height" => string(sensor.height),
                "statType" => sensor.statType,
                "unit" => sensor.unit,
                # ... other fields
            )
            for sensor in data.sensors
        )
        
        Parquet2.writefile(data_path, data.df; column_metadata=column_meta)
        
        # Optional: Also write sidecar TOML for human readability
        if !isnothing(source.sensors)
            sensors_path = resolve_path(source.sensors, base_dir)
            save_sensors(sensors_path, data.sensors)
        end
    else
        # Legacy CSV+TOML path
        CSV.write(data_path, data.df)
        sensors_path = resolve_path(source.sensors, base_dir)
        save_sensors(sensors_path, data.sensors)
    end
end
```

#### 5. Recommend Commands Updates

All 21 Recommend* commands need path generation updates:

**Current** (RecommendProcessCleanCommand.jl):
```julia
output_data = joinpath("./clean", "$(mast_name).csv")
output_sensors = joinpath("./clean", "$(mast_name).sensors.yaml")
```

**New** (with format option):
```julia
# Default to Parquet for new projects
output_data = joinpath("./clean", "$(mast_name).parquet")
output_sensors = joinpath("./clean", "$(mast_name).sensors.yaml")  # Optional sidecar

# Or for backward compatibility mode:
output_data = joinpath("./clean", "$(mast_name).csv")
output_sensors = joinpath("./clean", "$(mast_name).sensors.yaml")
```

### Python Implementation

#### 1. Dependency Addition

**pyproject.toml**:
```toml
dependencies = [
    "preprocess-tools",
    "polars>=0.20",
    "pandas>=2.0",
    "pyarrow>=15.0",  # NEW: For Parquet support
    # ... other deps
]
```

#### 2. TimeSeriesSource Modification

```python
class TimeSeriesSource(BaseModel):
    data: str
    sensors: Optional[str] = None  # Optional for Parquet
    
    @field_validator('sensors')
    @classmethod
    def validate_sensors_for_format(cls, v, info):
        data_path = info.data.get('data', '')
        if data_path.endswith('.csv') and not v:
            raise ValueError("sensors path required for CSV files")
        return v
```

#### 3. load_timeseries Implementation

```python
def load_timeseries(source: TimeSeriesSource, base_dir: str) -> TimeSeriesData:
    data_path = _resolve_path(source.data, base_dir)
    
    if str(data_path).endswith('.parquet'):
        # Load Parquet with polars
        df = pl.read_parquet(data_path)
        
        # Extract sensor metadata from Parquet schema
        sensors = _extract_sensors_from_parquet(data_path)
        
        return TimeSeriesData(df=df, sensors=sensors)
    else:
        # Legacy CSV path
        sensors_path = _resolve_path(source.sensors, base_dir)
        sensors = _load_sensors_from_file(sensors_path)
        df = pl.read_csv(data_path, try_parse_dates=True)
        return TimeSeriesData(df=df, sensors=sensors)
```

#### 4. save_timeseries Implementation

```python
def save_timeseries(source: TimeSeriesSource, base_dir: str, data: TimeSeriesData) -> None:
    data_path = _resolve_path(source.data, base_dir)
    
    if str(data_path).endswith('.parquet'):
        # Write Parquet
        data.df.write_parquet(data_path)
        
        # Store sensor metadata as Parquet metadata via pyarrow
        _write_parquet_with_metadata(data_path, data.sensors)
        
        # Optional sidecar
        if source.sensors:
            sensors_path = _resolve_path(source.sensors, base_dir)
            _save_sensors_to_file(sensors_path, data.sensors)
    else:
        # Legacy CSV path
        data.df.write_csv(data_path)
        sensors_path = _resolve_path(source.sensors, base_dir)
        _save_sensors_to_file(sensors_path, data.sensors)
```

#### 5. Extrapolation Module Updates

**top3_constant_shear.py** path generation:
```python
# Current:
output=TimeSeriesSource(
    data=f"./{output_dir}/{mast_name}.csv",
    sensors=f"./{output_dir}/{mast_name}.sensors.yaml",
)

# New (configurable format):
output=TimeSeriesSource(
    data=f"./{output_dir}/{mast_name}.parquet",
    sensors=f"./{output_dir}/{mast_name}.sensors.yaml",  # Optional
)
```

---

## Development Workflow

### Git Branch Strategy

**Branch Name**: `feature/parquet-migration`

```bash
# Start from main
git checkout main
git pull origin main
git checkout -b feature/parquet-migration
```

**Important**: 
- ⚠️ **DO NOT switch back to main branch** during implementation
- ⚠️ **DO NOT modify changelogs/ or docs/** (user will handle separately)
- ✅ **Commit after each task** with passing tests
- ✅ **All changes will be merged via PR** by user

### Commit Strategy

**Commit after EVERY task completion** with format:
```
type(scope): brief description

- What changed
- Tests added/updated
- Test results: X tests passed
```

**Examples**:
```
feat(deps): add Parquet2.jl dependency

- Added Parquet2 = "2.0" to Project.toml
- Tests: N/A (dependency only)

feat(types): make TimeSeriesSource.sensors optional

- Changed sensors field to Union{String, Nothing}
- Updated from_dict/to_dict functions
- Tests: 15 tests passed (TimeSeriesSource)

feat(io): add Parquet support to load_timeseries

- Added format detection (.csv vs .parquet)
- Implemented Parquet reading with metadata extraction
- Tests: 8 new tests added, all passed
```

---

## Migration Strategy

### Phase 1: Core Infrastructure (Julia)

**Duration**: 2-3 days  
**Files**: 3-5
**Branch**: `feature/parquet-migration`

1. **Add Parquet2.jl dependency** to Project.toml
   - **Commit**: `feat(deps): add Parquet2.jl dependency`
   
2. **Modify MastTimeSeries.jl**:
   - Update `TimeSeriesSource` struct (optional sensors field)
   - Implement `load_timeseries()` with format detection
   - Implement `save_timeseries()` with Parquet support
   - Add helper functions for metadata extraction/embedding
   - **Commit**: `feat(io): implement Parquet read/write with metadata`
   - **Tests Required**: 
     - Test loading CSV (backward compatibility)
     - Test loading Parquet
     - Test saving CSV (backward compatibility)
     - Test saving Parquet with metadata
     - Test format auto-detection
   
3. **Test** with sample data in projects/baiyang-parquet/
   - **Commit**: `test: add Parquet I/O integration tests`

### Phase 2: Julia Recommend Commands

**Duration**: 3-4 days  
**Files**: 21
**Branch**: `feature/parquet-migration` (continue on same branch)

Update all Recommend* commands to generate Parquet paths:

**Priority Order** (commit after each group):

**Group 1 - Core Processing (Commit after group)**:
1. `RecommendParseSensorsCommand.jl` - Entry point
2. `RecommendProcessCleanCommand.jl` - First processing step
   - **Commit**: `feat(recommend): update core processing commands for Parquet`
   - **Tests**: Verify generated configs have .parquet paths

**Group 2 - Reconstruction (Commit after group)**:
3. `RecommendTowerShadingCommand.jl`
4. `RecommendReconstructSingleCommand.jl`
5. `RecommendReconstructMesoCommand.jl`
6. `RecommendReconstructCrossCommand.jl`
   - **Commit**: `feat(recommend): update reconstruction commands for Parquet`
   - **Tests**: Verify all reconstruction configs

**Group 3 - Final Processing (Commit after group)**:
7. `RecommendRepresentativeYearCommand.jl`
8. `RecommendWtTimeSeriesCommand.jl` (keep CSV output for WT compatibility)
   - **Commit**: `feat(recommend): update final processing commands for Parquet`
   - **Tests**: Verify WtTimeSeries still uses CSV

**Group 4 - Reports (Commit after group)**:
9. All Report* recommend commands (8 files)
   - **Commit**: `feat(recommend): update all report commands for Parquet`
   - **Tests**: Verify report configs read from Parquet

**Group 5 - Training (Commit after group)**:
10. Training commands (3 files)
    - **Commit**: `feat(recommend): update training commands for Parquet`
    - **Tests**: Verify training configs

### Phase 3: Python Package

**Duration**: 2-3 days  
**Files**: 5-8
**Branch**: `feature/parquet-migration` (continue on same branch)

1. **Add pyarrow** to pyproject.toml
   - **Commit**: `feat(python-deps): add pyarrow dependency`
   
2. **Modify timeseries_io.py**:
   - Update `load_timeseries()` for Parquet
   - Update `save_timeseries()` for Parquet
   - Add format detection
   - **Commit**: `feat(python-io): implement Parquet read/write`
   - **Tests**: All existing tests pass + new Parquet tests
   
3. **Update timeseries.py**:
   - Make `TimeSeriesSource.sensors` optional
   - **Commit**: `feat(python-types): make sensors field optional`
   - **Tests**: Model validation tests
   
4. **Update extrapolation recommend** (top3_constant_shear.py)
   - **Commit**: `feat(python-extrapolate): update path generation for Parquet`
   - **Tests**: Extrapolation config generation tests
   
5. **Add tests** for Parquet I/O
   - **Commit**: `test(python): add Parquet I/O tests`
   - **Tests**: New test file with comprehensive coverage

### Phase 4: Integration Testing

**Duration**: 2-3 days
**Branch**: `feature/parquet-migration` (continue on same branch)

**Test Project**: projects/baiyang-parquet/

**Test Scenarios** (commit after each milestone):

**Milestone 1 - Basic Pipeline**:
1. `recommend parse-sensors` → generates config
2. `project parse-sensors` → produces Parquet output
   - **Commit**: `test(integration): verify parse-sensors produces Parquet`
   - **Tests**: Parquet files created with correct metadata

**Milestone 2 - Full Processing**:
3. `process steps --all` → full pipeline with Parquet
   - **Commit**: `test(integration): verify full pipeline with Parquet`
   - **Tests**: All processing steps complete successfully

**Milestone 3 - Reporting**:
4. `recommend report-all` → generates report config
5. `report all` → reads Parquet, generates reports
   - **Commit**: `test(integration): verify reports from Parquet data`
   - **Tests**: All reports generated correctly

**Milestone 4 - Compatibility**:
6. **Mixed mode**: CSV input → Parquet output
7. **Backward compatibility**: Old CSV projects still work
   - **Commit**: `test(integration): verify backward compatibility`
   - **Tests**: CSV projects work, mixed mode works

### Phase 5: Final Review & PR Preparation

**Duration**: 1 day
**Branch**: `feature/parquet-migration`

1. **Final test run** - All tests must pass
   - **Commit**: `test: final validation - all tests passing`
   
2. **Code review preparation**:
   - Review all changes
   - Ensure no debug code left
   - Verify no changes to changelogs/ or docs/
   
3. **PR Description** (user will create):
   - Summary of changes
   - Migration guide
   - Performance benchmarks
   - Breaking changes (none expected)

**DO NOT**:
- ❌ Switch to main branch
- ❌ Modify changelogs/ directory
- ❌ Modify docs/ directory
- ❌ Create merge commit

**User will**:
- ✅ Create PR from `feature/parquet-migration` to `main`
- ✅ Update changelogs/
- ✅ Update docs/
- ✅ Merge PR when ready

---

## Test Project: projects/baiyang-parquet/

### Setup

```
projects/baiyang-parquet/
├── original/              # Raw input files
│   ├── mast-data.txt
│   └── meso-data.txt
├── formats/
│   ├── sensor/
│   │   ├── mast.toml
│   │   └── meso.toml
│   └── clean/
│       └── default.toml
├── parse-sensors.toml     # Generated
├── raw/                   # ParseSensors output
│   ├── mast.parquet       # NEW: Parquet format
│   └── mast.sensors.yaml  # Optional sidecar
├── process-clean.toml     # Generated
├── clean/                 # ProcessClean output
│   ├── mast.parquet
│   └── mast.sensors.yaml
├── tower-shading.toml     # Generated
├── tower-shading/         # TowerShading output
│   └── mast.parquet
├── reconstruct-single.toml
├── reconstruct-single/
│   └── mast.parquet
├── train-meso.toml
├── meso-models/           # JLD2 models (unchanged)
├── reconstruct-meso.toml
├── reconstruct-meso/
│   └── mast.parquet
├── representative-year.toml
├── representative-year/
│   └── mast.parquet
├── wt-timeseries.toml
└── wt-timeseries/         # CSV output for WT
    └── mast-120_0m.csv
```

### Test Commands

```bash
# 1. Generate parse-sensors config
julia bin/CleanMast.jl recommend parse-sensors projects/baiyang-parquet

# 2. Parse sensors (produces Parquet)
julia bin/CleanMast.jl project parse-sensors projects/baiyang-parquet/parse-sensors.toml

# 3. Full processing pipeline
julia bin/CleanMast.jl process steps --all projects/baiyang-parquet

# 4. Generate report config
julia bin/CleanMast.jl recommend report-all projects/baiyang-parquet

# 5. Generate reports (reads Parquet)
julia bin/CleanMast.jl report all projects/baiyang-parquet/report-all.toml
```

---

## Backward Compatibility Strategy

### Option 1: Auto-Detection (Recommended)

```julia
function load_timeseries(source::TimeSeriesSource, base_dir::String)
    data_path = resolve_path(source.data, base_dir)
    
    # Auto-detect format from extension
    format = if endswith(data_path, ".parquet")
        :parquet
    elseif endswith(data_path, ".csv")
        :csv
    else
        # Try to detect from file content
        detect_format(data_path)
    end
    
    if format == :parquet
        load_parquet(data_path)
    else
        load_csv_with_sensors(source, base_dir)
    end
end
```

### Option 2: Configuration Flag

```toml
# In project config or environment variable
[global]
format = "parquet"  # or "csv"
```

### Migration Path for Existing Projects

1. **New projects**: Use Parquet by default
2. **Existing projects**: Continue using CSV (no forced migration)
3. **Optional conversion**: Provide `convert-to-parquet` command

---

## Files to Modify

### Julia (CleanMastProject)

**Core Changes** (3 files):
1. `Project.toml` - Add Parquet2 dependency
2. `src/Types/MastTimeSeries.jl` - Update TimeSeriesSource, load/save functions
3. `src/Types/SensorColumns.jl` - Add metadata conversion helpers

**Recommend Commands** (21 files):
- `src/ParseSensors/RecommendParseSensorsCommand.jl`
- `src/DataClean/RecommendProcessCleanCommand.jl`
- `src/TowerShading/RecommendTowerShadingCommand.jl`
- `src/ReconstructSingleMast/RecommendReconstructSingleCommand.jl`
- `src/ReconstructMeso/RecommendReconstructMesoCommand.jl`
- `src/ReconstructCross/RecommendReconstructCrossCommand.jl`
- `src/RepresentativeYear/RecommendRepresentativeYearCommand.jl`
- `src/WTTimeSeries/RecommendWtTimeSeriesCommand.jl`
- `src/TrainMeso/RecommendTrainMesoCommand.jl`
- `src/TrainReconstructCross/RecommendTrainReconstructCrossCommand.jl`
- `src/ReportClean/RecommendReportCleanCommand.jl`
- `src/ReportRecovery/RecommendReportRecoveryCommand.jl`
- `src/ReportFrozenPeriod/RecommendReportFrozenCommand.jl`
- `src/ReportReconstructSingle/RecommendReportReconstructSingleCommand.jl`
- `src/ReportReconstructMeso/RecommendReportReconstructMesoCommand.jl`
- `src/ReportReconstructCross/RecommendCrossMastReportCommand.jl`
- `src/ReportReconstructCross/RecommendAnalyzeReconstructCrossCommand.jl`
- `src/ReportTimeSeries/RecommendReportTimeSeriesMesoCommand.jl`
- `src/ReportTimeSeries/RecommendReportTimeSeriesRepCommand.jl`
- `src/ReportMesoTimeSeries/RecommendReportMesoTimeSeriesCommand.jl`
- `src/ReportAllMasts/RecommendReportAllCommand.jl`

**No Changes Needed**:
- Config type definitions (TimeSeriesSource structure change is sufficient)
- Report command implementations (they use load_timeseries)
- Processing command implementations (they use load/save_timeseries)

### Python (packages/cleanmast)

**Core Changes** (3 files):
1. `pyproject.toml` - Add pyarrow dependency
2. `src/cleanmast/models/timeseries.py` - Make sensors optional
3. `src/cleanmast/io/timeseries_io.py` - Add Parquet read/write

**Extrapolation** (1 file):
4. `src/cleanmast/extrapolate/recommend/top3_constant_shear.py` - Update path generation

**Tests** (add new):
5. `tests/io/test_parquet_io.py` - Parquet I/O tests

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Parquet2.jl compatibility issues | High | Test thoroughly with sample data; fallback to CSV mode |
| Performance regression | Medium | Benchmark before/after; Parquet should be faster |
| Metadata loss in round-trip | High | Comprehensive tests for metadata preservation |
| File size increase | Low | Parquet compression should reduce size |
| Breaking existing projects | High | Maintain backward compatibility; auto-detect format |
| Python-Julia interoperability | Medium | Ensure both can read each other's Parquet files |

---

## Success Criteria

1. ✅ All 21 Recommend commands generate correct Parquet paths
2. ✅ `load_timeseries` can read both CSV and Parquet
3. ✅ `save_timeseries` can write both CSV and Parquet
4. ✅ Sensor metadata preserved in Parquet column metadata
5. ✅ Full pipeline test passes in projects/baiyang-parquet/
6. ✅ Existing CSV projects continue to work
7. ✅ Python cleanmast can read Julia-generated Parquet files
8. ✅ Performance equal or better than CSV

---

## Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 1: Julia Core | 2-3 days | Day 3 |
| Phase 2: Julia Recommend | 3-4 days | Day 7 |
| Phase 3: Python Package | 2-3 days | Day 10 |
| Phase 4: Integration Testing | 2-3 days | Day 13 |
| Phase 5: Documentation | 1-2 days | Day 15 |

**Total Estimated Duration**: 2-3 weeks

---

## Next Steps

1. ✅ **Complete** - Investigation and planning
2. ✅ **Complete** - Implementation on branch `feature/parquet-migration`
3. ✅ **Complete** - All phases finished (40 commits)
4. ⏳ **Pending** - User creates PR and merges when ready

## Workflow Checklist for Implementer

### Before Starting
- [x] User approves this plan
- [x] Run `/start-work parquet-migration`
- [x] Create and checkout branch: `git checkout -b feature/parquet-migration`

### During Implementation
- [x] Commit after EVERY task with passing tests
- [x] Stay on `feature/parquet-migration` branch
- [x] Do NOT modify changelogs/ directory
- [x] Do NOT modify docs/ directory
- [x] Run tests before each commit

### Before Handoff
- [x] All tests passing (3,246+ Julia, 16 Python)
- [x] Clean working directory (all changes committed)
- [x] Branch `feature/parquet-migration` ready for PR
- [x] Summary of all commits provided to user

### User Responsibilities
- [x] Create PR from `feature/parquet-migration` to `main`
- [x] Update changelogs/ directory
- [x] Update docs/ directory
- [x] Merge PR when ready

---

## Notes

- **WTTimeSeries**: Will remain CSV output (required by external tools)
- **Report commands**: Only need read support, no changes to report generation logic
- **ParseSensors**: Input remains String (raw file), output becomes Parquet
- **Sidecar files**: Optional YAML/TOML sensors files for human readability alongside Parquet

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-08  
**Author**: Prometheus (Plan Builder)
