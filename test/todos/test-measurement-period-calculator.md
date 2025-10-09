# TODO: Tests for MeasurementPeriodCalculator

## Overview

Create comprehensive tests for `src/TimeSeriesProcessing/MeasurementPeriodCalculator.jl` to verify:
- Optimal measurement period calculation
- **Critical: Year(1) - Second(1) time range calculation** (recently changed from month-aligned end)
- Daily coverage scoring
- Helper functions

## Code Change Context

**Recent modification:** Changed time range calculation from month-aligned end to exact 1-year period:
```julia
# OLD (month-aligned end - could be 365-395 days):
aligned_end = Date(year(end_date), month(end_date), daysinmonth(year(end_date), month(end_date)))
end_datetime = DateTime(year(aligned_end), month(aligned_end), day(aligned_end), 23, 59, 59)

# NEW (exact 1-year period):
start_datetime = DateTime(aligned_start)
end_datetime = start_datetime + Year(1) - Second(1)
```

## Test File Location

Create: `test/TimeSeriesProcessing/test_measurement_period_calculator.jl`

Add to `test/runtests.jl`:
```julia
"measurement_period" => [
    "TimeSeriesProcessing/test_measurement_period_calculator.jl"
]
```

## Test Scenarios

### 1. Helper Functions

#### `calculate_max_allowed_end_time`
- [ ] Valid meso data with regular 1-hour intervals → returns `last_time + 1hour - 1second`
- [ ] Empty timestamps → throws error
- [ ] Edge case: single timestamp → verify behavior
- [ ] Different representative intervals (10min, 1hour) → correct calculation

**Example:**
```julia
# Meso last time: 2024-08-31 23:00:00, interval: 1 hour
# Expected: 2024-09-01 00:00:00 - 1 second = 2024-08-31 23:59:59
```

#### `get_highest_windspeed_column`
- [ ] Multiple WS sensors (10m, 50m, 120m) → returns 120m sensor column
- [ ] Single WS sensor → returns that sensor
- [ ] No WS sensors (only temp/pressure) → throws error
- [ ] Mixed statTypes (avg, min, max) → only considers "avg"
- [ ] Mixed sensorTypes → ignores non-WindSpeed

#### `calculate_dataset_daily_scores`
- [ ] Full day (144 points at 10min, weight=1.0) → score = 24.0
- [ ] Half day (72 points) → score = 12.0 * weight
- [ ] Partial day → proportional score
- [ ] Missing WS column → returns empty DataFrame
- [ ] Data beyond max_end_date → filtered out
- [ ] Missing values in WS → contribute 0.0
- [ ] Different weight factors (0.5, 1.0) → scores scaled correctly
- [ ] Score cap: 150 points in a day → capped at 24 * weight

### 2. Daily Coverage Scoring

#### `calculate_daily_coverage_scores`
- [ ] Both single + cross full coverage → combined scores (max 2.0)
- [ ] Only single data → cross_score = 0, total_score from single only
- [ ] Only cross data → single_score = 0, total_score from cross only
- [ ] Overlapping periods → correct aggregation
- [ ] Different weights (single=1.0, cross=0.5) → verify weighted scores
- [ ] Normalized scores → verify range [0, 1] for each component
- [ ] Sorted by date → ascending order

**Score calculation:**
```julia
# Normalized scores (0-1 range):
single_normalized = actual_hours / 24.0
cross_normalized = actual_hours / 24.0
total_normalized = single_normalized + cross_normalized  # max 2.0
```

### 3. Optimal Period Finding

#### `find_optimal_year_range` - **CRITICAL TESTS**

##### Time Range Calculation (Year(1) - Second(1))
- [ ] **Start: 2023-08-01 00:00:00 → End: 2024-07-31 23:59:59**
  - Verify: `end == start + Year(1) - Second(1)`
  - Verify: Exactly 365 days (not 396 days as before!)

- [ ] **Start: 2024-01-01 00:00:00 → End: 2024-12-31 23:59:59** (LEAP YEAR)
  - Verify: Exactly 366 days for leap year
  - Verify: Feb 29 included in period

- [ ] **Start: 2024-02-01 00:00:00 → End: 2025-01-31 23:59:59**
  - Verify: Crosses leap year boundary correctly

- [ ] **Start: 2023-12-15 → End: 2024-12-14 23:59:59**
  - Month alignment: start becomes 2023-12-01
  - End: 2024-11-30 23:59:59 (start + Year(1) - Second(1))

##### Month Alignment
- [ ] Optimal start: 2024-03-15 → Aligned: 2024-03-01 00:00:00
- [ ] Optimal start: 2024-01-01 → No change (already month start)
- [ ] Optimal start: 2024-12-31 → Aligned: 2024-12-01 00:00:00

##### Edge Cases
- [ ] Date range < 365 days → throws error with message
- [ ] Date range = exactly 365 days → returns that period
- [ ] All zero scores → still returns valid TimeRange
- [ ] Multiple periods with same score → returns first one
- [ ] Best period at start of range → correct extraction
- [ ] Best period at end of range → correct extraction
- [ ] Best period in middle → correct extraction

##### Scoring Logic
- [ ] Period with highest total_score selected
- [ ] Sum of 365 daily scores calculated correctly
- [ ] Missing dates (gaps) treated as zero score

### 4. Integration Tests

#### `calculate_optimal_measurement_period`

##### Constraint Verification
- [ ] Meso boundary: period doesn't extend beyond meso max_end_time
- [ ] Cross boundary: period starts >= cross data start
- [ ] Cross coverage: need >= 365 days of cross data
- [ ] Earliest start: `min(meso_end - Year(1), cross_start, cross_end - 364days)`

##### Optimal Period Selection
- [ ] High coverage at start, low at end → selects start period
- [ ] Low coverage at start, high at end → selects end period
- [ ] Uniform coverage → any valid period acceptable
- [ ] Gap in middle of year → period avoids gap if possible

##### Year(1) - Second(1) Verification (End-to-End)
- [ ] Full realistic scenario:
  - Single data: 2023-01-01 to 2024-12-31
  - Cross data: 2023-07-01 to 2024-08-31
  - Meso data: 2023-01-01 to 2024-12-31
  - Expected optimal: 2023-08-01 to 2024-07-31 23:59:59
  - **Verify duration = exactly 365 days**

##### Leap Year Full Test
- [ ] Scenario spanning Feb 2024:
  - Optimal period: 2024-01-15 to 2025-01-14
  - Month aligned: 2024-01-01 to 2024-12-31 23:59:59
  - **Verify: 366 days (leap year)**

### 5. Regression Tests

#### Prevent Month Alignment Bug
- [ ] Period MUST NOT extend beyond Year(1) from start
- [ ] Test case that previously failed:
  - Input: optimal 365 days from Aug 1, 2023
  - OLD behavior: 2023-08-01 to 2024-08-31 (396 days) ❌
  - NEW behavior: 2023-08-01 to 2024-07-31 23:59:59 (365 days) ✅

## Test Data Creation

### Mock TimeSeriesData Creation
```julia
function create_mock_timeseries(
    start_time::DateTime,
    end_time::DateTime,
    interval::Period,
    ws_height::Float64,
    coverage_ratio::Float64 = 1.0  # 1.0 = full coverage
)::TimeSeriesData
    # Generate timestamps
    # Add wind speed sensor
    # Apply coverage ratio (some missing data)
    # Return TimeSeriesData
end
```

### Test Helpers
- `verify_exact_year_period(time_range)` → checks Year(1) - Second(1)
- `verify_month_aligned_start(time_range)` → checks first day of month
- `count_days_in_range(time_range)` → verify 365/366 days
- `create_daily_scores_vector(dates, scores)` → mock DailyScore data

## Expected Test File Structure

```julia
@testset "MeasurementPeriodCalculator" begin
    @testset "Helper Functions" begin
        @testset "calculate_max_allowed_end_time" begin
            # Tests here
        end

        @testset "get_highest_windspeed_column" begin
            # Tests here
        end

        @testset "calculate_dataset_daily_scores" begin
            # Tests here
        end
    end

    @testset "Daily Coverage Scoring" begin
        @testset "calculate_daily_coverage_scores" begin
            # Tests here
        end
    end

    @testset "Optimal Period Finding" begin
        @testset "find_optimal_year_range" begin
            @testset "Year(1) - Second(1) Calculation" begin
                # CRITICAL: Test exact 1-year periods
            end

            @testset "Month Alignment" begin
                # Test start alignment
            end

            @testset "Edge Cases" begin
                # Error cases, boundaries
            end
        end
    end

    @testset "Integration Tests" begin
        @testset "calculate_optimal_measurement_period" begin
            @testset "Constraint Verification" begin
                # Boundary tests
            end

            @testset "Optimal Selection" begin
                # Coverage-based selection
            end

            @testset "Year(1) - Second(1) End-to-End" begin
                # Full realistic scenarios
            end
        end
    end

    @testset "Regression Tests" begin
        @testset "Month Alignment Bug Prevention" begin
            # Prevent reverting to old behavior
        end
    end
end
```

## Key Assertions

```julia
# Exact year period
@test time_range.max_time == time_range.min_time + Year(1) - Second(1)

# Month aligned start
@test day(time_range.min_time) == 1
@test hour(time_range.min_time) == 0
@test minute(time_range.min_time) == 0

# End time format
@test hour(time_range.max_time) == 23
@test minute(time_range.max_time) == 59
@test second(time_range.max_time) == 59

# Period length (accounting for leap years)
days_in_period = (Date(time_range.max_time) - Date(time_range.min_time)).value + 1
@test days_in_period ∈ [365, 366]  # Depends on leap year

# Leap year specific
if isleapyear(year(time_range.min_time))
    @test days_in_period == 366
else
    @test days_in_period == 365
end
```

## Implementation Priority

1. **HIGH**: Year(1) - Second(1) calculation tests (regression prevention)
2. **HIGH**: Month alignment tests
3. **MEDIUM**: Helper function tests (foundation)
4. **MEDIUM**: Daily scoring tests
5. **LOW**: Edge cases and error handling

## Related Files

- Source: `src/TimeSeriesProcessing/MeasurementPeriodCalculator.jl`
- Types: `src/Types/MastTimeSeries.jl` (TimeSeriesData, TimeRange)
- Dependencies: `src/TimeSeriesProcessing/IntervalDetection.jl`

## Notes

- Use `@test_throws` for error cases
- Consider property-based testing for date ranges
- Mock data should cover various intervals (10min, 1hour)
- Test both regular and leap years explicitly
- Verify backward compatibility with existing code using this function
