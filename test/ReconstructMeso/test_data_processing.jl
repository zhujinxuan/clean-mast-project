module TestDataProcessing

using Test
using Dates
using DataFrames
using Statistics
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, SensorColumn
using CleanMastProject.Types.ReconstructMeso: TrainingTimeRange
using CleanMastProject.Types.CleanMastConfig: TimeRange
using CleanMastProject.ReconstructMeso.DataProcessing: ensure_complete_timeseries, 
    prepare_timeseries, average_timeseries, find_nearest_height_sensor, 
    calculate_training_timerange

@testset "DataProcessing" begin
    # Create test data
    timestamps = collect(DateTime(2024,1,1):Hour(1):DateTime(2024,1,2))
    ws_data = [5.0, 6.0, missing, 7.0, 8.0, 6.0, missing, 5.0, 
              4.0, 7.0, missing, 8.0, 6.0, missing, 7.0, 5.0, 
              6.0, 7.0, missing, 8.0, 5.0, 6.0, missing, 7.0, 8.0]
    wd_data = [180.0, 185.0, missing, 190.0, 195.0, 180.0, missing, 185.0,
              190.0, 185.0, missing, 180.0, 185.0, missing, 190.0, 185.0,
              180.0, 185.0, missing, 190.0, 185.0, 180.0, missing, 185.0, 190.0]
    
    df = DataFrame(
        timestamp = timestamps,
        ws_80m = ws_data,
        wd_80m = wd_data
    )
    
    sensors = [
        SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s"),
        SensorColumn(:wd_80m, "WindDirection", "N", 80.0, "avg", "deg")
    ]
    
    ts = TimeSeriesData(df, sensors)
    time_range = TrainingTimeRange(DateTime(2024,1,1,2), DateTime(2024,1,1,22))

    @testset "ensure_complete_timeseries" begin
        # Test 10-minute completion
        completed = ensure_complete_timeseries(ts, time_range, Minute(10))
        @test size(completed.df, 1) == 121  # 20 hours * 6 10-min intervals + 1
        @test completed.sensors == sensors
        @test all(diff(completed.df.timestamp) .== Minute(10))
        
        # Test hourly completion
        completed_hourly = ensure_complete_timeseries(ts, time_range, Hour(1))
        @test size(completed_hourly.df, 1) == 21  # 20 hours + 1
        @test all(diff(completed_hourly.df.timestamp) .== Hour(1))
    end

    @testset "prepare_timeseries" begin
        prepared = prepare_timeseries(ts, time_range, Minute(10))
        @test issorted(prepared.df.timestamp)
        @test first(prepared.df.timestamp) == DateTime(2024,1,1,2)
        @test last(prepared.df.timestamp) == DateTime(2024,1,1,22)
    end

    @testset "find_nearest_height_sensor" begin
        sensors_multi = [
            SensorColumn(:ws_60m, "WindSpeed", "N", 60.0, "avg", "m/s"),
            SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s"),
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")
        ]
        
        # Test exact match
        @test find_nearest_height_sensor(80.0, sensors_multi, "WindSpeed").height == 80.0
        
        # Test nearest match
        @test find_nearest_height_sensor(85.0, sensors_multi, "WindSpeed").height == 80.0
        @test find_nearest_height_sensor(95.0, sensors_multi, "WindSpeed").height == 100.0
        
        # Test no match
        @test isnothing(find_nearest_height_sensor(80.0, sensors_multi, "Temperature"))
    end

    @testset "calculate_training_timerange" begin
        # Test with no time range specified
        input_range = TimeRange(nothing, nothing)
        result = calculate_training_timerange(ts, input_range)
        @test result isa TrainingTimeRange
        @test result.min == DateTime(2023,1,1)
        @test result.max == DateTime(2024,1,1) - Second(1)

        # Test with specified min
        input_range = TimeRange(DateTime(2024,1,1), nothing)
        result = calculate_training_timerange(ts, input_range)
        @test result.min == DateTime(2024,1,1)
        @test result.max == DateTime(2025,1,1) - Second(1)

        # Test with specified max
        input_range = TimeRange(nothing, DateTime(2024,1,2))
        result = calculate_training_timerange(ts, input_range)
        @test result.max == DateTime(2024,1,2)
        @test result.min == DateTime(2023,1,1)

        # Test with both specified
        input_range = TimeRange(DateTime(2024,1,1), DateTime(2024,1,2))
        result = calculate_training_timerange(ts, input_range)
        @test result.min == DateTime(2024,1,1)
        @test result.max == DateTime(2024,1,2)
    end

    @testset "average_timeseries with annual pattern" begin
        # Parameters for wind speed pattern
        n_days = 365
        n_hours = 24 * n_days
        base_wind = 8.0  # base wind speed
        amplitude = 2.0  # seasonal variation amplitude
        w = 2π / (365 * 24)  # angular frequency (per hour)
        noise_amplitude = 1.0  # random noise amplitude
        
        # Generate timestamps
        timestamps = collect(DateTime(2024,1,1):Hour(1):DateTime(2024,1,1) + Hour(n_hours-1))
        
        # Generate time indices (in hours)
        t = 0.0:(n_hours-1)
        
        # Generate wind speeds: base + seasonal + noise
        ws_data = Vector{Union{Missing,Float64}}(undef, n_hours)
        ws_data .= base_wind .+ amplitude .* sin.(w .* t) .+ (rand(n_hours) .- 0.5) .* 2 .* noise_amplitude
        
        # Add 5% missing values randomly
        missing_indices = rand(1:n_hours, round(Int, n_hours * 0.05))
        ws_data[missing_indices] .= missing
        
        df = DataFrame(
            timestamp = timestamps,
            ws_80m = ws_data
        )
        
        sensors = [
            SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s")
        ]
        
        ts = TimeSeriesData(df, sensors)
        full_range = TrainingTimeRange(DateTime(2024,1,1), DateTime(2024,1,1) + Day(n_days))
        
        # Get 15-day averages for the entire period
        averaged = average_timeseries(ts, full_range, Day(15))
        
        # For each 15-day period in the averaged data
        for i in 1:(size(averaged.df, 1)-1)
            period_start = averaged.df[i, :timestamp]
            
            # Calculate theoretical mean for this period
            t_start = (period_start - DateTime(2024,1,1)).value ÷ (1000 * 3600)  # hours since start (value is in milliseconds)
            t_period = t_start:(t_start + 24*15 - 1)
            
            # Theoretical mean (without noise, as noise should average to ~0)
            theoretical_mean = base_wind + amplitude * mean(sin.(w .* t_period))
            
            # Test that average is within 0.1 m/s of theoretical mean
            # (allowing for some deviation due to noise and missing values)
            @test !ismissing(averaged.df[i, :ws_80m])
            @test abs(averaged.df[i, :ws_80m] - theoretical_mean) < 0.1
            
            # Print for verification
            @info "Period starting $(period_start)" theoretical=theoretical_mean actual=averaged.df[i, :ws_80m]
        end
    end

    @testset "average_timeseries with high missing ratio" begin
        # Use same parameters as annual pattern test
        n_days = 360
        n_hours = 24 * n_days
        base_wind = 8.0
        amplitude = 2.0
        w = 2π / (365 * 24)
        
        # Generate base data
        timestamps = collect(DateTime(2024,1,1):Hour(1):DateTime(2024,1,1) + Hour(n_hours-1))
        t = 0.0:(n_hours-1)
        ws_data = base_wind .+ amplitude .* sin.(w .* t)
        
        # Create DataFrame
        df = DataFrame(
            timestamp = timestamps,
            ws_80m = Vector{Union{Missing, Float64}}(ws_data)
        )
        
        sensors = [
            SensorColumn(:ws_80m, "WindSpeed", "N", 80.0, "avg", "m/s")
        ]
        
        # Set 50% of values to missing in 12th and 13th 15-day periods (days 165-179)
        period_12_start = DateTime(2024,1,1) + Day(165)  # (11 * 15) 
        period_12_end = period_12_start + Day(15)
        
        # Find all indices in the period range
        period_indices = findall(t -> period_12_start <= t < period_12_end, timestamps)
        # Randomly select 50% of indices to set as missing
        indices_to_set_missing = period_indices[rand(Bool, length(period_indices))]
        
        df[indices_to_set_missing, :ws_80m] .= missing
        
        ts = TimeSeriesData(df, sensors)
        
        # Test averaging over the full period
        full_range = TrainingTimeRange(DateTime(2024,1,1), DateTime(2024,1,1) + Day(n_days))
        averaged = average_timeseries(ts, full_range, Day(15))
        
        # Find the 12th period in the averaged results
        period_12_idx = findfirst(t -> t == DateTime(2024,1,1) + Day(165), averaged.df.timestamp)
        
        # Test that these periods are missing
        @test ismissing(averaged.df[period_12_idx, :ws_80m])
        
        # Test that other periods are not missing
        @test !ismissing(averaged.df[period_12_idx-1, :ws_80m])  # period 11
        
        # Print for verification
        @info "Periods 11-14" begin
            period_11=averaged.df[period_12_idx-1, :ws_80m]
            period_12=averaged.df[period_12_idx, :ws_80m]
        end
    end
end

end 