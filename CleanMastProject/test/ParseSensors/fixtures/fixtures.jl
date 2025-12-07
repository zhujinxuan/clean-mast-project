# test/ParseSensors/fixtures/fixtures.jl
"""
Fixture loading utilities for ParseSensors tests.
"""

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

# Example
```julia
fixture = load_fixture("simple_rename")
@test transform_columns!(fixture.input, sensors) == fixture.expected_output
```
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

# Arguments
- `nrows`: Number of rows to generate
- `with_duplicates`: If true, creates Ch2 and Ch7 columns mapping to same target

# Returns
DataFrame with timestamp and sensor columns
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
