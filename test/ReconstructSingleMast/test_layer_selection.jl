using Test
using DataFrames
using Dates
using Random
using CleanMastProject.ReconstructSingleMast.LayerSelection
using CleanMastProject.Types.SensorColumns: SensorColumn

"""
Generate test data with specified data availability per sensor
"""
function generate_test_hour_data(;
    n_timestamps::Int = 6,
    heights::Vector{Float64} = [60.0, 80.0, 100.0, 120.0],
    availability::Dict{Float64, Float64} = Dict(h => 1.0 for h in heights)
)
    timestamps = DateTime(2024,1,1,10,0,0):Minute(10):DateTime(2024,1,1,10,50,0)
    @assert length(timestamps) == n_timestamps

    df = DataFrame(:timestamp => collect(timestamps))

    for height in heights
        col_name = Symbol("ws_$(Int(height))m")
        avail = get(availability, height, 1.0)
        n_valid = round(Int, n_timestamps * avail)

        # Create column with appropriate number of missing values
        col_values = Vector{Union{Missing, Float64}}(undef, n_timestamps)
        valid_indices = randperm(n_timestamps)[1:n_valid]

        for i in 1:n_timestamps
            if i in valid_indices
                col_values[i] = 5.0 + rand()  # Random wind speed
            else
                col_values[i] = missing
            end
        end

        df[!, col_name] = col_values
    end

    return df
end

@testset "LayerSelection" begin
    @testset "select_reconstruction_layers - sufficient layers" begin
        # Create test data with 4 layers, all with >50% availability
        df = generate_test_hour_data(
            heights = [60.0, 80.0, 100.0, 120.0],
            availability = Dict(
                60.0 => 1.0,
                80.0 => 0.8,
                100.0 => 0.7,
                120.0 => 0.6
            )
        )

        sensors = [
            SensorColumn(Symbol("ws_$(Int(h))m"), "WindSpeed", "N", h, "avg", "m/s")
            for h in [60.0, 80.0, 100.0, 120.0]
        ]

        result = select_reconstruction_layers(df, sensors, Minute(10), 50.0, 0.5)

        @test !isnothing(result)
        @test length(result) == 3
        @test result[1].height == 120.0  # Highest
        @test result[2].height == 100.0  # Second highest
        @test result[3].height == 80.0   # Third highest
    end

    @testset "select_reconstruction_layers - insufficient availability" begin
        # Create test data where some layers have <50% availability
        df = generate_test_hour_data(
            heights = [60.0, 80.0, 100.0, 120.0],
            availability = Dict(
                60.0 => 1.0,
                80.0 => 0.4,  # Below 50%
                100.0 => 0.3, # Below 50%
                120.0 => 0.6
            )
        )

        sensors = [
            SensorColumn(Symbol("ws_$(Int(h))m"), "WindSpeed", "N", h, "avg", "m/s")
            for h in [60.0, 80.0, 100.0, 120.0]
        ]

        result = select_reconstruction_layers(df, sensors, Minute(10), 50.0, 0.5)

        # Only 2 layers meet criteria, need at least 3
        @test isnothing(result)
    end

    @testset "select_reconstruction_layers - height filter" begin
        # Test that only heights >50m are considered
        df = generate_test_hour_data(
            heights = [40.0, 60.0, 80.0, 100.0],
            availability = Dict(h => 1.0 for h in [40.0, 60.0, 80.0, 100.0])
        )

        sensors = [
            SensorColumn(Symbol("ws_$(Int(h))m"), "WindSpeed", "N", h, "avg", "m/s")
            for h in [40.0, 60.0, 80.0, 100.0]
        ]

        result = select_reconstruction_layers(df, sensors, Minute(10), 50.0, 0.5)

        @test !isnothing(result)
        @test length(result) == 3
        @test all(s -> s.height > 50.0, result)  # All heights > 50m
        @test !any(s -> s.height == 40.0, result)  # 40m excluded
    end

    @testset "select_reconstruction_layers - fewer than 3 eligible sensors" begin
        # Only 2 sensors above 50m
        df = generate_test_hour_data(
            heights = [40.0, 60.0, 80.0],
            availability = Dict(h => 1.0 for h in [40.0, 60.0, 80.0])
        )

        sensors = [
            SensorColumn(Symbol("ws_$(Int(h))m"), "WindSpeed", "N", h, "avg", "m/s")
            for h in [40.0, 60.0, 80.0]
        ]

        result = select_reconstruction_layers(df, sensors, Minute(10), 50.0, 0.5)

        # Only 2 sensors > 50m, need at least 3
        @test isnothing(result)
    end

    @testset "partition_training_and_targets" begin
        # Create test data with some missing values
        df = generate_test_hour_data(
            heights = [60.0, 80.0, 100.0, 120.0],
            availability = Dict(
                60.0 => 1.0,
                80.0 => 0.8,  # Some missing
                100.0 => 0.7, # Some missing
                120.0 => 1.0
            )
        )

        sensors = [
            SensorColumn(Symbol("ws_$(Int(h))m"), "WindSpeed", "N", h, "avg", "m/s")
            for h in [60.0, 80.0, 100.0, 120.0]
        ]

        training_layers, targets = partition_training_and_targets(
            df, sensors, Minute(10), 50.0
        )

        @test !isnothing(training_layers)
        @test length(training_layers) == 3

        # Should have targets for missing values in 80m and 100m
        @test !isempty(targets)

        # All targets should be within the top 3 layers
        top_3_cols = Set([s.columnName for s in training_layers])
        for (ts, col) in targets
            @test col ∈ top_3_cols
        end
    end

    @testset "partition_training_and_targets - insufficient layers" begin
        # Test with insufficient layers
        df = generate_test_hour_data(
            heights = [60.0, 80.0],
            availability = Dict(h => 1.0 for h in [60.0, 80.0])
        )

        sensors = [
            SensorColumn(Symbol("ws_$(Int(h))m"), "WindSpeed", "N", h, "avg", "m/s")
            for h in [60.0, 80.0]
        ]

        training_layers, targets = partition_training_and_targets(
            df, sensors, Minute(10), 50.0
        )

        @test isnothing(training_layers)
        @test isempty(targets)
    end

    @testset "partition_training_and_targets - no missing values" begin
        # Test with no missing values (all 100% available)
        df = generate_test_hour_data(
            heights = [60.0, 80.0, 100.0, 120.0],
            availability = Dict(h => 1.0 for h in [60.0, 80.0, 100.0, 120.0])
        )

        sensors = [
            SensorColumn(Symbol("ws_$(Int(h))m"), "WindSpeed", "N", h, "avg", "m/s")
            for h in [60.0, 80.0, 100.0, 120.0]
        ]

        training_layers, targets = partition_training_and_targets(
            df, sensors, Minute(10), 50.0
        )

        @test !isnothing(training_layers)
        @test isempty(targets)  # No missing values, no targets
    end
end
