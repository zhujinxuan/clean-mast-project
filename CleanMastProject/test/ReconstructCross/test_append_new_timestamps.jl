"""
    test_append_new_timestamps.jl

Comprehensive test suite for append_new_timestamps helper function.
Tests time range extension behavior in cross-mast reconstruction.
"""

using Test
using DataFrames
using Dates
using Random

using CleanMastProject.ReconstructCross.ProcessReconstructCrossCommand: append_new_timestamps, merge_reconstruction_data
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.SensorColumns: SensorColumn

function create_mock_timeseries_data(
    timestamps::Vector{DateTime},
    sensor_heights::Vector{Float64},
    fill_values::Bool = true
)::TimeSeriesData
    df = DataFrame(:timestamp => timestamps)

    sensors = SensorColumn[]
    for height in sensor_heights
        col_name = Symbol("WS_$(Int(height))m")
        if fill_values
            df[!, col_name] = rand(length(timestamps)) .* 10.0
        else
            df[!, col_name] = missings(Float64, length(timestamps))
        end

        push!(sensors, SensorColumn(
            columnName = col_name,
            sensorType = "WindSpeed",
            statType = "avg",
            height = height,
            sensorDirection = "N/A",
            unit = "m/s"
        ))
    end

    return TimeSeriesData(df, sensors)
end

function hourly_timestamps(start_date::Date, end_date::Date)::Vector{DateTime}
    start_dt = DateTime(start_date)
    end_dt = DateTime(end_date) + Hour(23)
    return collect(start_dt:Hour(1):end_dt)
end

function verify_sorted(df::DataFrame)::Bool
    return issorted(df.timestamp)
end

function count_all_missing_rows(df::DataFrame, sensor_columns::Vector{Symbol})::Int
    count = 0
    for row in eachrow(df)
        if all(ismissing(row[col]) for col in sensor_columns)
            count += 1
        end
    end
    return count
end

@testset "append_new_timestamps Tests" begin

    @testset "Basic Functionality" begin

        @testset "No New Timestamps (Complete Overlap)" begin
            timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:23]

            target_df = DataFrame(
                timestamp = timestamps,
                WS_80m = rand(24) .* 10.0
            )
            reconstructed_df = DataFrame(
                timestamp = timestamps,
                WS_80m = rand(24) .* 10.0
            )

            sensor = SensorColumn(
                columnName = :WS_80m,
                sensorType = "WindSpeed",
                statType = "avg",
                height = 80.0,
                sensorDirection = "N/A",
                unit = "m/s"
            )

            target_ts = TimeSeriesData(target_df, [sensor])
            reconstructed_ts = TimeSeriesData(reconstructed_df, [sensor])

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test nrow(result) == nrow(target_df)
            @test all(result.timestamp .== target_df.timestamp)
            @test all(result.WS_80m .== target_df.WS_80m)
        end

        @testset "New Timestamps at End (Time Extension)" begin
            target_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:23]
            reconstructed_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:71]

            target_df = DataFrame(
                timestamp = target_timestamps,
                WS_80m = rand(24) .* 10.0
            )
            reconstructed_df = DataFrame(
                timestamp = reconstructed_timestamps,
                WS_80m = rand(72) .* 10.0
            )

            sensor = SensorColumn(
                columnName = :WS_80m,
                sensorType = "WindSpeed",
                statType = "avg",
                height = 80.0,
                sensorDirection = "N/A",
                unit = "m/s"
            )

            target_ts = TimeSeriesData(target_df, [sensor])
            reconstructed_ts = TimeSeriesData(reconstructed_df, [sensor])

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test nrow(result) == 72
            @test issorted(result.timestamp)
            @test result.timestamp[1:24] == target_timestamps
            @test all(result.WS_80m[1:24] .== target_df.WS_80m)
            @test all(ismissing.(result.WS_80m[25:72]))
        end

        @testset "New Timestamps at Beginning (Backward Extension)" begin
            target_timestamps = [DateTime(2024,1,2) + Hour(i) for i in 0:47]
            reconstructed_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:71]

            target_df = DataFrame(
                timestamp = target_timestamps,
                WS_80m = rand(48) .* 10.0
            )
            reconstructed_df = DataFrame(
                timestamp = reconstructed_timestamps,
                WS_80m = rand(72) .* 10.0
            )

            sensor = SensorColumn(
                columnName = :WS_80m,
                sensorType = "WindSpeed",
                statType = "avg",
                height = 80.0,
                sensorDirection = "N/A",
                unit = "m/s"
            )

            target_ts = TimeSeriesData(target_df, [sensor])
            reconstructed_ts = TimeSeriesData(reconstructed_df, [sensor])

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test nrow(result) == 72
            @test issorted(result.timestamp)
            @test all(ismissing.(result.WS_80m[1:24]))

            target_data_indices = findall(t -> t in target_timestamps, result.timestamp)
            @test length(target_data_indices) == 48
            @test all(.!ismissing.(result.WS_80m[target_data_indices]))
        end

        @testset "Bidirectional Extension (Both Ends)" begin
            target_timestamps = [DateTime(2024,1,2) + Hour(i) for i in 0:47]
            reconstructed_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:95]

            target_df = DataFrame(
                timestamp = target_timestamps,
                WS_80m = rand(48) .* 10.0
            )
            reconstructed_df = DataFrame(
                timestamp = reconstructed_timestamps,
                WS_80m = rand(96) .* 10.0
            )

            sensor = SensorColumn(
                columnName = :WS_80m,
                sensorType = "WindSpeed",
                statType = "avg",
                height = 80.0,
                sensorDirection = "N/A",
                unit = "m/s"
            )

            target_ts = TimeSeriesData(target_df, [sensor])
            reconstructed_ts = TimeSeriesData(reconstructed_df, [sensor])

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test nrow(result) == 96
            @test issorted(result.timestamp)

            target_data_indices = findall(t -> t in target_timestamps, result.timestamp)
            new_data_indices = findall(t -> !(t in target_timestamps), result.timestamp)

            @test length(target_data_indices) == 48
            @test length(new_data_indices) == 48
            @test all(.!ismissing.(result.WS_80m[target_data_indices]))
            @test all(ismissing.(result.WS_80m[new_data_indices]))
        end

        @testset "Sparse New Timestamps (Gap Filling)" begin
            target_timestamps = [DateTime(2024,1,1), DateTime(2024,1,3), DateTime(2024,1,5)]
            reconstructed_timestamps = [DateTime(2024,1,1) + Day(i) for i in 0:4]

            target_df = DataFrame(
                timestamp = target_timestamps,
                WS_80m = [5.0, 7.0, 9.0]
            )
            reconstructed_df = DataFrame(
                timestamp = reconstructed_timestamps,
                WS_80m = rand(5) .* 10.0
            )

            sensor = SensorColumn(
                columnName = :WS_80m,
                sensorType = "WindSpeed",
                statType = "avg",
                height = 80.0,
                sensorDirection = "N/A",
                unit = "m/s"
            )

            target_ts = TimeSeriesData(target_df, [sensor])
            reconstructed_ts = TimeSeriesData(reconstructed_df, [sensor])

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test nrow(result) == 5
            @test issorted(result.timestamp)
            @test all(result.timestamp .== reconstructed_timestamps)

            @test result[result.timestamp .== DateTime(2024,1,1), :WS_80m][1] == 5.0
            @test result[result.timestamp .== DateTime(2024,1,3), :WS_80m][1] == 7.0
            @test result[result.timestamp .== DateTime(2024,1,5), :WS_80m][1] == 9.0

            @test ismissing(result[result.timestamp .== DateTime(2024,1,2), :WS_80m][1])
            @test ismissing(result[result.timestamp .== DateTime(2024,1,4), :WS_80m][1])
        end
    end

    @testset "Sensor Column Handling" begin

        @testset "Multiple Sensor Columns" begin
            target_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:23]
            reconstructed_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:47]

            target_df = DataFrame(
                timestamp = target_timestamps,
                WS_80m = rand(24) .* 10.0,
                WS_100m = rand(24) .* 11.0,
                WD_80m = rand(24) .* 360.0
            )
            reconstructed_df = DataFrame(
                timestamp = reconstructed_timestamps,
                WS_80m = rand(48) .* 10.0,
                WS_100m = rand(48) .* 11.0,
                WD_80m = rand(48) .* 360.0
            )

            sensors = [
                SensorColumn(columnName=:WS_80m, sensorType="WindSpeed", statType="avg", height=80.0, sensorDirection="N/A", unit="m/s"),
                SensorColumn(columnName=:WS_100m, sensorType="WindSpeed", statType="avg", height=100.0, sensorDirection="N/A", unit="m/s"),
                SensorColumn(columnName=:WD_80m, sensorType="WindDirection", statType="avg", height=80.0, sensorDirection="N/A", unit="deg")
            ]

            target_ts = TimeSeriesData(target_df, sensors)
            reconstructed_ts = TimeSeriesData(reconstructed_df, sensors)

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test nrow(result) == 48
            @test propertynames(result) == [:timestamp, :WS_80m, :WS_100m, :WD_80m]

            @test all(ismissing.(result.WS_80m[25:48]))
            @test all(ismissing.(result.WS_100m[25:48]))
            @test all(ismissing.(result.WD_80m[25:48]))
        end

        @testset "Different Sensor Heights" begin
            timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:23]
            extended_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:47]

            target_df = DataFrame(
                timestamp = timestamps,
                WS_10m = rand(24) .* 8.0,
                WS_50m = rand(24) .* 10.0,
                WS_80m = rand(24) .* 11.0
            )
            reconstructed_df = DataFrame(
                timestamp = extended_timestamps,
                WS_10m = rand(48) .* 8.0,
                WS_50m = rand(48) .* 10.0,
                WS_80m = rand(48) .* 11.0
            )

            sensors = [
                SensorColumn(columnName=:WS_10m, sensorType="WindSpeed", statType="avg", height=10.0, sensorDirection="N/A", unit="m/s"),
                SensorColumn(columnName=:WS_50m, sensorType="WindSpeed", statType="avg", height=50.0, sensorDirection="N/A", unit="m/s"),
                SensorColumn(columnName=:WS_80m, sensorType="WindSpeed", statType="avg", height=80.0, sensorDirection="N/A", unit="m/s")
            ]

            target_ts = TimeSeriesData(target_df, sensors)
            reconstructed_ts = TimeSeriesData(reconstructed_df, sensors)

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test nrow(result) == 48
            @test all(propertynames(result) .== [:timestamp, :WS_10m, :WS_50m, :WS_80m])
        end
    end

    @testset "Edge Cases" begin

        @testset "Empty Target DataFrame" begin
            target_df = DataFrame(timestamp = DateTime[], WS_80m = Union{Missing, Float64}[])
            reconstructed_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:23]
            reconstructed_df = DataFrame(
                timestamp = reconstructed_timestamps,
                WS_80m = rand(24) .* 10.0
            )

            sensor = SensorColumn(
                columnName = :WS_80m,
                sensorType = "WindSpeed",
                statType = "avg",
                height = 80.0,
                sensorDirection = "N/A",
                unit = "m/s"
            )

            target_ts = TimeSeriesData(target_df, [sensor])
            reconstructed_ts = TimeSeriesData(reconstructed_df, [sensor])

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test nrow(result) == 24
            @test all(ismissing.(result.WS_80m))
        end

        @testset "Empty Reconstructed DataFrame" begin
            target_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:23]
            target_df = DataFrame(
                timestamp = target_timestamps,
                WS_80m = rand(24) .* 10.0
            )
            reconstructed_df = DataFrame(timestamp = DateTime[], WS_80m = Union{Missing, Float64}[])

            sensor = SensorColumn(
                columnName = :WS_80m,
                sensorType = "WindSpeed",
                statType = "avg",
                height = 80.0,
                sensorDirection = "N/A",
                unit = "m/s"
            )

            target_ts = TimeSeriesData(target_df, [sensor])
            reconstructed_ts = TimeSeriesData(reconstructed_df, [sensor])

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test nrow(result) == 24
            @test all(result.timestamp .== target_df.timestamp)
            @test all(result.WS_80m .== target_df.WS_80m)
        end

        @testset "Single Timestamp Difference" begin
            target_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:23]
            reconstructed_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:24]

            target_df = DataFrame(
                timestamp = target_timestamps,
                WS_80m = rand(24) .* 10.0
            )
            reconstructed_df = DataFrame(
                timestamp = reconstructed_timestamps,
                WS_80m = rand(25) .* 10.0
            )

            sensor = SensorColumn(
                columnName = :WS_80m,
                sensorType = "WindSpeed",
                statType = "avg",
                height = 80.0,
                sensorDirection = "N/A",
                unit = "m/s"
            )

            target_ts = TimeSeriesData(target_df, [sensor])
            reconstructed_ts = TimeSeriesData(reconstructed_df, [sensor])

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test nrow(result) == 25
            @test result.timestamp[25] == DateTime(2024,1,2)
            @test ismissing(result.WS_80m[25])
        end

        @testset "Identical Timestamps (Set Deduplication)" begin
            timestamps = [DateTime(2024,1,1), DateTime(2024,1,2), DateTime(2024,1,3)]

            target_df = DataFrame(
                timestamp = timestamps,
                WS_80m = [5.0, 7.0, 9.0]
            )
            reconstructed_df = DataFrame(
                timestamp = timestamps,
                WS_80m = [6.0, 8.0, 10.0]
            )

            sensor = SensorColumn(
                columnName = :WS_80m,
                sensorType = "WindSpeed",
                statType = "avg",
                height = 80.0,
                sensorDirection = "N/A",
                unit = "m/s"
            )

            target_ts = TimeSeriesData(target_df, [sensor])
            reconstructed_ts = TimeSeriesData(reconstructed_df, [sensor])

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test nrow(result) == 3
            @test all(result.WS_80m .== target_df.WS_80m)
        end

        @testset "Unsorted Input Timestamps" begin
            target_timestamps = [DateTime(2024,1,3), DateTime(2024,1,1), DateTime(2024,1,2)]
            reconstructed_timestamps = [DateTime(2024,1,5), DateTime(2024,1,4), DateTime(2024,1,1), DateTime(2024,1,2), DateTime(2024,1,3)]

            target_df = DataFrame(
                timestamp = target_timestamps,
                WS_80m = [30.0, 10.0, 20.0]
            )
            reconstructed_df = DataFrame(
                timestamp = reconstructed_timestamps,
                WS_80m = [50.0, 40.0, 15.0, 25.0, 35.0]
            )

            sensor = SensorColumn(
                columnName = :WS_80m,
                sensorType = "WindSpeed",
                statType = "avg",
                height = 80.0,
                sensorDirection = "N/A",
                unit = "m/s"
            )

            target_ts = TimeSeriesData(target_df, [sensor])
            reconstructed_ts = TimeSeriesData(reconstructed_df, [sensor])

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test nrow(result) == 5
            @test issorted(result.timestamp)
            @test result.timestamp == [DateTime(2024,1,i) for i in 1:5]

            @test result[result.timestamp .== DateTime(2024,1,1), :WS_80m][1] == 10.0
            @test result[result.timestamp .== DateTime(2024,1,2), :WS_80m][1] == 20.0
            @test result[result.timestamp .== DateTime(2024,1,3), :WS_80m][1] == 30.0
            @test ismissing(result[result.timestamp .== DateTime(2024,1,4), :WS_80m][1])
            @test ismissing(result[result.timestamp .== DateTime(2024,1,5), :WS_80m][1])
        end

        @testset "Non-Sensor Columns Preservation" begin
            target_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:23]
            reconstructed_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:47]

            target_df = DataFrame(
                timestamp = target_timestamps,
                WS_80m = rand(24) .* 10.0,
                Battery_V = rand(24) .* 12.0 .+ 11.0
            )
            reconstructed_df = DataFrame(
                timestamp = reconstructed_timestamps,
                WS_80m = rand(48) .* 10.0,
                Battery_V = rand(48) .* 12.0 .+ 11.0
            )

            sensor = SensorColumn(
                columnName = :WS_80m,
                sensorType = "WindSpeed",
                statType = "avg",
                height = 80.0,
                sensorDirection = "N/A",
                unit = "m/s"
            )

            target_ts = TimeSeriesData(target_df, [sensor])
            reconstructed_ts = TimeSeriesData(reconstructed_df, [sensor])

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test nrow(result) == 48
            @test :Battery_V in propertynames(result)
            @test all(.!ismissing.(result.Battery_V[1:24]))
            @test all(ismissing.(result.Battery_V[25:48]))
        end
    end

    @testset "Data Type Validation" begin

        @testset "Timestamp Types" begin
            timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:23]
            extended_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:47]

            target_df = DataFrame(timestamp = timestamps, WS_80m = rand(24) .* 10.0)
            reconstructed_df = DataFrame(timestamp = extended_timestamps, WS_80m = rand(48) .* 10.0)

            sensor = SensorColumn(
                columnName = :WS_80m,
                sensorType = "WindSpeed",
                statType = "avg",
                height = 80.0,
                sensorDirection = "N/A",
                unit = "m/s"
            )

            target_ts = TimeSeriesData(target_df, [sensor])
            reconstructed_ts = TimeSeriesData(reconstructed_df, [sensor])

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test all(t -> t isa DateTime, result.timestamp)
            @test !any(ismissing, result.timestamp)
        end

        @testset "Sensor Value Types" begin
            timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:23]
            extended_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:47]

            target_df = DataFrame(timestamp = timestamps, WS_80m = rand(24) .* 10.0)
            reconstructed_df = DataFrame(timestamp = extended_timestamps, WS_80m = rand(48) .* 10.0)

            sensor = SensorColumn(
                columnName = :WS_80m,
                sensorType = "WindSpeed",
                statType = "avg",
                height = 80.0,
                sensorDirection = "N/A",
                unit = "m/s"
            )

            target_ts = TimeSeriesData(target_df, [sensor])
            reconstructed_ts = TimeSeriesData(reconstructed_df, [sensor])

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test eltype(result.WS_80m) == Union{Missing, Float64}
        end

        @testset "DataFrame Structure" begin
            timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:23]
            extended_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:47]

            target_df = DataFrame(
                timestamp = timestamps,
                WS_80m = rand(24) .* 10.0,
                WD_80m = rand(24) .* 360.0
            )
            reconstructed_df = DataFrame(
                timestamp = extended_timestamps,
                WS_80m = rand(48) .* 10.0,
                WD_80m = rand(48) .* 360.0
            )

            sensors = [
                SensorColumn(columnName=:WS_80m, sensorType="WindSpeed", statType="avg", height=80.0, sensorDirection="N/A", unit="m/s"),
                SensorColumn(columnName=:WD_80m, sensorType="WindDirection", statType="avg", height=80.0, sensorDirection="N/A", unit="deg")
            ]

            target_ts = TimeSeriesData(target_df, sensors)
            reconstructed_ts = TimeSeriesData(reconstructed_df, sensors)

            result = append_new_timestamps(target_ts, reconstructed_ts)

            @test propertynames(result) == propertynames(target_df)
            @test :timestamp == propertynames(result)[1]
        end
    end

    @testset "Integration Tests" begin

        @testset "End-to-End Time Extension with merge_reconstruction_data" begin
            target_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:23]
            reconstructed_timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:95]

            Random.seed!(123)
            target_speeds = Vector{Union{Missing, Float64}}(rand(24) .* 10.0)
            target_speeds[5:8] .= missing

            reconstructed_speeds = rand(96) .* 10.0

            target_df = DataFrame(timestamp = target_timestamps, WS_80m = target_speeds)
            reconstructed_df = DataFrame(timestamp = reconstructed_timestamps, WS_80m = reconstructed_speeds)

            sensor = SensorColumn(
                columnName = :WS_80m,
                sensorType = "WindSpeed",
                statType = "avg",
                height = 80.0,
                sensorDirection = "N/A",
                unit = "m/s"
            )

            target_ts = TimeSeriesData(target_df, [sensor])
            reconstructed_ts = TimeSeriesData(reconstructed_df, [sensor])

            merged_ts = merge_reconstruction_data(target_ts, reconstructed_ts)

            @test nrow(merged_ts.df) == 96
            @test issorted(merged_ts.df.timestamp)

            @test all(.!ismissing.(merged_ts.df.WS_80m[1:4]))
            @test all(.!ismissing.(merged_ts.df.WS_80m[5:8]))
            @test all(.!ismissing.(merged_ts.df.WS_80m[9:24]))
        end

        @testset "Preserves Existing Target Data" begin
            target_timestamps = [DateTime(2024,1,1), DateTime(2024,1,2), DateTime(2024,1,3)]
            reconstructed_timestamps = [DateTime(2024,1,1), DateTime(2024,1,2), DateTime(2024,1,3), DateTime(2024,1,4), DateTime(2024,1,5)]

            target_df = DataFrame(
                timestamp = target_timestamps,
                WS_80m = [5.5, 7.5, 9.5]
            )
            reconstructed_df = DataFrame(
                timestamp = reconstructed_timestamps,
                WS_80m = [6.0, 8.0, 10.0, 12.0, 14.0]
            )

            sensor = SensorColumn(
                columnName = :WS_80m,
                sensorType = "WindSpeed",
                statType = "avg",
                height = 80.0,
                sensorDirection = "N/A",
                unit = "m/s"
            )

            target_ts = TimeSeriesData(target_df, [sensor])
            reconstructed_ts = TimeSeriesData(reconstructed_df, [sensor])

            merged_ts = merge_reconstruction_data(target_ts, reconstructed_ts)

            @test merged_ts.df[merged_ts.df.timestamp .== DateTime(2024,1,1), :WS_80m][1] == 5.5
            @test merged_ts.df[merged_ts.df.timestamp .== DateTime(2024,1,2), :WS_80m][1] == 7.5
            @test merged_ts.df[merged_ts.df.timestamp .== DateTime(2024,1,3), :WS_80m][1] == 9.5
            @test merged_ts.df[merged_ts.df.timestamp .== DateTime(2024,1,4), :WS_80m][1] == 12.0
            @test merged_ts.df[merged_ts.df.timestamp .== DateTime(2024,1,5), :WS_80m][1] == 14.0
        end
    end
end

@testset "Helper Function Tests" begin

    @testset "create_mock_timeseries_data" begin
        timestamps = [DateTime(2024,1,1) + Hour(i) for i in 0:23]
        sensor_heights = [80.0, 100.0]

        ts = create_mock_timeseries_data(timestamps, sensor_heights, true)

        @test nrow(ts.df) == 24
        @test length(ts.sensors) == 2
        @test all(ts.sensors[1].height == 80.0)
        @test all(ts.sensors[2].height == 100.0)
        @test all(.!ismissing.(ts.df.WS_80m))
        @test all(.!ismissing.(ts.df.WS_100m))
    end

    @testset "hourly_timestamps" begin
        timestamps = hourly_timestamps(Date(2024,1,1), Date(2024,1,2))

        @test length(timestamps) == 48
        @test timestamps[1] == DateTime(2024,1,1,0,0,0)
        @test timestamps[end] == DateTime(2024,1,2,23,0,0)
    end

    @testset "verify_sorted" begin
        sorted_df = DataFrame(timestamp = [DateTime(2024,1,1), DateTime(2024,1,2), DateTime(2024,1,3)])
        unsorted_df = DataFrame(timestamp = [DateTime(2024,1,3), DateTime(2024,1,1), DateTime(2024,1,2)])

        @test verify_sorted(sorted_df) == true
        @test verify_sorted(unsorted_df) == false
    end

    @testset "count_all_missing_rows" begin
        df = DataFrame(
            timestamp = [DateTime(2024,1,1), DateTime(2024,1,2), DateTime(2024,1,3)],
            WS_80m = [5.0, missing, missing],
            WD_80m = [180.0, missing, missing]
        )

        count = count_all_missing_rows(df, [:WS_80m, :WD_80m])
        @test count == 2
    end
end
