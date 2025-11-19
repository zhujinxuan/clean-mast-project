using Test
using DataFrames
using Dates
using Statistics
using CleanMastProject.ReconstructSingleMast.WindDirectionReconstructHourly
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.ReconstructSingleMast: ReconstructedSuccess, ReconstructedFailure

"""
    generate_hourly_direction_data(;
        hour_start::DateTime = DateTime(2024,1,1,10,0,0),
        heights::Vector{Float64} = [60.0, 80.0, 100.0, 120.0],
        top_direction::Float64 = 45.0,
        direction_diffs::Dict{Float64, Float64} = Dict(
            100.0 => 2.0,
            80.0 => 5.0,
            60.0 => 8.0
        ),
        n_timestamps::Int = 6
    )

Generate synthetic hourly direction data for testing.

Creates direction values based on a known profile: each layer has a consistent
difference from the top layer (highest height).

# Arguments
- `hour_start`: Start time of the hour
- `heights`: Heights of sensors (will be sorted descending)
- `top_direction`: Direction at the top (highest) layer
- `direction_diffs`: Direction difference from top layer for each height
- `n_timestamps`: Number of timestamps in the hour (default 6 for 10-min intervals)

# Returns
- DataFrame with timestamp column and direction columns for each height
"""
function generate_hourly_direction_data(;
    hour_start::DateTime = DateTime(2024,1,1,10,0,0),
    heights::Vector{Float64} = [60.0, 80.0, 100.0, 120.0],
    top_direction::Float64 = 45.0,
    direction_diffs::Dict{Float64, Float64} = Dict(
        100.0 => 2.0,
        80.0 => 5.0,
        60.0 => 8.0
    ),
    n_timestamps::Int = 6
)
    # Sort heights descending to identify top layer
    sorted_heights = sort(heights, rev=true)
    top_height = sorted_heights[1]

    # Generate timestamps (10-minute intervals)
    timestamps = [hour_start + Minute(10 * (i-1)) for i in 1:n_timestamps]

    # Create DataFrame
    df = DataFrame(timestamp = timestamps)

    # Add direction columns
    for h in sorted_heights
        col_name = Symbol("WD_$(Int(h))m_avg")

        if h == top_height
            # Top layer has the base direction
            df[!, col_name] = fill(top_direction, n_timestamps)
        else
            # Other layers have direction = top_direction + difference
            diff = get(direction_diffs, h, 0.0)
            direction = mod(top_direction + diff, 360.0)
            df[!, col_name] = fill(direction, n_timestamps)
        end
    end

    # Add corresponding speed columns for weighting tests
    for h in sorted_heights
        col_name = Symbol("WS_$(Int(h))m_avg")
        # Use constant speed of 8.0 m/s by default
        df[!, col_name] = fill(8.0, n_timestamps)
    end

    return df
end

@testset "WindDirectionReconstructHourly" begin

    # ========================================================================
    # Utility Functions
    # ========================================================================

    @testset "direction_to_vector - cardinal directions" begin
        # North (0°)
        x, y = direction_to_vector(0.0)
        @test x ≈ 0.0 atol=1e-10
        @test y ≈ 1.0

        # East (90°)
        x, y = direction_to_vector(90.0)
        @test x ≈ 1.0
        @test y ≈ 0.0 atol=1e-10

        # South (180°)
        x, y = direction_to_vector(180.0)
        @test x ≈ 0.0 atol=1e-10
        @test y ≈ -1.0

        # West (270°)
        x, y = direction_to_vector(270.0)
        @test x ≈ -1.0
        @test y ≈ 0.0 atol=1e-10
    end

    @testset "direction_to_vector - with speed" begin
        # Northeast (45°) with speed 2.0
        x, y = direction_to_vector(45.0, 2.0)
        @test x ≈ 2.0 * sin(deg2rad(45.0))
        @test y ≈ 2.0 * cos(deg2rad(45.0))
    end

    @testset "vector_to_direction - basic conversion" begin
        # North
        @test vector_to_direction(0.0, 1.0) ≈ 0.0

        # East
        @test vector_to_direction(1.0, 0.0) ≈ 90.0

        # South
        @test vector_to_direction(0.0, -1.0) ≈ 180.0

        # West
        @test vector_to_direction(-1.0, 0.0) ≈ 270.0
    end

    @testset "vector_to_direction - round trip" begin
        for dir in [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0]
            x, y = direction_to_vector(dir)
            recovered_dir = vector_to_direction(x, y)
            @test recovered_dir ≈ dir atol=1e-10
        end
    end


    # ========================================================================
    # Vector Averaging
    # ========================================================================

    @testset "calculate_vector_average_direction - constant direction" begin
        df = DataFrame(
            WD_100m_avg = [45.0, 45.0, 45.0, 45.0]
        )

        avg_dir = calculate_vector_average_direction(df, :WD_100m_avg, nothing)

        @test !isnothing(avg_dir)
        @test avg_dir ≈ 45.0
    end

    @testset "calculate_vector_average_direction - wrapping around north" begin
        # Average of 350° and 10° should be 0° (not 180°)
        df = DataFrame(
            WD_100m_avg = [350.0, 10.0, 350.0, 10.0]
        )

        avg_dir = calculate_vector_average_direction(df, :WD_100m_avg, nothing)

        @test !isnothing(avg_dir)
        @test avg_dir ≈ 0.0 atol=1.0
    end

    @testset "calculate_vector_average_direction - speed weighted" begin
        df = DataFrame(
            WD_100m_avg = [0.0, 90.0, 0.0, 90.0],
            WS_100m_avg = [1.0, 3.0, 1.0, 3.0]  # Strong wind from east
        )

        avg_dir = calculate_vector_average_direction(df, :WD_100m_avg, :WS_100m_avg)

        @test !isnothing(avg_dir)
        # Should be closer to 90° due to speed weighting
        @test avg_dir > 60.0
    end

    @testset "calculate_vector_average_direction - all missing" begin
        df = DataFrame(
            WD_100m_avg = [missing, missing, missing]
        )

        avg_dir = calculate_vector_average_direction(df, :WD_100m_avg, nothing)

        @test isnothing(avg_dir)
    end

    # ========================================================================
    # Profile Calculation
    # ========================================================================

    @testset "calculate_hourly_direction_difference - constant difference" begin
        df = DataFrame(
            WD_120m_avg = [45.0, 45.0, 45.0],
            WD_100m_avg = [50.0, 50.0, 50.0]  # Consistently 5° more
        )

        sensors = [
            SensorColumn(Symbol("WD_120m_avg"), "WindDirection", "N", 120.0, "avg", "deg"),
            SensorColumn(Symbol("WD_100m_avg"), "WindDirection", "N", 100.0, "avg", "deg")
        ]

        source_sensor = sensors[1]  # 120m (top)
        target_sensor = sensors[2]  # 100m

        diff = calculate_hourly_direction_difference(df, source_sensor, target_sensor, sensors)

        @test !isnothing(diff)
        @test diff ≈ 5.0
    end

    @testset "calculate_hourly_direction_difference - wrapping" begin
        df = DataFrame(
            WD_120m_avg = [350.0, 350.0, 350.0],
            WD_100m_avg = [10.0, 10.0, 10.0]  # Difference should be +20°, not +380°
        )

        sensors = [
            SensorColumn(Symbol("WD_120m_avg"), "WindDirection", "N", 120.0, "avg", "deg"),
            SensorColumn(Symbol("WD_100m_avg"), "WindDirection", "N", 100.0, "avg", "deg")
        ]

        diff = calculate_hourly_direction_difference(df, sensors[1], sensors[2], sensors)

        @test !isnothing(diff)
        @test diff ≈ 20.0 atol=1.0
    end

    @testset "calculate_hourly_direction_difference - all missing" begin
        df = DataFrame(
            WD_120m_avg = [missing, missing],
            WD_100m_avg = [missing, missing]
        )

        sensors = [
            SensorColumn(Symbol("WD_120m_avg"), "WindDirection", "N", 120.0, "avg", "deg"),
            SensorColumn(Symbol("WD_100m_avg"), "WindDirection", "N", 100.0, "avg", "deg")
        ]

        diff = calculate_hourly_direction_difference(df, sensors[1], sensors[2], sensors)

        @test isnothing(diff)
    end

    # ========================================================================
    # Reconstruction Logic
    # ========================================================================

    @testset "get_top_layer_direction - valid direction" begin
        df = DataFrame(
            timestamp = [DateTime(2024,1,1,10,0,0)],
            WD_120m_avg = [45.0]
        )
        row = df[1, :]
        top_sensor = SensorColumn(Symbol("WD_120m_avg"), "WindDirection", "N", 120.0, "avg", "deg")

        dir = get_top_layer_direction(row, top_sensor)

        @test !isnothing(dir)
        @test dir == 45.0
    end

    @testset "get_top_layer_direction - missing value" begin
        df = DataFrame(
            timestamp = [DateTime(2024,1,1,10,0,0)],
            WD_120m_avg = [missing]
        )
        row = df[1, :]
        top_sensor = SensorColumn(Symbol("WD_120m_avg"), "WindDirection", "N", 120.0, "avg", "deg")

        dir = get_top_layer_direction(row, top_sensor)

        @test isnothing(dir)
    end

    @testset "get_top_layer_direction - invalid direction" begin
        # Test out of range
        df = DataFrame(
            timestamp = [DateTime(2024,1,1,10,0,0)],
            WD_120m_avg = [400.0]
        )
        row = df[1, :]
        top_sensor = SensorColumn(Symbol("WD_120m_avg"), "WindDirection", "N", 120.0, "avg", "deg")

        dir = get_top_layer_direction(row, top_sensor)

        @test isnothing(dir)

        # Test negative
        df2 = DataFrame(
            timestamp = [DateTime(2024,1,1,10,0,0)],
            WD_120m_avg = [-10.0]
        )
        row2 = df2[1, :]
        dir2 = get_top_layer_direction(row2, top_sensor)

        @test isnothing(dir2)
    end


    # ========================================================================
    # Integration Tests
    # ========================================================================

    @testset "reconstruct_hourly_directions - successful reconstruction" begin
        # Create test data with known profile
        df = generate_hourly_direction_data(
            hour_start = DateTime(2024,1,1,10,0,0),
            heights = [60.0, 80.0, 100.0, 120.0],
            top_direction = 45.0,
            direction_diffs = Dict(100.0 => 2.0, 80.0 => 5.0, 60.0 => 8.0)
        )

        # Convert columns to Union{Missing, Float64} to allow missing values
        for col in names(df)
            if col != "timestamp"
                df[!, col] = Vector{Union{Missing, Float64}}(df[!, col])
            end
        end

        # Introduce missing values at specific timestamps
        df[2, :WD_100m_avg] = missing
        df[3, :WD_80m_avg] = missing

        sensors = [
            SensorColumn(Symbol("WD_120m_avg"), "WindDirection", "N", 120.0, "avg", "deg"),
            SensorColumn(Symbol("WD_100m_avg"), "WindDirection", "N", 100.0, "avg", "deg"),
            SensorColumn(Symbol("WD_80m_avg"), "WindDirection", "N", 80.0, "avg", "deg"),
            SensorColumn(Symbol("WD_60m_avg"), "WindDirection", "N", 60.0, "avg", "deg"),
            SensorColumn(Symbol("WS_120m_avg"), "WindSpeed", "N", 120.0, "avg", "m/s"),
            SensorColumn(Symbol("WS_100m_avg"), "WindSpeed", "N", 100.0, "avg", "m/s"),
            SensorColumn(Symbol("WS_80m_avg"), "WindSpeed", "N", 80.0, "avg", "m/s"),
            SensorColumn(Symbol("WS_60m_avg"), "WindSpeed", "N", 60.0, "avg", "m/s")
        ]

        ts_data = TimeSeriesData(df, sensors)

        results = reconstruct_hourly_directions(ts_data, Minute(10))

        # Should successfully reconstruct the 2 missing values
        successes = [r for r in results if r isa ReconstructedSuccess]
        @test length(successes) == 2

        # Check reconstructed values are approximately correct
        for success in successes
            if success.columnName == Symbol("WD_100m_avg")
                @test success.value ≈ 47.0 atol=1.0  # 45 + 2
            elseif success.columnName == Symbol("WD_80m_avg")
                @test success.value ≈ 50.0 atol=1.0  # 45 + 5
            end
        end
    end

    @testset "reconstruct_hourly_directions - insufficient layers" begin
        # Only 2 sensors (need 3)
        df = DataFrame(
            timestamp = [DateTime(2024,1,1,10,0,0)],
            WD_100m_avg = [45.0],
            WD_80m_avg = [missing]
        )

        sensors = [
            SensorColumn(Symbol("WD_100m_avg"), "WindDirection", "N", 100.0, "avg", "deg"),
            SensorColumn(Symbol("WD_80m_avg"), "WindDirection", "N", 80.0, "avg", "deg")
        ]

        ts_data = TimeSeriesData(df, sensors)

        results = reconstruct_hourly_directions(ts_data, Minute(10))

        @test isempty(results)
    end

    @testset "reconstruct_hourly_directions - no missing values" begin
        # All values present, no targets
        df = generate_hourly_direction_data()

        sensors = [
            SensorColumn(Symbol("WD_120m_avg"), "WindDirection", "N", 120.0, "avg", "deg"),
            SensorColumn(Symbol("WD_100m_avg"), "WindDirection", "N", 100.0, "avg", "deg"),
            SensorColumn(Symbol("WD_80m_avg"), "WindDirection", "N", 80.0, "avg", "deg"),
            SensorColumn(Symbol("WD_60m_avg"), "WindDirection", "N", 60.0, "avg", "deg")
        ]

        ts_data = TimeSeriesData(df, sensors)

        results = reconstruct_hourly_directions(ts_data, Minute(10))

        @test isempty(results)
    end

    @testset "reconstruct_hourly_directions - empty direction profile" begin
        # All direction data missing, cannot calculate profile
        df = DataFrame(
            timestamp = [DateTime(2024,1,1,10,0,0), DateTime(2024,1,1,10,10,0)],
            WD_120m_avg = [missing, missing],
            WD_100m_avg = [missing, missing],
            WD_80m_avg = [missing, 50.0]  # One value but not enough for profile
        )

        sensors = [
            SensorColumn(Symbol("WD_120m_avg"), "WindDirection", "N", 120.0, "avg", "deg"),
            SensorColumn(Symbol("WD_100m_avg"), "WindDirection", "N", 100.0, "avg", "deg"),
            SensorColumn(Symbol("WD_80m_avg"), "WindDirection", "N", 80.0, "avg", "deg")
        ]

        ts_data = TimeSeriesData(df, sensors)

        results = reconstruct_hourly_directions(ts_data, Minute(10))

        # All targets should fail
        @test all(r isa ReconstructedFailure for r in results)
    end

end
