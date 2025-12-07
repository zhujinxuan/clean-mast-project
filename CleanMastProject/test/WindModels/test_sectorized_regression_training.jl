using Test
using DataFrames
using Dates
using Statistics
using CleanMastProject

# Import specific types and modules
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.Types.SpeedReferenceModel.SectorizedRegression: SectorizedRegressionModel, SpeedPair, SpeedSector, SectorizedRegressionParams
using CleanMastProject.Types.Sector: DirectionSector
using CleanMastProject.WindSpeedModels.SectorizedRegressionTraining: train

@testset "SectorizedRegressionTraining" begin
    # Create test data
    timestamps = DateTime(2023,1,1):Minute(10):DateTime(2023,1,2)
    
    # Create mast sensors
    mast_sensors = [
        SensorColumn(Symbol("speed_40m"), "WindSpeed", "none", 40.0, "avg", "m/s"),
        SensorColumn(Symbol("speed_30m"), "WindSpeed", "none", 30.0, "avg", "m/s")
    ]
    
    # Create meso sensors
    meso_sensors = [
        SensorColumn(Symbol("speed_50m"), "WindSpeed", "none", 50.0, "avg", "m/s"),
        SensorColumn(Symbol("dir_50m"), "WindDirection", "none", 50.0, "avg", "deg")
    ]
    
    # Create test data frames
    mast_df = DataFrame(
        timestamp = timestamps,
        speed_40m = Vector{Union{Missing, Float64}}(rand(length(timestamps)) .* 10),  # Random speeds 0-10 m/s
        speed_30m = Vector{Union{Missing, Float64}}(rand(length(timestamps)) .* 8)     # Random speeds 0-8 m/s
    )
    
    meso_df = DataFrame(
        timestamp = timestamps,
        speed_50m = Vector{Union{Missing, Float64}}(rand(length(timestamps)) .* 12),   # Random speeds 0-12 m/s
        dir_50m = Vector{Union{Missing, Float64}}(rand(length(timestamps)) .* 360)     # Random directions 0-360 deg
    )
    
    # Create TimeSeriesData objects
    mast_data = TimeSeriesData(mast_df, mast_sensors)
    meso_data = TimeSeriesData(meso_df, meso_sensors)
    
    # Define sectors for testing - 4 sectors of 90 degrees each
    sectors = [
        DirectionSector("N", 0.0, 90.0),    # 315° to 45°
        DirectionSector("E", 90.0, 90.0),   # 45° to 135°
        DirectionSector("S", 180.0, 90.0),  # 135° to 225°
        DirectionSector("W", 270.0, 90.0)   # 225° to 315°
    ]
    
    # Test parameters
    params = SectorizedRegressionParams(sectors)
    
    @testset "Model Training" begin
        # Train the model
        model = train(SectorizedRegressionModel, params, mast_data, meso_data)
        
        # Test model structure
        @test model isa SectorizedRegressionModel
        @test !isempty(model.pairs)
        
        # Test speed pairs
        for pair in model.pairs
            @test pair isa SpeedPair
            @test pair.mast_speed_sensor in mast_sensors
            @test pair.meso_speed_sensor in meso_sensors
            @test pair.meso_direction_sensor in meso_sensors
            
            # Test sector models
            @test length(pair.sectors) == length(sectors)
            for sector_model in pair.sectors
                @test sector_model isa SpeedSector
                @test !isnan(sector_model.slope)
                @test !isnan(sector_model.intercept)
            end
        end
    end
    
    @testset "Sector Coverage" begin
        # Create data with specific sector coverage
        meso_df_sectors = copy(meso_df)
        n = length(timestamps)
        quarter = div(n, 4)
        
        # Distribute directions across sectors
        meso_df_sectors[1:quarter, :dir_50m] .= 0.0       # North sector
        meso_df_sectors[quarter+1:2*quarter, :dir_50m] .= 90.0    # East sector
        meso_df_sectors[2*quarter+1:3*quarter, :dir_50m] .= 180.0  # South sector
        meso_df_sectors[3*quarter+1:end, :dir_50m] .= 270.0   # West sector
        
        meso_data_sectors = TimeSeriesData(meso_df_sectors, meso_sensors)
        
        model_sectors = train(SectorizedRegressionModel, params, mast_data, meso_data_sectors)
        
        # Test that each sector has a model
        for pair in model_sectors.pairs
            @test length(pair.sectors) == length(sectors)
            sector_centers = [s.direction_sector.center for s in pair.sectors]
            @test all(center -> any(s -> s.center == center, sectors), sector_centers)
        end
    end
end 