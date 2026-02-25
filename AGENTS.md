<!-- NOTE: CLAUDE.md and AGENTS.md must be kept in sync! -->

# CleanMast Project Guide for Claude Code

CleanMast is a comprehensive Julia toolkit for processing wind energy meteorological tower data. This guide provides Claude Code agents with essential context, coding standards, and domain expertise for working effectively with this codebase.

## Project Overview

CleanMast processes wind measurement data through a multi-stage pipeline:
- **Data Parsing**: Flexible sensor data parsing with configurable column mappings
- **Data Cleaning**: Range validation, layer difference checks, icing detection, tower shading
- **Data Reconstruction**: Single-mast correlation, mesoscale data integration, representative year calibration
- **Analysis & Reporting**: Wind resource assessment, EN standard compliance, quality reports

### Key Technologies
- **CLI Framework**: Comonicon.jl for modular command structure
- **Data Processing**: DataFrames.jl, DataFramesMeta.jl, CSV.jl
- **Configuration**: TOML-based configuration system
- **Visualization**: AlgebraOfGraphics.jl (preferred), CairoMakie.jl
- **Statistical Modeling**: GLM.jl, Distributions.jl, StatsBase.jl

## Architecture Overview

```
CleanMastProject/
├── src/
│   ├── Types/                     # Core type definitions and configurations
│   ├── ParseSensors/             # Data parsing and column mapping
│   ├── DataClean/                # Data cleaning rules and validation
│   ├── ReconstructSingleMast/    # Single-mast data reconstruction
│   ├── ReconstructMeso/          # Mesoscale data reconstruction
│   ├── ReconstructCross/         # Cross-mast reconstruction (in development)
│   ├── AnalyzeTimeSeries/        # Wind resource analysis
│   ├── AnalyzeEN/                # EN standard compliance analysis
│   ├── RepresentativeYear/       # Long-term calibration
│   ├── TowerShading/             # Tower shadow detection/correction
│   ├── Command/                  # CLI command implementations
│   └── CleanMastUtils.jl        # Shared utilities
├── test/                         # Test suite
├── docs/                         # Documentation
└── Project.toml                  # Package dependencies
```

## Workspace Structure

The project uses Julia's workspace feature for better organization:

**Root Structure:**
```
clean-mast-project/
├── Project.toml           # Workspace configuration: [workspace] members = ["CleanMastProject"]
├── bin/
│   └── CleanMast.jl      # Entry point that activates CleanMastProject environment
└── CleanMastProject/     # The actual Julia package
    ├── Project.toml       # Package dependencies and metadata
    ├── src/               # Source code
    ├── test/              # Test suite
    └── docs/              # Documentation
```

**Key Points:**
- The root `Project.toml` defines the workspace with `CleanMastProject` as a member
- All source code, tests, and documentation live under `CleanMastProject/`
- `bin/CleanMast.jl` activates the `CleanMastProject` environment before loading the package
- When running tests, use: `julia CleanMastProject/test/runtests.jl [test_set]`
- All file paths in code should be relative to the package root (`CleanMastProject/`)

## Coding Standards

### File Path Convention (CRITICAL)

**Claude Code File Modification Bug Workaround**: Always use complete absolute Windows paths with drive letters and backslashes for ALL file operations. This applies to Read, Write, Edit, and any other file tools.

**Correct format**: `C:\Users\zhu_j\workspace\developing\clean-mast-project\file.txt`
**Incorrect formats**:
- Relative paths: `projects/file.txt`
- Forward slashes: `C:/Users/...`
- Mixed separators

Apply this rule consistently throughout the session, not just when encountering errors.

**IMPORTANT: Shell Commands with Paths**
When using paths in Bash/shell commands with double quotes, you MUST:
- Use forward slashes `/` OR
- Escape backslashes with `\\`

**Examples:**
```bash
# CORRECT - Forward slashes
ls -la "/c/Users/zhu_j/workspace/test"
ls -la "C:/Users/zhu_j/workspace/test"

# CORRECT - Escaped backslashes
ls -la "C:\\Users\\zhu_j\\workspace\\test"

# WRONG - Single backslashes in quotes
ls -la "C:\Users\zhu_j\workspace\test"  # ERROR: \U, \w, \t are escape sequences
```

**Rule of thumb:**
- **File tool parameters** (Read, Write, Edit): Use Windows backslashes `C:\path\to\file`
- **Shell command strings**: Use forward slashes `"C:/path/to/file"` or escaped backslashes `"C:\\path\\to\\file"`

### Formatting Rules
- **Julia Code**: 4 whitespaces for indentation, max 92 characters per line
- **Markdown**: 2 whitespaces for indentation, max 80 characters per line
- **Commit Messages**: Format `component: brief summary`, max 72 characters

### Function Design & Type Safety
Use restrictive type signatures for better error detection and maintainability:

```julia
# Good - specific types enable better error catching
function process_wind_data(data::DataFrame, config::ProcessCleanConfig)::DataFrame
    validate_data_format(data)
    return apply_processing_rules(data, config)
end

# Use explicit semicolon for keyword arguments
Position(; line=1, character=0)
```

### Data Processing Best Practices

#### Symbol vs String Handling (Critical!)
Julia DataFrames require `Symbol` for column operations:

```julia
# Correct - using Symbols
select(df, :wind_speed, :wind_direction)
df[:, :timestamp]

# Incorrect - using Strings (causes errors)
select(df, "wind_speed", "wind_direction")  # Error!

# Converting dynamic column names
col_name = "wind_speed_80m"
df[:, Symbol(col_name)]  # Convert string to symbol
```

#### Preferred Transformation Patterns
```julia
# Method chaining with pipe operator
cleaned_data = raw_data |>
    df -> filter(row -> !ismissing(row.wind_speed), df) |>
    df -> select(df, :timestamp, :wind_speed, :wind_direction)

# Broadcasting for vectorized operations
wind_power = wind_speed_data .|> speed -> 0.5 * 1.225 * speed^3

# Data subsetting with standard indexing
subset_data = full_data[1:1000, :]
```

#### Functional Programming Style (Critical!)
**AVOID** imperative loops with `push!` - use functional patterns instead:

```julia
# BAD - imperative style with for loop and push!
results = DataFrame()
for row in eachrow(data)
    if row.wind_speed > threshold
        push!(results, row)
    end
end

# GOOD - functional style with filter
results = filter(row -> row.wind_speed > threshold, data)

# BAD - building vectors with push!
wind_speeds = Float64[]
for sensor in sensors
    if sensor.sensorType == "WindSpeed"
        push!(wind_speeds, sensor.height)
    end
end

# GOOD - functional style with map/filter
wind_speeds = sensors |>
    sensors -> filter(s -> s.sensorType == "WindSpeed", sensors) |>
    sensors -> map(s -> s.height, sensors)

# GOOD - even more concise with broadcasting
wind_speeds = [s.height for s in sensors if s.sensorType == "WindSpeed"]

# For combining data - use DataFrame joins instead of loops
combined_data = leftjoin(mast_data, meso_data; on = :timestamp)

# Use zip for parallel iteration
height_speed_pairs = collect(zip(heights, speeds))
processed_pairs = map(((h, s),) -> process_measurement(h, s), height_speed_pairs)
```

#### Missing Data Strategy
- Always use `ismissing()` for missing value checks
- Allow missing values to propagate naturally through transformations
- Use `skipmissing()` for statistical operations
- Handle missing explicitly in filter conditions

### Domain-Specific Guidelines

#### Wind Energy Data Context
Based on the `SensorColumn` definition (see `CleanMastProject/src/Types/SensorColumns.jl`), the system supports multiple sensor types, but **primary focus is on WindSpeed and WindDirection** for wind energy analysis:
- **Primary Sensor Types**: WindSpeed, WindDirection (most analysis focuses on these)
- **Secondary Sensor Types**: Temperature, Pressure
- **Critical StatType**: `avg` (average) - this is the primary statistic used for wind analysis
- **Data Intervals**: 10-minute averages for mast data, 1-hour for mesoscale data (for input)
- **Height Levels**: Variable (common: 10m, 40m, 60m, 80m, 100m, but flexible)
- **Physical Constraints**: Wind speed 0-50 m/s, direction 0-360°, realistic ranges per sensor type
- **Sensor Directions**: May include directional info or "N/A" for omnidirectional sensors

#### Time Series Processing
- **Timestamps**: Always validate and regularize intervals (10min for mast, 1hr for meso)
- **Gaps**: Distinguish between missing data and sensor failures
- **Seasonal Patterns**: Account for diurnal and seasonal patterns
- **Quality Flags**: Preserve data provenance through processing stages

#### Configuration System
- All processing steps use TOML configuration files
- Use `recommend` commands to generate initial configurations
- Validate configurations using type system (see `Types/*Config.jl`)
- Support both relative and absolute file paths

### Testing Conventions

For comprehensive testing documentation, see **[CleanMastProject/docs/development/tests.md](CleanMastProject/docs/development/tests.md)**.

**Quick Reference:**
- **Run tests**: `julia CleanMastProject/test/runtests.jl [test_set]`
- **List test sets**: `julia CleanMastProject/test/runtests.jl --help`
- **Fixtures**: Use `CleanMastProject/test/{Module}/fixtures/` for complex scenarios
- **Inline data**: Use for simple unit tests and temp file tests

Always run relevant tests after code changes: `julia CleanMastProject/test/runtests.jl [module_name]`

### Python Type Checking

**Run type check:** `uv run ty check packages/cleanmast`
**Check specific module:** `uv run ty check packages/cleanmast/src/cleanmast/fill_heights`

Type errors should be fixed before committing. The project uses Pyright for type checking.

### Polars Best Practices (Python)

Polars is built on a lazy, expression-based engine. The key insight is to **build expressions first, then apply them**. This enables query optimization, parallel execution, and memory efficiency.

#### Core Principle: Build Expressions, Not Series

```python
# ❌ Wrong: Eagerly materialize intermediate Series
speed = df["wind_speed"]
direction = df["wind_direction"]
result = speed * pl.cos(direction * pl.pi / 180)
df = df.with_columns(result.alias("u_component"))

# ✅ Right: Build an expression, then apply it in one shot
u_expr = pl.col("wind_speed") * pl.cos(pl.col("wind_direction") * pl.pi / 180)
df = df.with_columns(u_expr.alias("u_component"))
```

#### 1. Expressions Over Loops (The Polars Way)

**Mindset shift**: Think in expressions, not iterations.

```python
# ❌ Wrong: Loop-based accumulation
weighted_sum = pl.lit(0.0)
for ref in references:
    weighted_sum = weighted_sum + pl.col(ref.source_column) * ref.weight
df = df.with_columns(weighted_sum.alias("result"))

# ✅ Right: Build expression with sum()
expr = sum(
    pl.col(ref.source_column) * ref.weight
    for ref in references
)
df = df.with_columns(expr.alias("result"))
```

#### 2. Composable Expression Building

Build complex logic by composing smaller expressions:

```python
# Build reusable expression components
speed_col = pl.col("wind_speed")
dir_col = pl.col("wind_direction")

# Convert to radians
rad_expr = dir_col * pl.pi / 180

# Calculate wind components
u_expr = speed_col * rad_expr.cos()
v_expr = speed_col * rad_expr.sin()

# Apply all at once
df = df.with_columns([
    u_expr.alias("u_component"),
    v_expr.alias("v_component"),
])
```

#### 3. Conditional Expressions with `when().then().otherwise()`

```python
# ❌ Wrong: Row-wise Python logic
for row in df.iter_rows():
    if row["wind_speed"] < 3:
        category = "calm"
    elif row["wind_speed"] < 10:
        category = "moderate"
    else:
        category = "strong"

# ✅ Right: Expression-based conditional
category_expr = (
    pl.when(pl.col("wind_speed") < 3).then(pl.lit("calm"))
    .when(pl.col("wind_speed") < 10).then(pl.lit("moderate"))
    .otherwise(pl.lit("strong"))
)
df = df.with_columns(category_expr.alias("wind_category"))
```

#### 4. Window Functions with `over()`

```python
# Calculate deviation from daily mean
daily_mean_expr = pl.col("wind_speed").mean().over(pl.col("date"))
deviation_expr = pl.col("wind_speed") - daily_mean_expr

df = df.with_columns([
    daily_mean_expr.alias("daily_mean_speed"),
    deviation_expr.alias("speed_deviation"),
])
```

#### 5. Aggregation Expressions with `agg()`

```python
# Complex aggregations in group_by
result = df.group_by("month").agg([
    pl.col("wind_speed").mean().alias("avg_speed"),
    pl.col("wind_speed").std().alias("std_speed"),
    (pl.col("wind_speed") ** 3).mean().alias("mean_cubed_speed"),
    pl.col("wind_direction").mode().first().alias("dominant_direction"),
])
```

#### 6. Use `pl.col()` for Dynamic Column References

```python
# When column names are dynamic
columns = ["wind_speed_10m", "wind_speed_50m", "wind_speed_100m"]

# Build expression for average across heights
avg_expr = sum(pl.col(c) for c in columns) / len(columns)
df = df.with_columns(avg_expr.alias("avg_speed_all_heights"))
```

#### 7. Chain Operations Method-Style

```python
# ✅ Fluent API for complex pipelines
clean_data = (
    raw_df
    .filter(pl.col("wind_speed").is_between(0, 50))
    .filter(pl.col("wind_direction").is_between(0, 360))
    .with_columns([
        (pl.col("wind_speed") ** 3).alias("wind_power"),
        pl.col("timestamp").dt.hour().alias("hour"),
    ])
    .select([
        "timestamp",
        "hour",
        "wind_speed",
        "wind_direction",
        "wind_power",
    ])
)
```

#### 8. Avoid `.to_numpy()` Unless Necessary

```python
# ❌ Wrong: Converting back and forth
result = some_numpy_operation(df["col"].to_numpy())
return pl.Series(result)

# ✅ Right: Stay in Polars expression land
result = df.with_columns(
    (pl.col("a") + pl.col("b")).alias("sum")
)["sum"]
```

#### 9. Handle Empty Cases with `pl.lit()`

```python
# ✅ Provide default for empty aggregations
expr = sum(
    [pl.col(ref.source_column) * ref.weight for ref in references],
    pl.lit(0.0)  # Ensures return type is always an expression
)
```

#### Summary: The Expression-First Checklist

- [ ] Did I build expressions before calling `with_columns()` or `filter()`?
- [ ] Did I use `pl.col()` instead of `df["col"]` in transformations?
- [ ] Did I avoid `iter_rows()` and Python loops?
- [ ] Did I compose complex logic from simple expressions?
- [ ] Did I apply all transformations in one `with_columns()` call when possible?
- [ ] Did I stay in Polars land without `.to_numpy()` conversions?

### Visualization Standards

#### AlgebraOfGraphics (Preferred)
```julia
# Grammar of graphics approach for wind data
wind_data |>
    mapping(:timestamp, :wind_speed; color=:height) *
    visual(Lines) |>
    draw
```

#### Plot Requirements
- Include clear titles, axis labels, and legends
- Use colorblind-friendly schemes (ColorSchemes.jl)
- For wind roses: use polar coordinates appropriately
- For time series: handle gaps and missing data gracefully

### CLI Command Development

#### Command Structure
- Use Comonicon.jl decorators: `@cast`, `@main`
- Group related commands: `process`, `analyze`, `recommend`, `report`
- Support both interactive and batch processing modes
- Provide meaningful help text and examples

#### Error Handling
- Validate input files and configurations early
- Provide clear error messages with suggested fixes
- Log processing steps for debugging
- Use `@assert` for internal consistency checks during development

### Performance Considerations

- **Vectorization**: Leverage Julia's broadcasting with dot syntax
- **Parallel Processing**: Consider `ThreadsX.jl` for CPU-intensive operations
- **External Libraries**: Use `@context7` when unsure about external library interfaces

### Environment Management

- **Project.toml**: NEVER modify dependency versions without explicit user approval
- **Working Directory**: Always `cd` to project root before running commands
- **Dependencies**: Check existing imports before suggesting new packages

### AI Agent Guidelines

#### Code Generation Priorities
1. **Domain Accuracy**: Understand meteorological constraints and wind energy physics
2. **Error Prevention**: Validate inputs and handle edge cases explicitly
3. **Performance**: Consider data size and processing efficiency
4. **Maintainability**: Follow established patterns and conventions

#### Testing Requirements
- Always run relevant tests after code changes: `julia test/runtests.jl [test_sets]`
- Prefer existing test patterns over creating new test structure
- Include both positive and negative test cases

#### User Interaction
- Respect user modifications to generated code
- Never reintroduce deleted functions without explicit request
- Ask for clarification when user changes seem problematic
- Preserve user's configuration choices and workflow patterns

#### Comments Policy
- **Minimal Comments**: Only include comments where truly necessary
- **Self-Documenting Code**: Prefer clear function/variable names
- **Docstrings**: Use for public API functions, avoid for obvious implementations
- **Domain Context**: Comment on meteorological assumptions or physical constraints

### Documentation Standards

#### Documentation Writing Principles
- **Source-Code Constrained**: Only document what can be verified from actual code files
- **No Hallucination**: Never invent configuration parameters, examples, or explanations not found in source code
- **Reference-First**: Base all documentation on:
  - Julia struct definitions in `CleanMastProject/src/Types/`
  - Actual configuration files in `projects/pn-masts/`
  - Code comments and docstrings
  - Do NOT use general domain knowledge to fill gaps

#### Fact-Checking Process
Before writing any documentation content:
1. **Verify in Types**: Check if parameters exist in the actual Julia struct definitions
2. **Confirm in Examples**: Ensure examples match real configuration files in reference projects
3. **Source Comments**: Only explain functionality that's documented in code comments
4. **When Uncertain**: Omit details rather than guess, or refer users to source files directly

#### Documentation Structure for Config Files
- **概述 (Overview)**: Brief description of the config file's purpose
- **基本结构 (Basic Structure)**: Simple TOML template showing required sections
- **配置参数 (Configuration Parameters)**: Only documented struct fields
- **完整配置示例 (Complete Example)**: Based on actual reference implementation
- **配置生成 (Configuration Generation)**: Appropriate `recommend` command

#### What NOT to Include
- Detailed algorithm explanations unless in source comments or under `docs/algorithms/`
- Parameter effects or processing logic details
- "Best practices" or troubleshooting sections
- Domain-specific advice beyond what's in the code
- Comprehensive parameter lists not found in actual structs

#### Language and Style for docs/*
- **Chinese Language**: All documentation under `docs/` uses Chinese
- **Concise Format**: Keep documentation brief and focused
- **User-Friendly**: Avoid overly technical explanations
- **Practical Examples**: Show real configuration patterns from reference projects

#### Error Prevention
- **Conservative Approach**: Prefer minimal accurate documentation over comprehensive but potentially wrong details
- **Explicit Constraints**: When documenting, state "refer to [specific file] for details" rather than elaborating
- **Verification**: Always cross-reference with actual code before documenting features

### Report Atom Pattern

When working with report generation code:

**Architecture:**
- `ReportAtom` is an abstract base class (ABC)
- Each atom implements 3 methods: `renderTable()`, `renderImage()`, `renderSummary()`
- DataFrame + Schema + Meta = Atom instance
- Use `Atom.create(schema, df, meta)` factory method

**Data Format:**
- Tables use **pivoted format**: Months/Sectors as rows, Heights as columns
- Charts use **Altair** with `.to_pandas()` conversion (required!)
- Wind roses use `mark_arc()` (not `mark_line`)
- All text in **Chinese** (月份, 外推, 风速, etc.)

**Table Column Order:**
```
[月份/风向], [10m], [50m], ..., [125m 外推], [140m 外推], [160m 外推]
```

**Typst Syntax:**
- Cells separated by **commas**: `[1], [value], [value]`
- Rows end with **trailing comma**: `[1], [value], [value],`
- Use `get_height_display_name()` for height formatting

**Testing:**
- Mock DataFrames in tests
- Test render methods return correct Typst syntax
- Skip actual compilation in unit tests (`compile_pdf=False`)

**Example Atom Structure:**
```python
@dataclass
class SingleMastMonthlyWindAtom(ReportAtom[MonthlyWindSchema, SingleMastMeta]):
    @override
    def renderTable(self) -> str:
        # Return Typst table markup

    @override
    def renderImage(self, output_dir: Path, force: bool = False) -> Path:
        # Generate PNG via Altair

    @override
    def renderSummary(self) -> str:
        # Return Chinese text summary
```

### Common Patterns

#### Configuration Loading
```julia
function load_config(config_path::String)::ConfigType
    config_dict = TOML.parsefile(config_path)
    return ConfigType(; config_dict...)
end
```

#### Data Processing Pipeline
```julia
function process_stage(input_data::DataFrame, config::StageConfig)::DataFrame
    # Validate inputs
    validate_data_format(input_data)

    # Apply transformations
    result = input_data |>
        df -> apply_quality_filters(df, config) |>
        df -> apply_corrections(df, config)

    # Validate outputs
    validate_processing_results(result)
    return result
end
```

#### Sensor Column Handling
```julia
# Working with SensorColumn types (defined in CleanMastProject/src/Types/SensorColumns.jl)
# Focus on WindSpeed/WindDirection with avg statType
function find_wind_speed_sensor(sensors::Vector{SensorColumn}, height::Float64)::Union{SensorColumn, Nothing}
    return find_nearest_height_sensor(height, sensors, "WindSpeed", "avg")
end

function find_wind_direction_sensor(sensors::Vector{SensorColumn}, height::Float64)::Union{SensorColumn, Nothing}
    return find_nearest_height_sensor(height, sensors, "WindDirection", "avg")
end

# Filter sensors functionally - AVOID for loops with push!
wind_sensors = filter(s -> s.sensorType ∈ ["WindSpeed", "WindDirection"] && s.statType == "avg", sensors)

# Create standardized sensor names
sensor_name = create_sensor_short_name(sensor)  # e.g., "WS:80m" or "WD:100m:N"
```

#### Sensor Column Detection Rule (CRITICAL - DO NOT VIOLATE)

**NEVER scan column names to detect sensor types. Always use SensorColumn from load_timeseries().**

**❌ FORBIDDEN: Pattern matching on column names**
```python
# NEVER DO THIS - Fragile and error-prone
def detect_wind_speed_columns(columns: list[str]) -> list[str]:
    wind_speed_cols = []
    for col in columns:
        if re.match(r"WS_\d+m|WindSpeed_\d+m", col):  # ❌ WRONG!
            wind_speed_cols.append(col)
    return wind_speed_cols

# DON'T DO THIS EITHER
ws_cols = [c for c in df.columns if c.startswith("WS_")]  # ❌ WRONG!

# DON'T DO THIS
import polars as pl
df = pl.read_parquet(path)  # ❌ Loses sensor metadata!
```

**Why this is forbidden:**
- Column naming conventions vary across projects and processing stages
- Raw data uses `WindSpeed_100m_NE_avg [m/s]` format
- Processed data uses `WS_125m_fill:extrapolated` format
- Column names change during preprocessing (merging, normalization)
- Pattern matching misses sensors or includes wrong columns
- **No access to sensor metadata** (sensor_type, stat_type, height, unit)
- Can't distinguish measured vs extrapolated vs interpolated data

**✅ CORRECT: Use load_timeseries() with sensor metadata**
```python
from cleanmast.io import load_timeseries
from cleanmast.models.timeseries import TimeSeriesSource

# Load data WITH sensor metadata from parquet
source = TimeSeriesSource(data="./clean/M6002.parquet")
timeseries = load_timeseries(source, str(project_dir))

# Access the DataFrame
df = timeseries.df

# Access sensors with full metadata
sensors = timeseries.sensors  # [SensorColumn, SensorColumn, ...]

# Filter for wind speed sensors using proper metadata
wind_speed_sensors = [
    s for s in sensors 
    if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
]

for sensor in wind_speed_sensors:
    height = sensor.height  # Official height from metadata
    col_name = sensor.column_name  # Column name in DataFrame
    data = df[col_name]  # ✅ CORRECT - Use sensor.column_name
```

**Key points:**
1. Always use `load_timeseries()` to load data - it preserves sensor metadata
2. Never use `pl.read_parquet()` directly - you lose sensor metadata
3. Filter sensors using `sensor.sensor_type`, `sensor.stat_type`, etc.
4. Access DataFrame columns via `sensor.column_name`
5. Sensor metadata includes: height, sensor_type, stat_type, unit, sensor_direction

**For report generation specifically:**
- The CLI command should use `load_timeseries()` to load mast data
- Access `timeseries.sensors` for sensor metadata
- Never auto-detect columns from parquet file column names
- If sensor metadata is missing, raise an error

**See also:**
- `packages/cleanmast/src/cleanmast/io/timeseries_io.py` - load_timeseries function
- `packages/cleanmast/src/cleanmast/models/timeseries.py` - TimeSeriesData class
- `packages/cleanmast/src/cleanmast/models/sensor.py` - SensorColumn model

#### Accessing DataFrames via SensorColumn (CRITICAL)
The `SensorColumn` type tracks the actual DataFrame column name after preprocessing. Always use this field to access DataFrame columns, not hardcoded strings or symbols:

- **Julia**: `columnName::Symbol` (camelCase)
- **Python**: `column_name::str` (snake_case)

**Julia DataFrames:**
```julia
# ✅ CORRECT: Access via sensor.columnName (Symbol)
wind_speed_data = df[:, wind_speed_sensor.columnName]

# ❌ WRONG: Hardcoded column name
data = df[:, :wind_speed_80m]  # Fragile!

# ✅ CORRECT: Using sensor metadata
function get_sensor_data(df::DataFrame, sensor::SensorColumn)
    return df[:, sensor.columnName]
end

# ✅ CORRECT: Column existence check
if hasproperty(df, sensor.columnName)
    data = df[:, sensor.columnName]
end
```

**Python Polars:**
```python
# ✅ CORRECT: Access via sensor.column_name (already a string)
wind_speed_col = wind_speed_sensor.column_name
expr = pl.col(wind_speed_col) * 2

# ✅ CORRECT: Using sensor in expressions
def get_sensor_expression(sensor: SensorColumn) -> pl.Expr:
    return pl.col(sensor.column_name)  # column_name is already str

# ✅ CORRECT: Building expressions from sensors
speed_expr = pl.col(wind_speed_sensor.column_name)
direction_expr = pl.col(wind_direction_sensor.column_name)
u_expr = speed_expr * (direction_expr * pl.pi / 180).cos()
```

**Why this matters:**
- Sensor columns may be renamed during preprocessing (e.g., merged files)
- `columnName` tracks the actual DataFrame column name after all transformations
- Hardcoded column names break when formats change or files are merged
- Using `sensor.columnName` ensures your code works across all pipeline stages

This guide ensures Claude Code agents can effectively contribute to CleanMast while maintaining code quality, domain accuracy, and user experience standards.