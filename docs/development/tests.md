# Testing Conventions

This document describes the testing structure, conventions, and best practices for the CleanMast project.

## Running Tests

### Basic Commands
```bash
# From project root
julia test/runtests.jl                    # Run all tests
julia test/runtests.jl parse_sensors      # Run specific test set
julia test/runtests.jl data-clean process # Run multiple test sets
julia test/runtests.jl --help             # List available test sets
```

### Available Test Sets

The test system uses organized test sets defined in `test/runtests.jl`:

| Test Set | Description |
|----------|-------------|
| `parse_sensors` | Data parsing and column mapping |
| `data-clean` | Data cleaning rules (range, icing, layer difference, availability) |
| `process` | Data processing operations |
| `time_series_processing` | Time series operations |
| `representative_year` | Long-term calibration |
| `tower` | Tower shading detection/correction |
| `logging` | Logging system tests |
| And more... | See `test/runtests.jl` for full list |

## Test File Organization

### Organization Pattern

Tests follow a consistent naming pattern:

**Pattern**: For source module `src/{ModuleName}`:
- Test set name: `{module-name}` (kebab-case)
- Test directory: `test/{ModuleName}/` (matching source structure)

**Examples**:
- `src/DataClean` → test set `data-clean` → directory `test/DataClean/`
- `src/ParseSensors` → test set `parse_sensors` → directory `test/ParseSensors/`
- `src/TimeSeriesProcessing` → test set `time_series_processing` → directory `test/TimeSeriesProcessing/`

### Directory Structure

```
test/
├── runtests.jl                  # Main test runner
├── ParseSensors/                # ParseSensors module tests
│   ├── fixtures/               # Test fixtures
│   ├── test_column_parser.jl
│   ├── test_dataframe_processor.jl
│   └── ...
├── DataClean/                   # DataClean module tests
│   ├── test_range_rules.jl
│   ├── test_icing_rules.jl
│   ├── test_layer_diff_rules.jl
│   └── test_availability_rules.jl
├── TimeSeriesProcessing/        # TimeSeriesProcessing tests
└── ...
```

## Test Fixtures

### When to Use Fixtures

**Use fixtures when:**
- ✅ Complex test scenarios with multiple test cases
- ✅ Golden test data representing real-world scenarios
- ✅ Reusable test data across multiple test sets
- ✅ Data that's too large to write inline
- ✅ Testing integration scenarios with realistic data

**Use inline/temp data when:**
- ✅ Simple unit tests with minimal data
- ✅ File I/O tests (should use `mktempdir()`)
- ✅ Integration tests building full environments
- ✅ One-off scenarios not reused elsewhere

### Fixture Directory Structure

```
test/{Module}/fixtures/
├── {scenario_name}/              # One directory per test scenario
│   ├── input.csv                 # Small data (hand-written CSV)
│   ├── generator.jl              # Large data (generated)
│   ├── expected_output.csv       # Golden test results
│   └── config.toml              # Test configuration (if needed)
└── fixtures.jl                   # Loader utility functions
```

### Fixture Naming Conventions

Use descriptive scenario names that indicate the test case:

**Good names:**
- `sensor_merge/zero_overlap` - Clear what scenario is being tested
- `multiplier_transform` - Describes the transformation
- `simple_rename` - Indicates basic functionality

**Bad names:**
- `test1`, `test2` - Non-descriptive
- `data` - Too generic

### Fixture File Types

**1. Small Hand-Written Data (`input.csv`, `expected_output.csv`)**
- Use for simple scenarios (< 20 rows)
- Easy to inspect and verify
- Version control friendly

**2. Generated Data (`generator.jl`)**
- Use for large datasets that can't be hand-written
- Must export `generate_input_data()` function
- Include comments describing the scenario

Example generator:
```julia
# Generates Ch2/Ch7 sensor replacement scenario with 0% overlap
using DataFrames, Dates

function generate_input_data()
    timestamps = [DateTime(2024,1,1) + Minute(10*i) for i in 1:200]

    # Ch2 data: first 100 rows
    ch2_data = vcat(rand(100) .* 5 .+ 3, fill(missing, 100))

    # Ch7 data: last 100 rows
    ch7_data = vcat(fill(missing, 100), rand(100) .* 5 .+ 3)

    df = DataFrame(timestamp = timestamps)
    df[!, Symbol("Ch2_Anem_120m_SE_Avg")] = ch2_data
    df[!, Symbol("Ch7_Anem_120m_SE_Avg")] = ch7_data
    return df
end
```

### Fixture Loader Utilities

Each fixtures directory should have a `fixtures.jl` with loader functions:

```julia
# test/{Module}/fixtures/fixtures.jl
using DataFrames, CSV, Dates, TOML

"""
Load test fixture from the given path.
Returns: (input, expected_output, config)
"""
function load_fixture(path::String)
    fixture_dir = joinpath(@__DIR__, path)

    # Load input (CSV or generator)
    input_df = if isfile(joinpath(fixture_dir, "input.csv"))
        CSV.read(joinpath(fixture_dir, "input.csv"), DataFrame)
    elseif isfile(joinpath(fixture_dir, "generator.jl"))
        include(joinpath(fixture_dir, "generator.jl"))
        generate_input_data()
    else
        nothing
    end

    # Load expected output
    expected_output = if isfile(joinpath(fixture_dir, "expected_output.csv"))
        CSV.read(joinpath(fixture_dir, "expected_output.csv"), DataFrame)
    else
        nothing
    end

    return (input=input_df, expected_output=expected_output, config=nothing)
end
```

### Using Fixtures in Tests

```julia
# test/{Module}/test_something.jl
using Test
include("fixtures/fixtures.jl")

@testset "My Test" begin
    # Load fixture
    fixture = load_fixture("sensor_merge/zero_overlap")

    # Run function under test
    result = my_function(fixture.input)

    # Assert against expected output
    @test result == fixture.expected_output
end
```

## Test Patterns

### Unit Tests (Inline Data)

For simple unit tests, use inline data:

```julia
@testset "calculate_overlap_percentage" begin
    df = DataFrame(
        col1 = [1.0, 2.0, missing, 4.0, missing],
        col2 = [missing, 2.0, 3.0, 4.0, missing]
    )

    overlap_pct = calculate_overlap_percentage(df, :col1, :col2)
    @test overlap_pct == 40.0  # 2 out of 5 rows
end
```

### Integration Tests (Temp Files)

For file I/O and integration tests, use `mktempdir()`:

```julia
@testset "File Processing" begin
    mktempdir() do temp_dir
        # Create test file
        test_file = joinpath(temp_dir, "test.csv")
        write(test_file, "header1,header2\nvalue1,value2\n")

        # Process file
        result = process_file(test_file)

        # Verify results
        @test result !== nothing
    end
end
```

### Golden Tests (Fixtures)

For tests comparing against known-good outputs:

```julia
@testset "Sensor Merge Golden Test" begin
    fixture = load_fixture("sensor_merge/zero_overlap")

    df_result, sensors_result = transform_columns!(fixture.input, sensors)

    # Compare against golden output
    @test names(df_result) == names(fixture.expected_output)
    @test nrow(df_result) == nrow(fixture.expected_output)
end
```

## Test Writing Guidelines

### Descriptive Test Names

Use descriptive `@testset` names:

```julia
# Good
@testset "merge_columns! - latter wins when both have data" begin
    ...
end

# Bad
@testset "Test 1" begin
    ...
end
```

### Test One Thing

Each test should verify one specific behavior:

```julia
# Good - focused test
@testset "Column should be renamed" begin
    @test "WindSpeed_80m" in names(result)
end

@testset "Original column should be removed" begin
    @test "Ch1_Anem_80m" ∉ names(result)
end

# Bad - testing multiple things
@testset "Rename works" begin
    @test "WindSpeed_80m" in names(result)
    @test "Ch1_Anem_80m" ∉ names(result)
    @test result[1, "WindSpeed_80m"] == 5.0
end
```

### Clear Assertions

Write clear, specific assertions with helpful messages:

```julia
# Good
@test length(merged.originalColumnNames) == 2

# Better - with message
@test length(merged.originalColumnNames) == 2 "Expected 2 original columns to be merged"
```

### Test Edge Cases

Always test edge cases:
- Empty data
- Missing values
- Boundary conditions
- Error conditions

```julia
@testset "Edge Cases" begin
    # Empty DataFrame
    @test transform_columns(DataFrame(), []) == DataFrame()

    # All missing data
    df_missing = DataFrame(col = [missing, missing])
    @test all(ismissing, process(df_missing).col)

    # Invalid input
    @test_throws ArgumentError transform_columns(df, invalid_sensors)
end
```

## Test Maintenance

### Keeping Tests Up-to-Date

- Run tests after every code change
- Update tests when refactoring
- Remove obsolete tests
- Keep fixtures synchronized with code

### Test Performance

- Keep unit tests fast (< 1 second)
- Use fixtures for expensive setups
- Consider `@testset` granularity for parallel execution

### Test Coverage

While we don't enforce strict coverage metrics, aim to test:
- All public API functions
- Critical internal logic
- Edge cases and error paths
- Integration points between modules

## Common Pitfalls

### DataFrame Column Names

Remember: `names(df)` returns **String**, not **Symbol**:

```julia
# Wrong
@test :column_name in names(df)

# Right
@test "column_name" in names(df)
```

### Symbol Construction in DataFrames

Can't use `Symbol()` directly in DataFrame constructors:

```julia
# Wrong
df = DataFrame(Symbol("col_name") = [1, 2, 3])

# Right
df = DataFrame()
df[!, Symbol("col_name")] = [1, 2, 3]
```

### Path Escaping in Shell Commands

When using paths in Bash commands with quotes:

```julia
# Wrong
run(`ls "C:\path\to\file"`)  # \p, \t, \f are escape sequences

# Right (forward slashes)
run(`ls "C:/path/to/file"`)

# Right (escaped backslashes)
run(`ls "C:\\path\\to\\file"`)
```

## Reference Implementation

See `test/ParseSensors/` for a complete example of:
- Fixture organization
- Loader utilities
- Unit tests
- Integration tests
- Golden tests

This module demonstrates best practices for test organization and implementation.
