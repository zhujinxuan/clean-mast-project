using Test
using DataFrames
using Dates
using Statistics
using CleanMastProject

# Import specific types and modules
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, SensorColumn
using CleanMastProject.Types.DirectionReferenceModel.DirectionOffset: DirectionOffsetModel, DirectionPair, DirectionOffsetParams
using CleanMastProject.WindDirectionModels.DirectionOffsetTraining: train

@testset "DirectionOffsetTraining" begin
    # Create test data
    timestamps = DateTime(2023,1,1):Minute(10):DateTime(2023,1,2)
    
    # Create mast sensors
    mast_sensors = [
        SensorColumn(Symbol("dir_40m"), "test_format", "WindDirection", "none", 40.0, "avg", "deg"),
        SensorColumn(Symbol("dir_30m"), "test_format", "WindDirection", "none", 30.0, "avg", "deg")
    ]
    
    # Create meso sensors
    meso_sensors = [
        SensorColumn(Symbol("dir_50m"), "test_format", "WindDirection", "none", 50.0, "avg", "deg"),
        SensorColumn(Symbol("dir_35m"), "test_format", "WindDirection", "none", 35.0, "avg", "deg")
    ]
    
    @testset "Basic Training" begin
        # Create test data with known offset
        offset = 15.0  # 15 degree offset
        n = length(timestamps)
        
        # Generate random directions for mast
        mast_directions = rand(n) .* 360
        # Apply known offset to create meso directions
        meso_directions = mod.(mast_directions .+ offset, 360)
        
        mast_df = DataFrame(
            timestamp = timestamps,
            dir_40m = mast_directions,
            dir_30m = mast_directions  # Same direction at both heights for simplicity
        )
        
        meso_df = DataFrame(
            timestamp = timestamps,
            dir_50m = meso_directions,
            dir_35m = meso_directions  # Same direction at both heights for simplicity
        )
        
        # Create TimeSeriesData objects
        mast_data = TimeSeriesData(mast_df, mast_sensors)
        meso_data = TimeSeriesData(meso_df, meso_sensors)
        
        # Train model
        model = train(DirectionOffsetModel, DirectionOffsetParams(), mast_data, meso_data)
        
        # Test model structure
        @test model isa DirectionOffsetModel
        @test !isempty(model.pairs)
        
        # Test direction pairs
        for pair in model.pairs
            @test pair isa DirectionPair
            @test pair.mast_sensor in mast_sensors
            @test pair.meso_sensor in meso_sensors
            # Test that the calculated offset is close to the known offset
            # Allow for some numerical error due to circular statistics
            @test isapprox(pair.offset, -offset, atol=1.0)
        end
    end
    
    @testset "Circular Boundary Cases" begin
        n = length(timestamps)
        # Test with directions near 0/360 boundary
        mast_df_boundary = DataFrame(
            timestamp = timestamps,
            dir_40m = vcat(fill(355.0, div(n,2)), fill(5.0, n - div(n,2))),
            dir_30m = vcat(fill(355.0, div(n,2)), fill(5.0, n - div(n,2)))
        )
        
        meso_df_boundary = DataFrame(
            timestamp = timestamps,
            dir_50m = vcat(fill(5.0, div(n,2)), fill(15.0, n - div(n,2))),
            dir_35m = vcat(fill(5.0, div(n,2)), fill(15.0, n - div(n,2)))
        )
        
        mast_data_boundary = TimeSeriesData(mast_df_boundary, mast_sensors)
        meso_data_boundary = TimeSeriesData(meso_df_boundary, meso_sensors)
        
        model_boundary = train(DirectionOffsetModel, DirectionOffsetParams(), mast_data_boundary, meso_data_boundary)
        
        # Test that the model handles circular boundary correctly
        for pair in model_boundary.pairs
            # Expected offset should be around 10 degrees
            @test isapprox(pair.offset, -10.0, atol=1.0)
        end
    end
end 