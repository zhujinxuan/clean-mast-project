module TestTraining

using Test
using Dates
using DataFrames
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, SensorColumn
using CleanMastProject.Types.ReconstructMeso: TrainingTimeRange, WindSpeedSectorModel
using CleanMastProject.ReconstructMeso.Training

@testset "Training without missing values" begin
    # Create test data with known correlation for each sector
    timestamps = DateTime(2024,1,1):Hour(1):DateTime(2024,1,10)
    n_points = length(timestamps)
    
    # Create sector-based correlations
    # Sector 0-22.5: y = 2x + 1
    # Sector 22.5-45: y = 1.5x + 2
    # etc.
    function get_sector_params(direction)
        sector = floor(Int, direction / 22.5)
        slope = 2.0 - 0.1 * sector
        intercept = 1.0 + 0.2 * sector
        return slope, intercept
    end
    
    # Generate test data
    directions = mod.(collect(1:n_points) .* 10, 360)  # Covers all sectors
    meso_speeds = collect(1:n_points) .+ randn(n_points) .* 0.05
    
    # Calculate mast speeds based on sector
    mast_speeds = map(1:n_points) do i
        slope, intercept = get_sector_params(directions[i])
        slope * meso_speeds[i] + intercept + randn() * 0.1
    end
    
    # Create DataFrames
    mast_df = DataFrame(
        timestamp = timestamps,
        ws_80m = mast_speeds,
        wd_80m = directions .+ 5.0  # Add 5 degrees offset for direction
    )
    
    meso_df = DataFrame(
        timestamp = timestamps,
        ws_75m = meso_speeds,
        wd_75m = directions
    )
    
    mast_sensors = [
        SensorColumn(:ws_80m, "ws_80m", "WindSpeed", "N", 80.0, "avg", "m/s"),
        SensorColumn(:wd_80m, "wd_80m", "WindDirection", "N", 80.0, "avg", "deg")
    ]
    
    meso_sensors = [
        SensorColumn(:ws_75m, "ws_75m", "WindSpeed", "N", 75.0, "avg", "m/s"),
        SensorColumn(:wd_75m, "wd_75m", "WindDirection", "N", 75.0, "avg", "deg")
    ]
    
    mast_ts = TimeSeriesData(mast_df, mast_sensors)
    meso_ts = TimeSeriesData(meso_df, meso_sensors)

    time_range = TrainingTimeRange(DateTime(2024,1,1), DateTime(2024,1,10))

    @testset "train_wind_speed" begin
        ws_results = train_wind_speed(mast_ts, meso_ts)
        @test length(ws_results) == 1
        @test haskey(ws_results, :ws_80m)
        
        result = ws_results[:ws_80m]
        @test length(result.sector_models) == 16  # 16 sectors
        
        # Test each sector model
        for model in result.sector_models
            # Get theoretical parameters for this sector
            slope, intercept = get_sector_params((model.sector_start + model.sector_end) / 2)
            
            # Check slope and intercept are close to theoretical values
            # Use larger tolerance due to sector-based fitting
            @test isapprox(model.slope, slope, atol=0.3)
            @test isapprox(model.intercept, intercept, atol=0.5)
        end
    end

    @testset "train_wind_direction" begin
        wd_results = train_wind_direction(mast_ts, meso_ts)
        @test length(wd_results) == 1
        @test haskey(wd_results, :wd_80m)
        
        result = wd_results[:wd_80m]
        # Check difference is close to 5.0 (the offset we added)
        @test isapprox(result.diff, 5.0, atol=1.0)
    end
end

@testset "Training with 10% missing values" begin
    timestamps = DateTime(2024,1,1):Hour(1):DateTime(2024,1,10)
    n_points = length(timestamps)
    
    # Create mask for missing values (10% random missing)
    missing_mask_mast = rand(n_points) .> 0.9
    missing_mask_meso = rand(n_points) .> 0.9
    
    # Create sector-based correlations
    function get_sector_params(direction)
        sector = floor(Int, direction / 22.5)
        slope = 2.0 - 0.1 * sector
        intercept = 1.0 + 0.2 * sector
        return slope, intercept
    end
    
    # Generate test data
    directions = mod.(collect(1:n_points) .* 10, 360)
    meso_speeds = collect(1:n_points) .+ randn(n_points) .* 0.05
    
    # Calculate mast speeds based on sector
    mast_speeds = map(1:n_points) do i
        slope, intercept = get_sector_params(directions[i])
        slope * meso_speeds[i] + intercept + randn() * 0.1
    end
    
    # Apply missing values
    mast_df = DataFrame(
        timestamp = timestamps,
        ws_80m = [missing_mask_mast[i] ? missing : mast_speeds[i] for i in 1:n_points],
        wd_80m = [missing_mask_mast[i] ? missing : directions[i] + 5.0 for i in 1:n_points]
    )
    
    meso_df = DataFrame(
        timestamp = timestamps,
        ws_75m = [missing_mask_meso[i] ? missing : meso_speeds[i] for i in 1:n_points],
        wd_75m = [missing_mask_meso[i] ? missing : directions[i] for i in 1:n_points]
    )
    
    mast_sensors = [
        SensorColumn(:ws_80m, "ws_80m", "WindSpeed", "N", 80.0, "avg", "m/s"),
        SensorColumn(:wd_80m, "wd_80m", "WindDirection", "N", 80.0, "avg", "deg")
    ]
    
    meso_sensors = [
        SensorColumn(:ws_75m, "ws_75m", "WindSpeed", "N", 75.0, "avg", "m/s"),
        SensorColumn(:wd_75m, "wd_75m", "WindDirection", "N", 75.0, "avg", "deg")
    ]
    
    mast_ts = TimeSeriesData(mast_df, mast_sensors)
    meso_ts = TimeSeriesData(meso_df, meso_sensors)

    @testset "train_wind_speed with missing values" begin
        ws_results = train_wind_speed(mast_ts, meso_ts)
        @test length(ws_results) == 1
        @test haskey(ws_results, :ws_80m)
        
        result = ws_results[:ws_80m]
        @test length(result.sector_models) == 16
        
        # Test each sector model with increased tolerance
        for model in result.sector_models
            slope, intercept = get_sector_params((model.sector_start + model.sector_end) / 2)
            @test isapprox(model.slope, slope, atol=0.4)
            @test isapprox(model.intercept, intercept, atol=0.6)
        end
    end

    @testset "train_wind_direction with missing values" begin
        wd_results = train_wind_direction(mast_ts, meso_ts)
        @test length(wd_results) == 1
        @test haskey(wd_results, :wd_80m)
        
        result = wd_results[:wd_80m]
        # Increase tolerance due to missing values
        @test isapprox(result.diff, 5.0, atol=2.0)
    end
end

end 