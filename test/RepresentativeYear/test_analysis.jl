module TestRepresentativeYear

using Test
using Dates
using DataFrames
using Statistics
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.Types.RepresentativeYear: DirectionalCalibration, CalibrationResults, CalibrationEachWSSensor
using CleanMastProject.RepresentativeYear.Analysis
using CleanMastProject.Types.SpeedReferenceModel.SectorizedRegression: SpeedSector, SectorizedRegressionModel, SpeedPair
using CleanMastProject.Types.Sector: DirectionSector, DIRECTION_16_SECTORS

function generate_test_data_for_integration_test(;
    start_date::DateTime = DateTime(2024,1,1),
    duration_days::Int = 365,
    time_step::Period = Hour(1),
    base_ws::Float64 = 8.0,
    amplitude::Float64 = 2.0,
    noise_level::Float64 = 0.5
    ):: Tuple{TimeSeriesData, TimeSeriesData}
    # Generate timestamps
    timestamps = start_date:time_step:(start_date + Day(duration_days) - time_step)
    n_points = length(timestamps)
    
    # Generate synthetic wind speeds with annual pattern
    hours = Float64.(Dates.value.(Millisecond.(timestamps .- start_date))) / (1000 * 60 * 60)
    w = 2π / (365 * 24)  # Angular frequency for annual cycle
    
    # Generate mast data
    mast_ws = Vector{Union{Missing, Float64}}(base_ws .+ 0.42 * amplitude .* sin.(w .* hours) .+ randn(n_points) .* noise_level)
    mast_wd = Vector{Union{Missing, Float64}}(mod.(hours .* 5.0, 360.0))  # Simple rotating direction

    mast_df = DataFrame(
        timestamp = timestamps,
        ws_120m = mast_ws,
        ws_80m = mast_ws .* 0.9,  # Lower speed at lower height
        wd_120m = mast_wd,
        wd_80m = mast_wd .- 5.0  # Slight veer
    )

    # Create sensors
    mast_sensors = [
        SensorColumn(:ws_120m, "WindSpeed", "N", 120.0, "avg", "m/s"),
        SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s"),
        SensorColumn(:wd_120m, "WindDirection", "N", 120.0, "avg", "deg"),
        SensorColumn(:wd_80m, "WindDirection", "N", 80.0, "avg", "deg")
    ]
    mast_ts = TimeSeriesData(mast_df, mast_sensors)


    # Generate meso data with slightly different characteristics
    meso_timestamp = (start_date - Year(2)):time_step:(start_date + Day(duration_days) - time_step)
    meso_hours = Float64.(Dates.value.(Millisecond.(meso_timestamp .- start_date))) / (1000 * 60 * 60)
    meso_ws = base_ws * 1.1 .+ amplitude .* sin.(w .* meso_hours) 
    meso_wd = mod.(meso_hours .* 5.0, 360.0)
    # Meso data >= 2024 + 1 m/s; meso data < 2024 - 1 m/s
    meso_ws[year.(meso_timestamp) .== 2024] .-= 2.0
    meso_ws[year.(meso_timestamp) .== 2023] .+= 2.0

    meso_sensors = [
        SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s"),
        SensorColumn(:wd_100m, "WindDirection", "N", 100.0, "avg", "deg")
    ]
    meso_df = DataFrame(
        timestamp = meso_timestamp,
        ws_100m = meso_ws,
        wd_100m = meso_wd
    )
    meso_ts = TimeSeriesData(meso_df, meso_sensors)
    
    return mast_ts, meso_ts
end

function generate_test_data(;
    start_date::DateTime = DateTime(2024,1,1),
    duration_days::Int = 365,
    time_step::Period = Hour(1),
    base_ws::Float64 = 8.0,
    amplitude::Float64 = 2.0,
    noise_level::Float64 = 0.5
)::Tuple{TimeSeriesData, TimeSeriesData}
    # Generate timestamps
    timestamps = start_date:time_step:(start_date + Day(duration_days) - time_step)
    n_points = length(timestamps)
    
    # Generate synthetic wind speeds with annual pattern
    hours = Float64.(Dates.value.(Millisecond.(timestamps .- start_date))) / (1000 * 60 * 60)
    w = 2π / (365 * 24)  # Angular frequency for annual cycle
    
    # Generate mast data
    mast_ws = Vector{Union{Missing, Float64}}(base_ws .+ amplitude .* sin.(w .* hours) .+ randn(n_points) .* noise_level)
    mast_wd = Vector{Union{Missing, Float64}}(mod.(collect(1:n_points) .* 10.0, 360.0))  # Simple rotating direction
    
    mast_df = DataFrame(
        timestamp = timestamps,
        ws_120m = mast_ws,
        ws_80m = mast_ws .* 0.9,  # Lower speed at lower height
        wd_120m = mast_wd,
        wd_80m = mast_wd .- 5.0  # Slight veer
    )
    
    # Generate meso data with slightly different characteristics
    meso_ws = base_ws .* 1.1 .+ amplitude .* sin.(w .* hours) .+ randn(n_points) .* noise_level
    meso_wd = mast_wd .+ randn(n_points) .* 5.0  # Add some noise to directions
    
    meso_df = DataFrame(
        timestamp = timestamps,
        ws_100m = meso_ws,
        wd_100m = meso_wd
    )
    
    # Create sensors
    mast_sensors = [
        SensorColumn(:ws_120m, "WindSpeed", "N", 120.0, "avg", "m/s"),
        SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s"),
        SensorColumn(:wd_120m, "WindDirection", "N", 120.0, "avg", "deg"),
        SensorColumn(:wd_80m, "WindDirection", "N", 80.0, "avg", "deg")
    ]
    
    meso_sensors = [
        SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s"),
        SensorColumn(:wd_100m, "WindDirection", "N", 100.0, "avg", "deg")
    ]
    
    return TimeSeriesData(mast_df, mast_sensors), TimeSeriesData(meso_df, meso_sensors)
end

@testset "RepresentativeYear Analysis" begin
    mast_ts, meso_ts = generate_test_data()

    @testset "find_direction_sector" begin
        @test find_direction_sector(0.0) == 1    # N
        @test find_direction_sector(90.0) == 5   # E
        @test find_direction_sector(180.0) == 9  # S
        @test find_direction_sector(270.0) == 13 # W
        @test find_direction_sector(360.0) == 1  # N again
        @test find_direction_sector(-45.0) == 15 # NW
    end
    
    @testset "apply_calibration" begin
        # Create test data with known values and multiple heights
        test_df = DataFrame(
            timestamp = [DateTime(2024,1,1, h) for h in 1:5],
            ws_100m = [10.0, 20.0, 5.0, 15.0, missing],
            ws_80m = [9.0, 18.0, 4.5, 14.0, missing],
            ws_60m = [8.0, 16.0, 4.0, 13.0, missing]
        )
        
        # Create meso data with directions
        meso_df = DataFrame(
            timestamp = [DateTime(2024,1,1, h) for h in 1:5],
            ws_100m = [10.0, 20.0, 5.0, 15.0, missing],
            wd_100m = [0.0, 90.0, 180.0, 270.0, 0.0]
        )
        
        test_sensors = [
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s"),
            SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s"),
            SensorColumn(:ws_60m, "WindSpeed", "N", 60.0, "avg", "m/s")
        ]
        
        meso_sensors = [
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s"),
            SensorColumn(:wd_100m, "WindDirection", "N", 100.0, "avg", "deg")
        ]
        
        test_ts = TimeSeriesData(test_df, test_sensors)
        meso_ts = TimeSeriesData(meso_df, meso_sensors)
        
        # Create calibrations for each height
        calibrations = map(test_sensors) do sensor
            CalibrationEachWSSensor(
                sensor,  # target sensor
                meso_sensors[2],  # meso direction sensor
                map(DIRECTION_16_SECTORS) do sector
                    DirectionalCalibration(sector, 1.0, sector.center == 270 ? 100 : 0.1 * sector.center/22.5)
                end
            )
        end
        
        calibration = CalibrationResults(
            calibrations,
            DateTime(2024,1,1),
        )
        
        # Apply calibration
        calibrated = apply_calibration(test_ts, calibration, meso_ts)
        
        # Test that values are calibrated at each height
        for sensor in test_sensors
            col = sensor.columnName
            # Test that values are calibrated only when result is within bounds
            @test calibrated.df[1, col] == test_df[1, col]  
            @test calibrated.df[2, col] == test_df[2, col] + 0.1 * 90/22.5  # Calibrated with slope 1.0
            @test calibrated.df[3, col] == test_df[3, col] + 0.1 * 180/22.5  # Calibrated with slope 1.0
            @test calibrated.df[4, col] == test_df[4, col] # No calibration when result would be too high
            @test ismissing(calibrated.df[5, col])  # missing stays missing
        end
    end
end # end for RepresentativeYear Analysis 
end # end for module TestRepresentativeYear 
