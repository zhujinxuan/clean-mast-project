using Test
using DataFrames
using Dates
using CleanMastProject.ReconstructSingleMast.GroupByHour
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.SensorColumns: SensorColumn

"""
Generate multi-hour test data
"""
function generate_multi_hour_data(;
    n_hours::Int = 3,
    timestamps_per_hour::Int = 6
)
    all_timestamps = DateTime[]

    for hour in 0:(n_hours-1)
        hour_start = DateTime(2024,1,1,10+hour,0,0)
        hour_timestamps = hour_start:Minute(10):(hour_start + Minute(50))
        append!(all_timestamps, collect(hour_timestamps))
    end

    df = DataFrame(:timestamp => all_timestamps)
    df[!, :ws_100m] = rand(length(all_timestamps)) .* 10 .+ 5  # Random speeds 5-15 m/s

    return df
end

@testset "GroupByHour" begin
    @testset "process_by_hour - basic grouping" begin
        df = generate_multi_hour_data(n_hours = 3)

        sensors = [
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")
        ]

        data = TimeSeriesData(df, sensors)

        # Count hours processed
        hour_count = 0
        function count_hours(hour_data::TimeSeriesData)
            hour_count += 1
            return [hour_count]  # Return vector of results
        end

        results = process_by_hour(data, count_hours)

        @test length(results) == 3  # 3 hours
        @test results == [1, 2, 3]  # Each hour processed in order
    end

    @testset "process_by_hour - collect results" begin
        df = generate_multi_hour_data(n_hours = 2)

        sensors = [
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")
        ]

        data = TimeSeriesData(df, sensors)

        # Function that returns multiple results per hour
        function process_hour(hour_data::TimeSeriesData)
            n_rows = nrow(hour_data.df)
            return [i for i in 1:n_rows]  # Return 1, 2, 3, 4, 5, 6 for each hour
        end

        results = process_by_hour(data, process_hour)

        # Should have 6 results per hour * 2 hours = 12 results
        @test length(results) == 12
        @test results == [1, 2, 3, 4, 5, 6, 1, 2, 3, 4, 5, 6]
    end

    @testset "process_by_hour - verify hour data structure" begin
        df = generate_multi_hour_data(n_hours = 2)

        sensors = [
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")
        ]

        data = TimeSeriesData(df, sensors)

        hour_timestamps_collected = []

        function collect_timestamps(hour_data::TimeSeriesData)
            push!(hour_timestamps_collected, hour_data.df.timestamp)
            return [1]  # Return dummy result
        end

        process_by_hour(data, collect_timestamps)

        # Verify we got 2 hours
        @test length(hour_timestamps_collected) == 2

        # Each hour should have 6 timestamps
        @test all(length(ts) == 6 for ts in hour_timestamps_collected)

        # Verify timestamps are within correct hour
        for (i, timestamps) in enumerate(hour_timestamps_collected)
            expected_hour = 9 + i  # Hours 10 and 11 (0-indexed hour + 10)
            for ts in timestamps
                @test Dates.hour(ts) == expected_hour
            end
        end
    end

    @testset "process_by_hour - empty results" begin
        df = generate_multi_hour_data(n_hours = 2)

        sensors = [
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")
        ]

        data = TimeSeriesData(df, sensors)

        # Function that returns empty results
        function return_empty(hour_data::TimeSeriesData)
            return []
        end

        results = process_by_hour(data, return_empty)

        @test isempty(results)
    end

    @testset "process_by_hour - mixed empty and non-empty results" begin
        df = generate_multi_hour_data(n_hours = 3)

        sensors = [
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")
        ]

        data = TimeSeriesData(df, sensors)

        hour_counter = 0

        # Function that returns results only for odd hours
        function process_selective(hour_data::TimeSeriesData)
            hour_counter += 1
            if hour_counter % 2 == 1
                return [hour_counter]
            else
                return []
            end
        end

        results = process_by_hour(data, process_selective)

        # Should have results only from hours 1 and 3
        @test length(results) == 2
        @test results == [1, 3]
    end

    @testset "process_by_hour - sensors preserved" begin
        df = generate_multi_hour_data(n_hours = 2)

        sensors = [
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")
        ]

        data = TimeSeriesData(df, sensors)

        sensor_counts = []

        function count_sensors(hour_data::TimeSeriesData)
            push!(sensor_counts, length(hour_data.sensors))
            return [1]
        end

        process_by_hour(data, count_sensors)

        # Each hour should have the same sensors
        @test all(c == 1 for c in sensor_counts)
    end

    @testset "process_by_hour - single hour" begin
        # Test with data spanning only 1 hour
        timestamps = DateTime(2024,1,1,10,0,0):Minute(10):DateTime(2024,1,1,10,50,0)
        df = DataFrame(:timestamp => collect(timestamps))
        df[!, :ws_100m] = rand(6) .* 10 .+ 5

        sensors = [
            SensorColumn(:ws_100m, "WindSpeed", "N", 100.0, "avg", "m/s")
        ]

        data = TimeSeriesData(df, sensors)

        processed_count = 0

        function count_processing(hour_data::TimeSeriesData)
            processed_count += 1
            return [nrow(hour_data.df)]
        end

        results = process_by_hour(data, count_processing)

        @test processed_count == 1  # Only 1 hour
        @test results == [6]  # 6 timestamps in that hour
    end
end
