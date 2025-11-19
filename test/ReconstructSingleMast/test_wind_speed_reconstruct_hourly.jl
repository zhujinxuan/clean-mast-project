using Test
using DataFrames
using Dates
using Statistics
using CleanMastProject.ReconstructSingleMast.WindSpeedReconstructHourly
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.ReconstructSingleMast: ReconstructedSuccess, ReconstructedFailure
using CleanMastProject.Types.SensorColumns: SensorColumn

"""
Generate synthetic hourly wind data with known shear exponent
"""
function generate_hourly_wind_data(;
    hour_start::DateTime = DateTime(2024,1,1,10,0,0),
    heights::Vector{Float64} = [60.0, 80.0, 100.0, 120.0],
    shear_exponent::Float64 = 0.2,
    base_speed::Float64 = 8.0
)
    timestamps = hour_start:Minute(10):(hour_start + Minute(50))
    n_timestamps = length(timestamps)

    df = DataFrame(:timestamp => collect(timestamps))

    # Generate wind speeds using power law
    reference_height = heights[end]  # Highest layer as reference

    for height in heights
        col_name = Symbol("ws_$(Int(height))m")
        # Add some temporal variation
        speeds = [
            base_speed * (height / reference_height)^shear_exponent * (1 + 0.1 * sin(2π * i / n_timestamps))
            for i in 1:n_timestamps
        ]
        df[!, col_name] = Vector{Union{Missing, Float64}}(speeds)
    end

    return df
end

@testset "WindSpeedReconstructHourly" begin
    @testset "calculate_shear_exponent - basic calculation" begin
        # Test with known shear exponent
        reference_height = 100.0
        true_alpha = 0.25
        base_speed = 8.0

        heights = [60.0, 80.0, 100.0, 120.0]
        heights_speeds = [
            (h, base_speed * (h / reference_height)^true_alpha)
            for h in heights
        ]

        calculated_alpha = calculate_shear_exponent(heights_speeds, reference_height)

        @test !isnothing(calculated_alpha)
        @test abs(calculated_alpha - true_alpha) < 0.01
    end

    @testset "calculate_shear_exponent - clamping" begin
        # Test that extreme values are clamped
        reference_height = 100.0

        # Test lower bound clamping
        heights_speeds = [(50.0, 10.0), (100.0, 5.0)]  # Decreasing with height
        alpha_low = calculate_shear_exponent(heights_speeds, reference_height)
        @test !isnothing(alpha_low)
        @test alpha_low >= -0.25  # Should be clamped to MIN_SHEAR_EXPONENT

        # Test upper bound clamping
        heights_speeds = [(50.0, 5.0), (100.0, 20.0)]  # Very steep increase
        alpha_high = calculate_shear_exponent(heights_speeds, reference_height)
        @test !isnothing(alpha_high)
        @test alpha_high <= 1.25  # Should be clamped to MAX_SHEAR_EXPONENT
    end

    @testset "calculate_shear_exponent - insufficient data" begin
        # Test with only 1 point (need at least 2)
        heights_speeds = [(100.0, 8.0)]
        result = calculate_shear_exponent(heights_speeds, 100.0)
        @test isnothing(result)
    end

    @testset "calculate_hourly_shear_exponent" begin
        df = generate_hourly_wind_data(
            heights = [60.0, 80.0, 100.0, 120.0],
            shear_exponent = 0.18
        )

        sensors = [
            SensorColumn(Symbol("ws_$(Int(h))m"), "WindSpeed", "N", h, "avg", "m/s")
            for h in [120.0, 100.0, 80.0]  # Top 3 layers
        ]

        alpha = calculate_hourly_shear_exponent(df, sensors)

        @test !isnothing(alpha)
        @test abs(alpha - 0.18) < 0.05  # Allow some error due to temporal variation
    end

    @testset "apply_shear_profile" begin
        reference_speed = 10.0
        reference_height = 100.0
        target_height = 80.0
        shear_exponent = 0.2

        result = apply_shear_profile(
            reference_speed,
            reference_height,
            target_height,
            shear_exponent
        )

        # Target height is lower, so speed should be lower
        @test result < reference_speed

        # Test the power law formula manually
        expected = reference_speed * (target_height / reference_height)^shear_exponent
        @test abs(result - expected) < 0.001
    end

    @testset "find_highest_available_reference" begin
        # Create test row with some missing values
        row = DataFrameRow(
            DataFrame(
                :timestamp => DateTime(2024,1,1,10,0,0),
                :ws_60m => missing,
                :ws_80m => 8.5,
                :ws_100m => 9.2,
                :ws_120m => 10.1
            ),
            1
        )

        sensors = [
            SensorColumn(:ws_120m, "WindSpeed", "N", 120.0, "avg", "m/s"),
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s"),
            SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s"),
            SensorColumn(:ws_60m, "WindSpeed", "N", 60.0, "avg", "m/s")
        ]

        # Find reference for 80m (should skip 80m itself)
        result = find_highest_available_reference(row, 80.0, sensors)

        @test !isnothing(result)
        @test result[1] == 120.0  # Highest available
        @test result[2] == 10.1
    end

    @testset "find_highest_available_reference - all missing except target" begin
        row = DataFrameRow(
            DataFrame(
                :timestamp => DateTime(2024,1,1,10,0,0),
                :ws_60m => missing,
                :ws_80m => 8.5,
                :ws_100m => missing,
                :ws_120m => missing
            ),
            1
        )

        sensors = [
            SensorColumn(:ws_120m, "WindSpeed", "N", 120.0, "avg", "m/s"),
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s"),
            SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s"),
            SensorColumn(:ws_60m, "WindSpeed", "N", 60.0, "avg", "m/s")
        ]

        result = find_highest_available_reference(row, 80.0, sensors)

        # No valid reference available
        @test isnothing(result)
    end

    @testset "reconstruct_targets_vectorized" begin
        # Generate hour data with known shear
        df = generate_hourly_wind_data(
            heights = [60.0, 80.0, 100.0, 120.0],
            shear_exponent = 0.2
        )

        # Create some missing values
        df[2, :ws_80m] = missing
        df[4, :ws_100m] = missing

        sensors = [
            SensorColumn(:ws_120m, "WindSpeed", "N", 120.0, "avg", "m/s"),
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s"),
            SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s")
        ]

        targets = [
            (df.timestamp[2], :ws_80m),
            (df.timestamp[4], :ws_100m)
        ]

        results = reconstruct_targets_vectorized(df, targets, 0.2, sensors)

        @test length(results) == 2
        @test all(r -> r isa ReconstructedSuccess || r isa ReconstructedFailure, results)

        # Check that successes have reasonable values
        successes = filter(r -> r isa ReconstructedSuccess, results)
        for success in successes
            @test success.value > 0
            @test success.value < 100
        end
    end

    @testset "reconstruct_hourly_speeds - integration test" begin
        # Generate realistic hour data
        df = generate_hourly_wind_data(
            heights = [60.0, 80.0, 100.0, 120.0],
            shear_exponent = 0.2,
            base_speed = 8.0
        )

        # Introduce missing values
        original_80m_2 = df[2, :ws_80m]
        original_100m_4 = df[4, :ws_100m]
        df[2, :ws_80m] = missing
        df[4, :ws_100m] = missing

        sensors = [
            SensorColumn(Symbol("ws_$(Int(h))m"), "WindSpeed", "N", h, "avg", "m/s")
            for h in [60.0, 80.0, 100.0, 120.0]
        ]

        hour_data = TimeSeriesData(df, sensors)
        results = reconstruct_hourly_speeds(hour_data, Minute(10))

        @test !isempty(results)

        # Check reconstruction accuracy
        successes = filter(r -> r isa ReconstructedSuccess, results)

        for success in successes
            if success.columnName == :ws_80m && success.timestamp == df.timestamp[2]
                # Check reconstruction accuracy
                error = abs(success.value - original_80m_2) / original_80m_2
                @test error < 0.15  # Within 15% error
            elseif success.columnName == :ws_100m && success.timestamp == df.timestamp[4]
                error = abs(success.value - original_100m_4) / original_100m_4
                @test error < 0.15
            end
        end
    end

    @testset "reconstruct_hourly_speeds - insufficient layers" begin
        # Test with only 2 sensors (need 3)
        df = generate_hourly_wind_data(heights = [60.0, 80.0])

        sensors = [
            SensorColumn(Symbol("ws_$(Int(h))m"), "WindSpeed", "N", h, "avg", "m/s")
            for h in [60.0, 80.0]
        ]

        hour_data = TimeSeriesData(df, sensors)
        results = reconstruct_hourly_speeds(hour_data, Minute(10))

        # Should return empty (not enough layers)
        @test isempty(results)
    end

    @testset "reconstruct_hourly_speeds - no missing values" begin
        # Test with complete data (no missing values)
        df = generate_hourly_wind_data(heights = [60.0, 80.0, 100.0, 120.0])

        sensors = [
            SensorColumn(Symbol("ws_$(Int(h))m"), "WindSpeed", "N", h, "avg", "m/s")
            for h in [60.0, 80.0, 100.0, 120.0]
        ]

        hour_data = TimeSeriesData(df, sensors)
        results = reconstruct_hourly_speeds(hour_data, Minute(10))

        # Should return empty (no targets to reconstruct)
        @test isempty(results)
    end
end
