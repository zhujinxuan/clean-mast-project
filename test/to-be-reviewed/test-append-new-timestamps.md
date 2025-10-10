# TODO: Tests for append_new_timestamps Helper Function

## Overview

Create tests for the `append_new_timestamps()` helper function in `src/ReconstructCross/ProcessReconstructCrossCommand.jl` to verify time range extension behavior in cross-mast reconstruction.

## Code Change Context

**Recent addition:** New helper function to extend target time range with timestamps from reconstructed data:

```julia
function append_new_timestamps(target_ts::TimeSeriesData, reconstructed_ts::TimeSeriesData)::DataFrame
    # Start with target data
    result_df = copy(target_ts.df)

    # Find timestamps in reconstructed that don't exist in target
    existing_timestamps = Set(target_ts.df.timestamp)
    reconstructed_timestamps = reconstructed_ts.df.timestamp
    new_timestamps = filter(t -> !(t in existing_timestamps), reconstructed_timestamps)

    if isempty(new_timestamps)
        return result_df  # No new timestamps to add
    end

    # Create rows for new timestamps with all sensor values as missing
    new_rows = DataFrame(:timestamp => new_timestamps)
    for sensor in target_ts.sensors
        new_rows[!, sensor.columnName] = missings(Float64, length(new_timestamps))
    end

    # Append new rows and sort by timestamp
    result_df = vcat(result_df, new_rows)
    sort!(result_df, :timestamp)

    return result_df
end
```

**Purpose:** Enable cross-mast reconstruction to extend measurement periods beyond the original target data range (fixing the inner join limitation).

## Test File Location

Create: `test/ReconstructCross/test_append_new_timestamps.jl`

Add to `test/runtests.jl`:
```julia
"reconstruct_cross" => [
    "ReconstructCross/test_append_new_timestamps.jl"
]
```

## Test Scenarios

### 1. Basic Functionality

#### No New Timestamps (Complete Overlap)
- [ ] Target: 2024-01-01 00:00 to 2024-01-31 23:00 (hourly)
- [ ] Reconstructed: 2024-01-01 00:00 to 2024-01-31 23:00 (hourly)
- [ ] Expected: Returns copy of target_df unchanged
- [ ] Verify: `nrow(result) == nrow(target_df)`
- [ ] Verify: All timestamps identical to target

#### New Timestamps at End (Time Extension)
- [ ] Target: 2024-01-01 to 2024-01-31 (1 month)
- [ ] Reconstructed: 2024-01-01 to 2024-03-31 (3 months)
- [ ] Expected: Target data + 2 months of new timestamps with missing values
- [ ] Verify: `nrow(result) == nrow(target) + (2 months in hours)`
- [ ] Verify: First month has original target data
- [ ] Verify: Last 2 months have all missing sensor values
- [ ] Verify: Timestamps sorted chronologically

#### New Timestamps at Beginning (Backward Extension)
- [ ] Target: 2024-02-01 to 2024-03-31 (2 months)
- [ ] Reconstructed: 2024-01-01 to 2024-03-31 (3 months)
- [ ] Expected: 1 month prepended + target data
- [ ] Verify: First month has all missing sensor values
- [ ] Verify: Last 2 months have original target data
- [ ] Verify: Result sorted by timestamp

#### New Timestamps at Both Ends (Bidirectional Extension)
- [ ] Target: 2024-02-01 to 2024-02-29 (1 month)
- [ ] Reconstructed: 2024-01-01 to 2024-03-31 (3 months)
- [ ] Expected: 1 month before + target + 1 month after
- [ ] Verify: Middle month has target data
- [ ] Verify: First and last months have missing sensor values

#### Sparse New Timestamps (Gaps Filling)
- [ ] Target: 2024-01-01, 2024-01-03, 2024-01-05 (every 2 days)
- [ ] Reconstructed: 2024-01-01 to 2024-01-05 (daily)
- [ ] Expected: All 5 days present
- [ ] Verify: Jan 1, 3, 5 have target data
- [ ] Verify: Jan 2, 4 have missing sensor values
- [ ] Verify: Proper chronological order

### 2. Sensor Column Handling

#### Multiple Sensor Columns
- [ ] Target has 3 sensors: WS_80m, WS_100m, WD_80m
- [ ] Reconstructed has same sensors
- [ ] Expected: New rows have all 3 columns with missing values
- [ ] Verify: All sensor columns present in new rows
- [ ] Verify: `ismissing(new_row.WS_80m) == true`

#### Different Sensor Heights
- [ ] Target sensors: WS_10m, WS_50m, WS_80m
- [ ] Expected: New timestamps have missing values for all heights
- [ ] Verify: Sensor metadata (heights) preserved in result

### 3. Edge Cases

#### Empty Target DataFrame
- [ ] Target: Empty DataFrame (0 rows)
- [ ] Reconstructed: 1000 timestamps
- [ ] Expected: All 1000 timestamps added with missing values
- [ ] Verify: `nrow(result) == 1000`

#### Empty Reconstructed DataFrame
- [ ] Target: 1000 timestamps
- [ ] Reconstructed: Empty DataFrame (0 rows)
- [ ] Expected: Returns copy of target unchanged
- [ ] Verify: `nrow(result) == 1000`
- [ ] Verify: Result identical to target

#### Single Timestamp Difference
- [ ] Target: 2024-01-01 00:00 to 2024-01-01 23:00 (24 hours)
- [ ] Reconstructed: Same + 2024-01-02 00:00 (1 extra)
- [ ] Expected: 25 rows total
- [ ] Verify: Last row timestamp is 2024-01-02 00:00
- [ ] Verify: Last row has missing sensor values

#### Identical Timestamps (Set Deduplication)
- [ ] Target: [T1, T2, T3]
- [ ] Reconstructed: [T1, T2, T3] (exact same)
- [ ] Expected: No new timestamps added
- [ ] Verify: Result == copy of target

#### Unsorted Input Timestamps
- [ ] Target: [T3, T1, T2] (unsorted)
- [ ] Reconstructed: [T5, T4, T1, T2, T3] (unsorted)
- [ ] Expected: Result has [T1, T2, T3, T4, T5] (sorted)
- [ ] Verify: `issorted(result.timestamp) == true`

### 4. Data Type Validation

#### Timestamp Types
- [ ] Verify: All timestamps are `DateTime` type
- [ ] Verify: No `missing` in timestamp column
- [ ] Verify: Timezone consistency

#### Sensor Value Types
- [ ] Verify: New rows have `Float64` missing type (not `Missing` type)
- [ ] Verify: `eltype(result.WS_80m) == Union{Missing, Float64}`

#### DataFrame Structure
- [ ] Verify: Column names match target_ts.sensors
- [ ] Verify: Column order preserved (timestamp first)
- [ ] Verify: No extra columns added

### 5. Performance Considerations

#### Large Time Range Extension
- [ ] Target: 1 year of hourly data (8760 rows)
- [ ] Reconstructed: 3 years of hourly data (26280 rows)
- [ ] Expected: 26280 rows total
- [ ] Verify: Operation completes in reasonable time
- [ ] Verify: Memory usage acceptable

#### Set Lookup Efficiency
- [ ] Test with 10,000+ timestamps
- [ ] Verify: Set-based lookup faster than array iteration
- [ ] Measure: Performance of `t in existing_timestamps`

### 6. Integration with merge_reconstruction_data

#### End-to-End Time Extension
- [ ] Target: Jan 2024 with some missing data
- [ ] Reconstructed: Jan-Mar 2024 with complete data
- [ ] Call: `merge_reconstruction_data(target_ts, reconstructed_ts)`
- [ ] Expected:
  - Jan data filled from reconstruction
  - Feb-Mar added from reconstruction
  - All timestamps sorted
- [ ] Verify: Time range extended correctly
- [ ] Verify: Original target data preserved where it exists

#### Preserves Existing Target Data
- [ ] Target: Has non-missing value at T1 for WS_80m = 5.5
- [ ] Reconstructed: Has different value at T1 for WS_80m = 6.0
- [ ] Expected: T1 keeps target value (5.5)
- [ ] Verify: `result[T1, :WS_80m] == 5.5` (target preserved)

## Test Helpers

### Mock Data Creation

```julia
"""
Create mock TimeSeriesData for testing append_new_timestamps
"""
function create_mock_timeseries_data(
    timestamps::Vector{DateTime},
    sensor_heights::Vector{Float64},
    fill_values::Bool = true
)::TimeSeriesData
    # Create DataFrame
    df = DataFrame(:timestamp => timestamps)

    # Create sensors
    sensors = SensorColumn[]
    for height in sensor_heights
        col_name = Symbol("WS_$(Int(height))m")
        if fill_values
            df[!, col_name] = rand(length(timestamps)) .* 10.0  # Random wind speeds
        else
            df[!, col_name] = missings(Float64, length(timestamps))
        end

        push!(sensors, SensorColumn(
            columnName = col_name,
            sensorType = "WindSpeed",
            statType = "avg",
            height = height,
            direction = "N/A",
            unit = "m/s"
        ))
    end

    return TimeSeriesData(df, sensors)
end

"""
Generate hourly timestamps for a date range
"""
function hourly_timestamps(start_date::Date, end_date::Date)::Vector{DateTime}
    start_dt = DateTime(start_date)
    end_dt = DateTime(end_date, 23, 0, 0)
    return collect(start_dt:Hour(1):end_dt)
end

"""
Verify timestamps are sorted
"""
function verify_sorted(df::DataFrame)::Bool
    return issorted(df.timestamp)
end

"""
Count rows with all missing sensor values
"""
function count_all_missing_rows(df::DataFrame, sensor_columns::Vector{Symbol})::Int
    count = 0
    for row in eachrow(df)
        if all(ismissing(row[col]) for col in sensor_columns)
            count += 1
        end
    end
    return count
end
```

## Expected Test File Structure

```julia
@testset "append_new_timestamps" begin
    @testset "Basic Functionality" begin
        @testset "No New Timestamps" begin
            # Test complete overlap
        end

        @testset "New Timestamps at End" begin
            # Test forward extension
        end

        @testset "New Timestamps at Beginning" begin
            # Test backward extension
        end

        @testset "Bidirectional Extension" begin
            # Test extension on both sides
        end
    end

    @testset "Sensor Column Handling" begin
        @testset "Multiple Sensor Columns" begin
            # Test all columns added with missing values
        end
    end

    @testset "Edge Cases" begin
        @testset "Empty Target" begin
            # Test empty target handling
        end

        @testset "Unsorted Inputs" begin
            # Test sorting behavior
        end
    end

    @testset "Integration Tests" begin
        @testset "End-to-End Time Extension" begin
            # Test full merge_reconstruction_data workflow
        end
    end
end
```

## Key Assertions

```julia
# Verify row count after extension
@test nrow(result) == nrow(target) + num_new_timestamps

# Verify sorting
@test issorted(result.timestamp)

# Verify new timestamps added
@test all(new_timestamp in result.timestamp for new_timestamp in expected_new_timestamps)

# Verify new rows have missing values
new_rows = filter(row -> row.timestamp in new_timestamps, result)
@test all(ismissing(row.WS_80m) for row in eachrow(new_rows))

# Verify target data preserved
for (i, target_row) in enumerate(eachrow(target_df))
    result_row = result[result.timestamp .== target_row.timestamp, :]
    @test nrow(result_row) == 1
    @test result_row[1, :WS_80m] == target_row.WS_80m
end

# Verify no duplicate timestamps
@test length(unique(result.timestamp)) == nrow(result)

# Verify column structure
@test propertynames(result) == propertynames(target_df)
```

## Implementation Priority

1. **HIGH**: Basic functionality tests (no overlap, end extension, beginning extension)
2. **HIGH**: Edge case - empty DataFrames
3. **MEDIUM**: Sensor column handling (multiple sensors, missing values)
4. **MEDIUM**: Sorting verification (unsorted inputs)
5. **MEDIUM**: Integration test with merge_reconstruction_data
6. **LOW**: Performance tests (large datasets)

## Related Files

- **Source**: `src/ReconstructCross/ProcessReconstructCrossCommand.jl` (append_new_timestamps, merge_reconstruction_data)
- **Types**: `src/Types/MastTimeSeries.jl` (TimeSeriesData, SensorColumn)
- **Dependencies**: DataFrames.jl, Dates.jl

## Notes

- This function is critical for enabling time range extension in cross-mast reconstruction
- Tests should verify both functional correctness and data preservation
- Focus on edge cases to prevent regressions
- Integration tests ensure proper interaction with merge_reconstruction_data
