module TestTraining

using Test
using Dates
using DataFrames
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.CleanMastConfig: TimeRange
using ...ReconstructMeso.Training

@testset "Training" begin
    # Create test data with known correlation
    timestamps = DateTime(2024,1,1):Hour(1):DateTime(2024,1,10)
    
    # Mast data (y = 2x + 1 with some noise)
    mast_df = DataFrame(
        timestamp = timestamps,
        ws_80m = 2.0 .* collect(1:length(timestamps)) .+ 1.0 .+ randn(length(timestamps)) .* 0.1,
        wd_80m = mod.(collect(1:length(timestamps)) .* 10 .+ 5.0, 360)
    )
    
    # Meso data (x values)
    meso_df = DataFrame(
        timestamp = timestamps,
        ws_75m = collect(1:length(timestamps)) .+ randn(length(timestamps)) .* 0.05,
        wd_75m = mod.(collect(1:length(timestamps)) .* 10, 360)
    )
    
    mast_sensors = [
        SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s"),
        SensorColumn(:wd_80m, "WindDirection", "N", 80.0, "avg", "deg")
    ]
    
    meso_sensors = [
        SensorColumn(:ws_75m, "WindSpeed", "N", 75.0, "avg", "m/s"),
        SensorColumn(:wd_75m, "WindDirection", "N", 75.0, "avg", "deg")
    ]
    
    mast_ts = TimeSeriesData(mast_df, mast_sensors)
    meso_ts = TimeSeriesData(meso_df, meso_sensors)

    @testset "train_wind_speed" begin
        ws_results = train_wind_speed(mast_ts, meso_ts)
        @test length(ws_results) == 1
        @test haskey(ws_results, :ws_80m)
        
        result = ws_results[:ws_80m]
        # Check slope is close to 2.0 (with some tolerance for noise)
        @test isapprox(result.slope, 2.0, atol=0.1)
        # Check intercept is close to 1.0
        @test isapprox(result.intercept, 1.0, atol=0.1)
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

end 