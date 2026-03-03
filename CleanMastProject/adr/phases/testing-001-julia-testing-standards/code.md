# Phase: code - Julia Test Patterns

## When to Use

Load this file when:
- Writing test files
- Creating fixture utilities
- Implementing unit tests
- Adding tests to runtests.jl
- Designing test data generators

## Related ADR

- [ADR-testing-001: Julia Testing Standards](../testing-001-julia-testing-standards.md)
- [ADR-types-001: Julia Type System](../types-001-julia-type-system.md) - Type signatures in tests

## Implementation Patterns

### Basic Test File Structure

```julia
# test/{Module}/test_{feature}.jl

using Test
using CleanMastProject.{Module}
using CleanMastProject.Types.{Config}

# Include fixtures if needed
include(joinpath(@__DIR__, "fixtures", "fixtures.jl"))

@testset "{Feature} Tests" begin
    
    @testset "Basic functionality" begin
        # Arrange
        input = [1, 2, 3]
        
        # Act
        result = process_data(input)
        
        # Assert
        @test length(result) == 3
        @test result[1] == expected_value
    end
    
    @testset "Edge cases" begin
        @test_throws DomainError process_data([])
    end
    
    @testset "Complex scenario with fixtures" begin
        fixture = load_fixture("scenario_name")
        result = process_data(fixture.input, fixture.config)
        @test result == fixture.expected_output
    end
    
end
```

### Test Runner Structure

```julia
# test/runtests.jl

using Test
using Pkg

# Get absolute path of test directory
test_dir = @__DIR__
project_dir = joinpath(test_dir, "..")

# Activate project environment
Pkg.activate(project_dir)

# Define test sets
const TEST_SETS = Dict{String, Vector{String}}(
    "module_name" => [
        "ModuleName/test_feature.jl",
        "ModuleName/test_another_feature.jl"
    ]
)

# Helper function to list available test sets
function print_available_test_sets()
    println("Available test sets:")
    for (name, files) in sort(collect(TEST_SETS))
        println("  $name:")
        for file in files
            println("    - $file")
        end
    end
end

# Parse command line arguments
function parse_args()
    if isempty(ARGS)
        return collect(keys(TEST_SETS))
    elseif ARGS[1] in ["--help", "-h"]
        println("Usage: julia runtests.jl [test_set1 test_set2 ...]")
        println()
        print_available_test_sets()
        exit(0)
    else
        invalid_sets = setdiff(ARGS, keys(TEST_SETS))
        if !isempty(invalid_sets)
            println("Error: Invalid test sets: ", join(invalid_sets, ", "))
            println()
            print_available_test_sets()
            exit(1)
        end
        return ARGS
    end
end

# Run selected test sets
function run_test_sets(selected_sets)
    for test_set in selected_sets
        files = TEST_SETS[test_set]
        @testset "$test_set" begin
            for file in files
                include(file)
            end
        end
    end
end

# Main execution
selected_sets = parse_args()
run_test_sets(selected_sets)
```

### Fixture Loading Utilities

```julia
# test/{Module}/fixtures/fixtures.jl

using DataFrames, CSV, Dates, TOML

"""
    load_fixture(path::String) -> NamedTuple

Load test fixture from the given path relative to fixtures directory.

# Arguments
- `path`: Path like "simple_rename" or "sensor_merge/zero_overlap"

# Returns
Named tuple with:
- `input`: Input DataFrame or nothing
- `expected_output`: Expected DataFrame or nothing
- `expected_sensors`: Expected sensor metadata or nothing
- `config`: Config dictionary or nothing
"""
function load_fixture(path::String)
    fixture_dir = joinpath(@__DIR__, path)

    if !isdir(fixture_dir)
        error("Fixture directory not found: $fixture_dir")
    end

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

    # Load expected sensors metadata
    expected_sensors = if isfile(joinpath(fixture_dir, "expected_sensors.toml"))
        TOML.parsefile(joinpath(fixture_dir, "expected_sensors.toml"))
    else
        nothing
    end

    # Load config
    config = if isfile(joinpath(fixture_dir, "config.toml"))
        TOML.parsefile(joinpath(fixture_dir, "config.toml"))
    else
        nothing
    end

    return (
        input = input_df,
        expected_output = expected_output,
        expected_sensors = expected_sensors,
        config = config
    )
end

"""
    create_test_dataframe(nrows::Int; with_duplicates::Bool=false) -> DataFrame

Create a simple test DataFrame for unit tests.
"""
function create_test_dataframe(nrows::Int; with_duplicates::Bool=false)
    timestamps = [DateTime(2024, 1, 1) + Minute(10 * (i-1)) for i in 1:nrows]

    if with_duplicates
        df = DataFrame(timestamp = timestamps)
        df[!, Symbol("Ch2_Anem_120.00m_SE_Avg_m/s")] = rand(nrows) .* 10
        df[!, Symbol("Ch7_Anem_120.00m_SE_Avg_m/s")] = rand(nrows) .* 10
        return df
    else
        df = DataFrame(timestamp = timestamps)
        df[!, Symbol("Ch1_Anem_80.00m_NW_Avg_m/s")] = rand(nrows) .* 10
        df[!, Symbol("Ch2_Vane_80.00m_NW_Avg_Deg")] = rand(nrows) .* 360
        return df
    end
end
```

### Generator Fixture Pattern

```julia
# test/{Module}/fixtures/{scenario}/generator.jl

using DataFrames, Dates

function generate_input_data()
    nrows = 100
    timestamps = [DateTime(2024, 1, 1) + Minute(10 * (i-1)) for i in 1:nrows]
    
    df = DataFrame(timestamp = timestamps)
    df[!, :wind_speed] = 5 .+ 3 .* rand(nrows)  # Random wind speeds 5-8 m/s
    df[!, :wind_direction] = 360 .* rand(nrows)  # Random directions 0-360
    
    return df
end

function generate_expected_output()
    input = generate_input_data()
    # Apply expected transformation
    output = copy(input)
    output[!, :wind_speed] = output[!, :wind_speed] .* 2  # Example transformation
    return output
end
```

## Examples

### Unit Test with Inline Data

```julia
# test/Types/test_process_clean_config.jl

using Test
using CleanMastProject.Types.ProcessCleanConfig

@testset "ProcessCleanConfig Tests" begin
    
    @testset "Range validation" begin
        config = RangeConfig(min=0.0, max=50.0)
        
        @test is_valid(config, 25.0) == true
        @test is_valid(config, -1.0) == false
        @test is_valid(config, 51.0) == false
    end
    
    @testset "Edge case handling" begin
        config = RangeConfig(min=0.0, max=50.0)
        
        # Boundary values
        @test is_valid(config, 0.0) == true
        @test is_valid(config, 50.0) == true
        
        # Missing data
        @test is_valid(config, missing) == false
    end
    
end
```

### Unit Test with Fixtures

```julia
# test/ParseSensors/test_column_parser.jl

using Test
using CleanMastProject.ParseSensors.ColumnParser

include(joinpath(@__DIR__, "fixtures", "fixtures.jl"))

@testset "ColumnParser Tests" begin
    
    @testset "Placeholder extraction" begin
        format = "Ch{channel}_{sensorType}_{height}m_{sensorDirection}"
        placeholders = extract_format_placeholders(format)
        @test placeholders == ["channel", "sensorType", "height", "sensorDirection"]
    end
    
    @testset "Complex parsing with fixtures" begin
        fixture = load_fixture("simple_rename")
        result = parse_column_names(fixture.input, fixture.config)
        
        @test result == fixture.expected_output
    end
    
    @testset "Generator-based fixture" begin
        fixture = load_fixture("sensor_merge/zero_overlap")
        result = merge_sensors(fixture.input, fixture.config)
        
        @test nrow(result) == nrow(fixture.expected_output)
    end
    
end
```

### Data Transformation Test

```julia
# test/DataClean/test_range_rules.jl

using Test
using CleanMastProject.DataClean.RangeRules
using DataFrames

@testset "Range Rules Tests" begin
    
    @testset "Apply range filter" begin
        # Create test data inline
        df = DataFrame(
            timestamp = [DateTime(2024, 1, 1), DateTime(2024, 1, 2)],
            wind_speed = [10.0, 100.0]  # 100 is out of range
        )
        
        rule = RangeRule(column=:wind_speed, min=0.0, max=50.0)
        result = apply_rule(df, rule)
        
        @test result[1, :wind_speed] == 10.0
        @test ismissing(result[2, :wind_speed])
    end
    
    @testset "Multiple rules" begin
        df = DataFrame(
            wind_speed = [10.0, 60.0, -5.0],
            wind_direction = [180.0, 400.0, 90.0]
        )
        
        rules = [
            RangeRule(column=:wind_speed, min=0.0, max=50.0),
            RangeRule(column=:wind_direction, min=0.0, max=360.0)
        ]
        
        result = apply_rules(df, rules)
        
        # Row 1: all valid
        @test result[1, :wind_speed] == 10.0
        @test result[1, :wind_direction] == 180.0
        
        # Row 2: wind_speed invalid, direction invalid
        @test ismissing(result[2, :wind_speed])
        @test ismissing(result[2, :wind_direction])
        
        # Row 3: wind_speed invalid
        @test ismissing(result[3, :wind_speed])
        @test result[3, :wind_direction] == 90.0
    end
    
end
```

### Configuration Loading Test

```julia
# test/Types/test_process_clean_config.jl

using Test
using CleanMastProject.Types.ProcessCleanConfig
using TOML

@testset "ProcessCleanConfig Loading Tests" begin
    
    @testset "Load from TOML" begin
        toml_str = """
        [range_rules]
        wind_speed = { min = 0.0, max = 50.0 }
        wind_direction = { min = 0.0, max = 360.0 }
        """
        
        config_dict = TOML.parse(toml_str)
        config = ProcessCleanConfig(config_dict)
        
        @test length(config.range_rules) == 2
        @test config.range_rules[:wind_speed].min == 0.0
        @test config.range_rules[:wind_speed].max == 50.0
    end
    
    @testset "Invalid config throws" begin
        toml_str = """
        [range_rules]
        wind_speed = { min = "invalid", max = 50.0 }
        """
        
        config_dict = TOML.parse(toml_str)
        @test_throws ArgumentError ProcessCleanConfig(config_dict)
    end
    
end
```

## Test Naming Conventions

| What | Convention | Example |
|------|------------|---------|
| Test file | `test_{feature}.jl` | `test_column_parser.jl` |
| Test set | Descriptive string | `@testset "Column parsing"` |
| Nested test set | Specific scenario | `@testset "With regex patterns"` |
| Fixture directory | `{scenario_name}` | `fixtures/sensor_merge/` |
| Fixture loader | `load_fixture()` | Standard fixture loading function |
| Data generator | `create_test_{data}()` | `create_test_dataframe()` |

## Running Tests

```bash
# Run all tests
julia CleanMastProject/test/runtests.jl

# Run specific test sets
julia CleanMastProject/test/runtests.jl parse_sensors data-clean

# List available test sets
julia CleanMastProject/test/runtests.jl --help

# Run with detailed output
julia CleanMastProject/test/runtests.jl --verbose

# Run tests for a specific module only
julia CleanMastProject/test/runtests.jl single_mast
```
