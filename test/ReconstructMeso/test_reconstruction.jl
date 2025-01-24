module TestReconstruction

using Test
using DataFrames
using Dates
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, SensorColumn
using CleanMastProject.Types.ReconstructMeso: WindSpeedTrainResult, WindDirectionTrainResult, 
                                            WindSpeedSectorModel, TrainingTimeRange
using CleanMastProject.ReconstructMeso.Reconstruction: get_sector_model, fill_missing_data

@testset "Reconstruction" begin
    # Create test data
    sensors = [
        SensorColumn(:ws_80m, "ws_80m", "WindSpeed", "N", 80.0, "avg", "m/s")
        SensorColumn(:wd_80m, "wd_80m", "WindDirection", "N", 80.0, "avg", "deg")
    ]

    @testset "get_sector_model" begin
        sector_models = [
            WindSpeedSectorModel(0.0, 90.0, 1.1, 0.5),
            WindSpeedSectorModel(90.0, 180.0, 1.2, 0.6),
            WindSpeedSectorModel(180.0, 270.0, 1.3, 0.7),
            WindSpeedSectorModel(270.0, 360.0, 1.4, 0.8)
        ]
        
        train_result = WindSpeedTrainResult(
            sensors[1], sensors[1], sensors[2],
            sector_models
        )
        
        # Test each sector
        @test get_sector_model(45.0, train_result) == sector_models[1]
        @test get_sector_model(135.0, train_result) == sector_models[2]
        @test get_sector_model(225.0, train_result) == sector_models[3]
        @test get_sector_model(315.0, train_result) == sector_models[4]
        
        # Test sector boundaries
        @test get_sector_model(0.0, train_result) == sector_models[1]
        @test get_sector_model(90.0, train_result) == sector_models[2]
        @test get_sector_model(180.0, train_result) == sector_models[3]
        @test get_sector_model(270.0, train_result) == sector_models[4]
    end

    @testset "fill_missing_data" begin
        # Create test data with 10-minute intervals
        timestamps = collect(DateTime(2020,1,1):Minute(10):DateTime(2020,1,2))
        mast_df = DataFrame(
            timestamp = timestamps[1:end-1],  # Exclude the last timestamp to get 144 points
            ws_80m = vcat([10.0], fill(missing, 143)),  # 144 10-minute intervals in a day
            wd_80m = vcat([180.0], fill(missing, 143))
        )
        mast_ts = TimeSeriesData(mast_df, sensors)
        
        # Create meso data with 10-minute intervals - include all timestamps to match ensure_training_range
        meso_df = DataFrame(
            timestamp = timestamps,  # Include all timestamps
            ws_80m = collect(range(12.0, 11.0, length=145)),  # 145 points to include end timestamp
            wd_80m = collect(range(185.0, 184.0, length=145))  # 145 points to include end timestamp
        )
        meso_ts = TimeSeriesData(meso_df, sensors)
        
        # Create training results
        ws_results = Dict(
            :ws_80m => WindSpeedTrainResult(
                sensors[1], sensors[1], sensors[2],
                [WindSpeedSectorModel(0.0, 360.0, 1.0, 0.0)]
            )
        )
        wd_results = Dict(
            :wd_80m => WindDirectionTrainResult(
                sensors[2], sensors[2], 5.0
            )
        )
        
        time_range = TrainingTimeRange(DateTime(2020,1,1), DateTime(2020,1,2))
        
        # Test filling
        result = fill_missing_data(mast_ts, meso_ts, time_range, ws_results, wd_results)
        
        # Check results
        @test !any(ismissing, result.df.ws_80m)
        @test !any(ismissing, result.df.wd_80m)
        @test all(diff(result.df.timestamp) .== Minute(10))  # Verify 10-minute intervals
        
        # Check interpolation between hourly points
        for hour in 0:23
            # Get timestamps between this hour and next hour
            hour_start = DateTime(2020,1,1) + Hour(hour)
            hour_end = hour_start + Hour(1)
            
            # Get expected values at start and end of hour
            start_ws = 12.0 - (hour/24)  # Linear decrease from 12.0 to 11.0 over 24 hours
            end_ws = 12.0 - ((hour+1)/24)
            
            # Check points between hours
            mid_timestamps = result.df[result.df.timestamp .> hour_start .&& result.df.timestamp .< hour_end, :timestamp]
            @test length(mid_timestamps) == 5  # Should have 5 10-minute intervals between hours
            
            for ts in mid_timestamps
                # Calculate expected linear interpolation within this hour
                minutes_in = Dates.value(ts - hour_start) / (1000 * 60)  # Convert to minutes
                fraction = minutes_in / 60  # Fraction of hour completed
                expected_ws = start_ws + (end_ws - start_ws) * fraction
                
                # Test the value with small tolerance
                @test isapprox(result.df[result.df.timestamp .== ts, :ws_80m][1], expected_ws, atol=0.01)
            end
        end
    end

    @testset "fill_missing_data with extended range" begin
        # Create test data with 10-minute intervals for one day
        timestamps = collect(DateTime(2020,1,1):Minute(10):DateTime(2020,1,2))
        mast_df = DataFrame(
            timestamp = timestamps[1:end-1],  # Exclude the last timestamp to get 144 points
            ws_80m = vcat([10.0], fill(missing, 143)),
            wd_80m = vcat([180.0], fill(missing, 143))
        )
        sensors = [
            SensorColumn(:ws_80m, "ws_80m", "WindSpeed", "N", 80.0, "avg", "m/s")
            SensorColumn(:wd_80m, "wd_80m", "WindDirection", "N", 80.0, "avg", "deg")
        ]
        mast_ts = TimeSeriesData(mast_df, sensors)
        
        # Create meso data with wider range and 10-minute intervals - include all timestamps
        timestamps_extended = collect(DateTime(2019,12,31):Minute(10):DateTime(2020,1,3))
        meso_df = DataFrame(
            timestamp = timestamps_extended,  # Include all timestamps
            ws_80m = fill(12.0, length(timestamps_extended)),  # Include all points
            wd_80m = fill(185.0, length(timestamps_extended))
        )
        meso_ts = TimeSeriesData(meso_df, sensors)
        
        # Create time range that extends beyond mast data
        time_range = TrainingTimeRange(
            DateTime(2019,12,31),
            DateTime(2020,1,3)
        )
        
        # Create simple training results
        ws_results = Dict(
            :ws_80m => WindSpeedTrainResult(
                sensors[1], sensors[1], sensors[2],
                [WindSpeedSectorModel(0.0, 360.0, 1.0, 0.0)]
            )
        )
        wd_results = Dict(
            :wd_80m => WindDirectionTrainResult(
                sensors[2], sensors[2], 5.0
            )
        )
        
        # Test filling with extended range
        result = fill_missing_data(mast_ts, meso_ts, time_range, ws_results, wd_results)
        
        # Check results
        @test minimum(result.df.timestamp) == time_range.min
        @test maximum(result.df.timestamp) == time_range.max
        @test all(diff(result.df.timestamp) .== Minute(10))  # Verify 10-minute intervals
        @test !any(ismissing, result.df.ws_80m)
        @test !any(ismissing, result.df.wd_80m)
        
        # Additional checks for proper interpolation
        @test size(result.df, 1) == length(collect(time_range.min:Minute(10):time_range.max))  # Verify correct number of rows
    end
end

end 