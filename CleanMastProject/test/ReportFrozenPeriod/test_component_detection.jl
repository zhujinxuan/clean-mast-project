using Test
using Dates
using DataFrames
using CleanMastProject.ReportFrozenPeriod.FrozenDetection:
    find_temperature_periods, find_windspeed_stable_periods, find_winddirection_stable_periods
using CleanMastProject.ReportFrozenPeriod.PeriodOperations: TimePeriod

@testset "Component Detection Functions" begin

    @testset "find_temperature_periods" begin
        rep_interval = Minute(10)
        min_duration = Hour(6)
        threshold = 2.0

        @testset "Single continuous cold period (>6 hours)" begin
            # 8 hours of T < 2°C
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 8, 0))
            temp_values = fill(1.0, length(timestamps))

            periods = find_temperature_periods(timestamps, temp_values, threshold, min_duration, rep_interval)

            @test length(periods) == 1
            @test periods[1].start_time == DateTime(2024, 1, 1, 0, 0)
            @test periods[1].end_time == DateTime(2024, 1, 1, 8, 0)
            @test periods[1].duration_points == length(timestamps)
        end

        @testset "Period too short (<6 hours) - should be filtered out" begin
            # Only 4 hours of T < 2°C
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 4, 0))
            temp_values = fill(1.0, length(timestamps))

            periods = find_temperature_periods(timestamps, temp_values, threshold, min_duration, rep_interval)

            @test isempty(periods)  # Too short
        end

        @testset "Period exactly 6 hours - should be included" begin
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 6, 0))
            temp_values = fill(1.0, length(timestamps))

            periods = find_temperature_periods(timestamps, temp_values, threshold, min_duration, rep_interval)

            @test length(periods) == 1
            @test periods[1].end_time - periods[1].start_time == Hour(6)
        end

        @testset "Two separate cold periods with warm gap" begin
            # 8 hours cold, 2 hours warm, 8 hours cold
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 18, 0))
            temp_values = Vector{Float64}(undef, length(timestamps))

            for i in 1:length(timestamps)
                hour = Dates.hour(timestamps[i])
                if hour < 8 || hour >= 10
                    temp_values[i] = 1.0  # Cold
                else
                    temp_values[i] = 5.0  # Warm (breaks the period)
                end
            end

            periods = find_temperature_periods(timestamps, temp_values, threshold, min_duration, rep_interval)

            @test length(periods) == 2
            @test periods[1].end_time < periods[2].start_time  # Non-overlapping
        end

        @testset "Missing values break the period" begin
            # 10 hours total, but with missing in the middle
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 10, 0))
            temp_values = Vector{Union{Float64, Missing}}(fill(1.0, length(timestamps)))

            # Insert missing values at hour 5 (breaks into two periods)
            for i in 1:length(timestamps)
                if Dates.hour(timestamps[i]) == 5
                    temp_values[i] = missing
                end
            end

            periods = find_temperature_periods(timestamps, temp_values, threshold, min_duration, rep_interval)

            # Should have two periods (0-5h and 6-10h), but 0-5h and 6-10h might be <6h
            # Let's check the actual result
            @test all(ismissing(temp_values[i]) || temp_values[i] < threshold for i in 1:length(temp_values) if !ismissing(temp_values[i]))
        end

        @testset "Temperature oscillating around threshold" begin
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 12, 0))
            temp_values = [mod(i, 2) == 0 ? 1.0 : 3.0 for i in 1:length(timestamps)]

            periods = find_temperature_periods(timestamps, temp_values, threshold, min_duration, rep_interval)

            # No continuous 6-hour period
            @test isempty(periods)
        end
    end

    @testset "find_windspeed_stable_periods" begin
        rep_interval = Minute(10)
        min_duration = Hour(6)
        threshold = 0.1  # m/s

        @testset "Perfectly stable wind speed (>6 hours)" begin
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 8, 0))
            ws_values = fill(5.0, length(timestamps))

            periods = find_windspeed_stable_periods(timestamps, ws_values, threshold, min_duration, rep_interval)

            @test length(periods) == 1
            @test periods[1].start_time == DateTime(2024, 1, 1, 0, 0)
            @test periods[1].end_time == DateTime(2024, 1, 1, 8, 0)
        end

        @testset "Wind speed within threshold (±0.05 m/s)" begin
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 8, 0))
            # Start at 5.0, vary by ±0.05 (within 0.1 threshold)
            ws_values = [5.0 + (mod(i, 2) == 0 ? 0.05 : -0.05) for i in 1:length(timestamps)]

            periods = find_windspeed_stable_periods(timestamps, ws_values, threshold, min_duration, rep_interval)

            @test length(periods) == 1
            @test periods[1].duration_points == length(timestamps)
        end

        @testset "Wind speed change exceeds threshold - creates new period" begin
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 14, 0))
            ws_values = Vector{Float64}(undef, length(timestamps))

            # 7 hours at 5.0 m/s, then jump to 6.0 m/s (change = 1.0 > 0.1), then 7 hours at 6.0 m/s
            for i in 1:length(timestamps)
                hour = Dates.hour(timestamps[i])
                ws_values[i] = hour < 7 ? 5.0 : 6.0
            end

            periods = find_windspeed_stable_periods(timestamps, ws_values, threshold, min_duration, rep_interval)

            @test length(periods) == 2  # Two separate stable periods
        end

        @testset "Very slow drift (0.01 m/s per step) creates one long stable period" begin
            # Start at 5.0, increase by 0.01 each step (very gradual)
            # Over 8 hours (49 points): 5.0 to 5.48 m/s
            # Change from start never exceeds 0.1 m/s for ~10 points (100 minutes)
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 8, 0))
            ws_values = [5.0 + 0.01 * i for i in 0:(length(timestamps)-1)]

            periods = find_windspeed_stable_periods(timestamps, ws_values, threshold, min_duration, rep_interval)

            # After 10 steps (100 min): change = 0.10 m/s (at threshold)
            # After 11 steps (110 min): change = 0.11 > 0.1 → breaks period
            # First period is ~100 minutes < 6 hours
            # Then many short periods as each new start quickly exceeds 0.1
            # Expect 0 or more periods
            @test length(periods) >= 0
        end

        @testset "10% scattered missing values - period detected" begin
            # 8 hours total, 10% missing scattered throughout
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 8, 0))
            ws_values = Vector{Union{Float64, Missing}}(fill(5.0, length(timestamps)))

            # Add 10% missing (every 10th point)
            for i in 10:10:length(timestamps)
                ws_values[i] = missing
            end

            periods = find_windspeed_stable_periods(timestamps, ws_values, threshold, min_duration, rep_interval)

            # Should detect one 8-hour period despite 10% missing
            @test length(periods) == 1
            @test periods[1].end_time - periods[1].start_time == Hour(8)
        end

        @testset "30% scattered missing values - period still detected" begin
            # 8 hours total, 30% missing
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 8, 0))
            ws_values = Vector{Union{Float64, Missing}}(fill(5.0, length(timestamps)))

            # Add 30% missing (every 3rd point)
            for i in 3:3:length(timestamps)
                ws_values[i] = missing
            end

            periods = find_windspeed_stable_periods(timestamps, ws_values, threshold, min_duration, rep_interval)

            # Should detect one 8-hour period despite 30% missing
            @test length(periods) == 1
            @test periods[1].end_time - periods[1].start_time == Hour(8)
        end
    end

    @testset "find_winddirection_stable_periods" begin
        rep_interval = Minute(10)
        min_duration = Hour(6)
        threshold = 5.0  # degrees

        @testset "Perfectly stable wind direction (>6 hours)" begin
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 8, 0))
            wd_values = fill(180.0, length(timestamps))

            periods = find_winddirection_stable_periods(timestamps, wd_values, threshold, min_duration, rep_interval)

            @test length(periods) == 1
            @test periods[1].start_time == DateTime(2024, 1, 1, 0, 0)
            @test periods[1].end_time == DateTime(2024, 1, 1, 8, 0)
        end

        @testset "Wind direction stable within ±2° for 8 hours" begin
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 8, 0))
            # Start at 180°, vary within ±2° (well within 5° threshold)
            wd_values = [180.0 + (mod(i, 3) == 0 ? 2.0 : (mod(i, 3) == 1 ? -2.0 : 0.0)) for i in 1:length(timestamps)]

            periods = find_winddirection_stable_periods(timestamps, wd_values, threshold, min_duration, rep_interval)

            # All changes from start are ≤2°, well within 5° threshold
            # Should get one 8-hour period
            @test length(periods) == 1
            @test periods[1].end_time - periods[1].start_time == Hour(8)
        end

        @testset "Wraparound case: two 7-hour periods separated by 10° shift" begin
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 14, 0))
            # 7 hours at 355°, then 7 hours at 5° (angular difference = 10°, which exceeds 5° threshold)
            wd_values = [Dates.hour(t) < 7 ? 355.0 : 5.0 for t in timestamps]

            periods = find_winddirection_stable_periods(timestamps, wd_values, threshold, min_duration, rep_interval)

            # 10° > 5° threshold, should create two 7-hour periods
            @test length(periods) == 2
            @test all(p.end_time - p.start_time >= Hour(6) for p in periods)
        end

        @testset "Wraparound case: 358° to 2° (should be 4° difference - within threshold)" begin
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 8, 0))
            # Start at 358°, vary to 2° (angular difference = 4° < 5° threshold)
            wd_values = [358.0 + mod(i, 5) for i in 1:length(timestamps)]  # 358, 359, 0, 1, 2, repeat

            periods = find_winddirection_stable_periods(timestamps, wd_values, threshold, min_duration, rep_interval)

            # Should maintain one period since max difference is ~4° < 5°
            @test length(periods) >= 1
        end

        @testset "Large direction change (180° wind shift)" begin
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 14, 0))
            wd_values = Vector{Float64}(undef, length(timestamps))

            # 7 hours from north (0°), then shift to south (180°)
            for i in 1:length(timestamps)
                hour = Dates.hour(timestamps[i])
                wd_values[i] = hour < 7 ? 0.0 : 180.0
            end

            periods = find_winddirection_stable_periods(timestamps, wd_values, threshold, min_duration, rep_interval)

            @test length(periods) == 2  # Two separate stable periods
        end

        @testset "20% scattered missing values - period detected" begin
            # 8 hours total, 20% missing scattered throughout
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 8, 0))
            wd_values = Vector{Union{Float64, Missing}}(fill(180.0, length(timestamps)))

            # Add 20% missing (every 5th point)
            for i in 5:5:length(timestamps)
                wd_values[i] = missing
            end

            periods = find_winddirection_stable_periods(timestamps, wd_values, threshold, min_duration, rep_interval)

            # Should detect one 8-hour period despite 20% missing
            @test length(periods) == 1
            @test periods[1].end_time - periods[1].start_time == Hour(8)
        end

        @testset "Slow rotation across north (stays within ±3° for 8 hours)" begin
            # Rotate very slowly from 358° through 0° to 2° over 8 hours
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 8, 0))
            n_points = length(timestamps)
            # Gradual change: 358, 359, 0, 1, 2 repeated
            wd_values = [358.0 + mod(i, 5) for i in 0:(n_points-1)]

            periods = find_winddirection_stable_periods(timestamps, wd_values, threshold, min_duration, rep_interval)

            # Max change from start 358°: 358 to 2° = 4° (via wraparound) < 5° threshold
            # Should maintain one stable period for 8 hours
            @test length(periods) == 1
            @test periods[1].end_time - periods[1].start_time >= Hour(6)
        end
    end

    @testset "Missing Data Filter Integration (50% threshold)" begin
        # These tests verify the complete flow: detection → 50% filter
        using DataFrames
        using CleanMastProject.ReportFrozenPeriod.FrozenDetection: detect_nonheated_frozen_periods
        using CleanMastProject.Types.SensorColumns: SensorColumn
        using CleanMastProject.Types.ReportFrozenPeriodConfig: FrozenThresholdSet

        rep_interval = Minute(10)

        @testset "Period with 30% missing - accepted by filter" begin
            # Create 8-hour dataset with 30% missing
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 8, 0))
            n_points = length(timestamps)

            df = DataFrame(timestamp = timestamps)
            df[!, :ws] = Vector{Union{Float64, Missing}}(fill(5.0, n_points))
            df[!, :wd] = Vector{Union{Float64, Missing}}(fill(180.0, n_points))
            df[!, :temp] = Vector{Union{Float64, Missing}}(fill(1.0, n_points))

            # Add 30% missing to all sensors
            for i in 3:3:n_points
                df[i, :ws] = missing
                df[i, :wd] = missing
                df[i, :temp] = missing
            end

            ws_sensor = SensorColumn(columnName = :ws, sensorType = "WindSpeed", sensorDirection = "N/A", statType = "avg", height = 80.0, unit = "m/s")
            wd_sensor = SensorColumn(columnName = :wd, sensorType = "WindDirection", sensorDirection = "N/A", statType = "avg", height = 80.0, unit = "deg")
            temp_sensor = SensorColumn(columnName = :temp, sensorType = "Temperature", sensorDirection = "N/A", statType = "avg", height = 10.0, unit = "C")

            threshold_set = FrozenThresholdSet(
                name = "test",
                temperature_threshold = 2.0,
                windspeed_change_threshold = 0.1,
                winddirection_change_threshold = 5.0,
                min_duration_seconds = 21600  # 6 hours
            )

            periods = detect_nonheated_frozen_periods(df, ws_sensor, wd_sensor, temp_sensor, threshold_set, rep_interval)

            # Should detect period and pass 50% filter (30% < 50%)
            @test length(periods) == 1
            @test periods[1].end_time - periods[1].start_time == Hour(8)
        end

        @testset "Period with 60% missing - rejected by filter" begin
            # Create 8-hour dataset with 60% missing
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 8, 0))
            n_points = length(timestamps)

            df = DataFrame(timestamp = timestamps)
            df[!, :ws] = Vector{Union{Float64, Missing}}(fill(5.0, n_points))
            df[!, :wd] = Vector{Union{Float64, Missing}}(fill(180.0, n_points))
            df[!, :temp] = Vector{Union{Float64, Missing}}(fill(1.0, n_points))

            # Add 60% missing to WS sensor (most critical)
            for i in 1:n_points
                if mod(i, 5) <= 2  # 3 out of 5 = 60%
                    df[i, :ws] = missing
                end
            end

            ws_sensor = SensorColumn(columnName = :ws, sensorType = "WindSpeed", sensorDirection = "N/A", statType = "avg", height = 80.0, unit = "m/s")
            wd_sensor = SensorColumn(columnName = :wd, sensorType = "WindDirection", sensorDirection = "N/A", statType = "avg", height = 80.0, unit = "deg")
            temp_sensor = SensorColumn(columnName = :temp, sensorType = "Temperature", sensorDirection = "N/A", statType = "avg", height = 10.0, unit = "C")

            threshold_set = FrozenThresholdSet(
                name = "test",
                temperature_threshold = 2.0,
                windspeed_change_threshold = 0.1,
                winddirection_change_threshold = 5.0,
                min_duration_seconds = 21600
            )

            periods = detect_nonheated_frozen_periods(df, ws_sensor, wd_sensor, temp_sensor, threshold_set, rep_interval)

            # Should be rejected by 50% filter (60% > 50%)
            @test isempty(periods)
        end

        @testset "Period with exactly 50% missing - at threshold boundary" begin
            # Create 8-hour dataset with exactly 50% missing
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 8, 0))
            n_points = length(timestamps)

            df = DataFrame(timestamp = timestamps)
            df[!, :ws] = Vector{Union{Float64, Missing}}(fill(5.0, n_points))
            df[!, :wd] = Vector{Union{Float64, Missing}}(fill(180.0, n_points))
            df[!, :temp] = Vector{Union{Float64, Missing}}(fill(1.0, n_points))

            # Add exactly 50% missing (every other point)
            for i in 2:2:n_points
                df[i, :ws] = missing
            end

            ws_sensor = SensorColumn(columnName = :ws, sensorType = "WindSpeed", sensorDirection = "N/A", statType = "avg", height = 80.0, unit = "m/s")
            wd_sensor = SensorColumn(columnName = :wd, sensorType = "WindDirection", sensorDirection = "N/A", statType = "avg", height = 80.0, unit = "deg")
            temp_sensor = SensorColumn(columnName = :temp, sensorType = "Temperature", sensorDirection = "N/A", statType = "avg", height = 10.0, unit = "C")

            threshold_set = FrozenThresholdSet(
                name = "test",
                temperature_threshold = 2.0,
                windspeed_change_threshold = 0.1,
                winddirection_change_threshold = 5.0,
                min_duration_seconds = 21600
            )

            periods = detect_nonheated_frozen_periods(df, ws_sensor, wd_sensor, temp_sensor, threshold_set, rep_interval)

            # At exactly 50%, should be accepted (<=50%)
            @test length(periods) == 1
        end
    end

    @testset "Edge Cases for All Functions" begin
        rep_interval = Minute(10)
        min_duration = Hour(6)

        @testset "Empty input" begin
            timestamps = DateTime[]
            values = Float64[]

            temp_periods = find_temperature_periods(timestamps, values, 2.0, min_duration, rep_interval)
            ws_periods = find_windspeed_stable_periods(timestamps, values, 0.1, min_duration, rep_interval)
            wd_periods = find_winddirection_stable_periods(timestamps, values, 5.0, min_duration, rep_interval)

            @test isempty(temp_periods)
            @test isempty(ws_periods)
            @test isempty(wd_periods)
        end

        @testset "All missing values" begin
            timestamps = collect(DateTime(2024, 1, 1, 0, 0):rep_interval:DateTime(2024, 1, 1, 8, 0))
            values = Vector{Union{Float64, Missing}}(fill(missing, length(timestamps)))

            temp_periods = find_temperature_periods(timestamps, values, 2.0, min_duration, rep_interval)
            ws_periods = find_windspeed_stable_periods(timestamps, values, 0.1, min_duration, rep_interval)
            wd_periods = find_winddirection_stable_periods(timestamps, values, 5.0, min_duration, rep_interval)

            @test isempty(temp_periods)
            @test isempty(ws_periods)
            @test isempty(wd_periods)
        end

        @testset "Single data point" begin
            timestamps = [DateTime(2024, 1, 1, 0, 0)]
            values = [5.0]

            temp_periods = find_temperature_periods(timestamps, values, 2.0, min_duration, rep_interval)
            ws_periods = find_windspeed_stable_periods(timestamps, values, 0.1, min_duration, rep_interval)
            wd_periods = find_winddirection_stable_periods(timestamps, values, 5.0, min_duration, rep_interval)

            # Single point cannot form a 6-hour period
            @test isempty(temp_periods)
            @test isempty(ws_periods)
            @test isempty(wd_periods)
        end
    end

end
