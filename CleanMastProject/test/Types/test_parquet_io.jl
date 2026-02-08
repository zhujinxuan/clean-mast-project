using Test
using DataFrames
using Dates
using TOML
using UUIDs
include("../TestUtils.jl")
using .TestUtils: mktempdir_project
using CleanMastProject.Types.MastTimeSeries:
    TimeSeriesData,
    TimeRange,
    TimeSeriesSource,
    detect_file_format,
    load_timeseries,
    save_timeseries,
    load_timeseries_csv,
    load_timeseries_parquet,
    save_timeseries_csv,
    save_timeseries_parquet
using CleanMastProject.Types.SensorColumns: SensorColumn

# Helper function to find a sensor by predicate
function find_sensor(predicate::Function, sensors::Vector{SensorColumn})::Union{SensorColumn, Nothing}
    for s in sensors
        if predicate(s)
            return s
        end
    end
    return nothing
end

@testset "Parquet I/O" begin
    @testset "detect_file_format" begin
        @test detect_file_format("data.csv") == :csv
        @test detect_file_format("data.CSV") == :csv
        @test detect_file_format("data.parquet") == :parquet
        @test detect_file_format("data.PARQUET") == :parquet
        @test detect_file_format("data.parq") == :parquet
        @test detect_file_format("data.txt") == :unknown
        @test detect_file_format("data") == :unknown
        @test detect_file_format("/path/to/data.csv") == :csv
        @test detect_file_format("/path/to/data.parquet") == :parquet
    end

    @testset "TimeSeriesSource construction" begin
        source_with_sensors = TimeSeriesSource("data.csv", "sensors.toml")
        @test source_with_sensors.data == "data.csv"
        @test source_with_sensors.sensors == "sensors.toml"

        source_without_sensors = TimeSeriesSource("data.parquet", nothing)
        @test source_without_sensors.data == "data.parquet"
        @test isnothing(source_without_sensors.sensors)
    end

    @testset "load_timeseries CSV backward compatibility" begin
        mktempdir_project("parquet_io") do tmpdir
            # Create test CSV data
            csv_path = joinpath(tmpdir, "test_data.csv")
            sensors_path = joinpath(tmpdir, "test_sensors.toml")

            # Write test CSV
            test_csv_content = """timestamp,WS_80m,WD_80m,Temp_10m
2023-01-01T00:00:00,8.5,180,15.2
2023-01-01T00:10:00,8.3,182,15.1
2023-01-01T00:20:00,8.7,179,15.0
"""
            write(csv_path, test_csv_content)

            # Write test sensors TOML
            sensors_config = Dict{String, Any}(
                "sensors" => [
                    Dict{String, Any}(
                        "columnName" => "WS_80m",
                        "sensorType" => "WindSpeed",
                        "sensorDirection" => "N",
                        "height" => 80.0,
                        "statType" => "avg",
                        "unit" => "m/s"
                    ),
                    Dict{String, Any}(
                        "columnName" => "WD_80m",
                        "sensorType" => "WindDirection",
                        "sensorDirection" => "N",
                        "height" => 80.0,
                        "statType" => "avg",
                        "unit" => "deg"
                    ),
                    Dict{String, Any}(
                        "columnName" => "Temp_10m",
                        "sensorType" => "Temperature",
                        "sensorDirection" => "N/A",
                        "height" => 10.0,
                        "statType" => "avg",
                        "unit" => "C"
                    )
                ]
            )
            open(sensors_path, "w") do io
                TOML.print(io, sensors_config)
            end

            # Load time series
            source = TimeSeriesSource(csv_path, sensors_path)
            ts_data = load_timeseries(source, tmpdir)

            # Verify loaded data
            @test ts_data isa TimeSeriesData
            @test nrow(ts_data.df) == 3
            @test Set(propertynames(ts_data.df)) == Set([:timestamp, :WS_80m, :WD_80m, :Temp_10m])
            @test length(ts_data.sensors) == 3

            # Verify sensor metadata
            ws_sensor = find_sensor(s -> s.sensorType == "WindSpeed", ts_data.sensors)
            @test ws_sensor !== nothing
            @test ws_sensor.columnName == :WS_80m
            @test ws_sensor.height == 80.0
            @test ws_sensor.statType == "avg"
            @test ws_sensor.unit == "m/s"

            wd_sensor = find_sensor(s -> s.sensorType == "WindDirection", ts_data.sensors)
            @test wd_sensor !== nothing
            @test wd_sensor.columnName == :WD_80m
            @test wd_sensor.height == 80.0
            @test wd_sensor.unit == "deg"
        end
    end

    @testset "load_timeseries CSV with missing data" begin
        mktempdir_project("parquet_io") do tmpdir
            # Create test CSV with missing values
            csv_path = joinpath(tmpdir, "test_missing.csv")
            sensors_path = joinpath(tmpdir, "test_sensors.toml")

            test_csv_content = """timestamp,WS_80m
2023-01-01T00:00:00,8.5
2023-01-01T00:10:00,
2023-01-01T00:20:00,7.9
"""
            write(csv_path, test_csv_content)

            sensors_config = Dict{String, Any}(
                "sensors" => [
                    Dict{String, Any}(
                        "columnName" => "WS_80m",
                        "sensorType" => "WindSpeed",
                        "sensorDirection" => "N",
                        "height" => 80.0,
                        "statType" => "avg",
                        "unit" => "m/s"
                    )
                ]
            )
            open(sensors_path, "w") do io
                TOML.print(io, sensors_config)
            end

            source = TimeSeriesSource(csv_path, sensors_path)
            ts_data = load_timeseries(source, tmpdir)

            @test nrow(ts_data.df) == 3
            @test ismissing(ts_data.df[2, :WS_80m])
            @test !ismissing(ts_data.df[1, :WS_80m])
            @test !ismissing(ts_data.df[3, :WS_80m])
        end
    end

    @testset "load_timeseries_parquet" begin
        mktempdir_project("parquet_io") do tmpdir
            # Create test data and save to Parquet first
            df = DataFrame(
                timestamp = [DateTime(2023, 1, 1, 0, i * 10) for i in 0:5],
                WS_80m = [8.5 + i * 0.1 for i in 0:5],
                WD_80m = [180.0 + i for i in 0:5]
            )
            sensors = [
                SensorColumn(
                    columnName = :WS_80m,
                    sensorType = "WindSpeed",
                    sensorDirection = "N",
                    height = 80.0,
                    statType = "avg",
                    unit = "m/s"
                ),
                SensorColumn(
                    columnName = :WD_80m,
                    sensorType = "WindDirection",
                    sensorDirection = "N",
                    height = 80.0,
                    statType = "avg",
                    unit = "deg"
                )
            ]
            original_data = TimeSeriesData(df, sensors)

            # Save to Parquet
            parquet_path = joinpath(tmpdir, "test.parquet")
            save_timeseries_parquet(parquet_path, original_data)

            # Load from Parquet
            source = TimeSeriesSource(parquet_path, nothing)
            loaded_data = load_timeseries_parquet(source)

            # Verify loaded data
            @test loaded_data isa TimeSeriesData
            @test nrow(loaded_data.df) == 6
            @test Set(propertynames(loaded_data.df)) == Set([:timestamp, :WS_80m, :WD_80m])
            @test length(loaded_data.sensors) == 2

            # Verify data values
            @test loaded_data.df[1, :WS_80m] == 8.5
            @test loaded_data.df[6, :WS_80m] == 9.0
            @test loaded_data.df[1, :WD_80m] == 180.0
            @test loaded_data.df[6, :WD_80m] == 185.0

            # Verify sensor metadata from Parquet
            ws_sensor = find_sensor(s -> s.columnName == :WS_80m, loaded_data.sensors)
            @test ws_sensor !== nothing
            @test ws_sensor.sensorType == "WindSpeed"
            @test ws_sensor.height == 80.0
            @test ws_sensor.statType == "avg"
            @test ws_sensor.unit == "m/s"
        end
    end

    @testset "save_timeseries_parquet with metadata" begin
        mktempdir_project("parquet_io") do tmpdir
            # Create test data with multiple sensors
            df = DataFrame(
                timestamp = [DateTime(2023, 1, 1, i) for i in 1:3],
                WS_100m = [10.0, 10.5, 11.0],
                WD_100m = [90.0, 92.0, 95.0],
                Temp_10m = [15.0, 14.8, 14.5]
            )
            sensors = [
                SensorColumn(columnName = :WS_100m, sensorType = "WindSpeed", sensorDirection = "N", height = 100.0, statType = "avg", unit = "m/s"),
                SensorColumn(columnName = :WD_100m, sensorType = "WindDirection", sensorDirection = "N", height = 100.0, statType = "avg", unit = "deg"),
                SensorColumn(columnName = :Temp_10m, sensorType = "Temperature", sensorDirection = "N/A", height = 10.0, statType = "avg", unit = "C")
            ]
            data = TimeSeriesData(df, sensors)

            # Save to Parquet
            parquet_path = joinpath(tmpdir, "output.parquet")
            save_timeseries_parquet(parquet_path, data)

            # Verify file exists
            @test isfile(parquet_path)

            # Load and verify
            source = TimeSeriesSource(parquet_path, nothing)
            loaded = load_timeseries_parquet(source)

            @test nrow(loaded.df) == 3
            @test length(loaded.sensors) == 3

            # Verify all sensors preserved
            @test any(s -> s.columnName == :WS_100m && s.height == 100.0, loaded.sensors)
            @test any(s -> s.columnName == :Temp_10m && s.height == 10.0, loaded.sensors)
            @test any(s -> s.columnName == :Temp_10m && s.sensorType == "Temperature", loaded.sensors)
        end
    end

    @testset "save_timeseries CSV backward compatibility" begin
        mktempdir_project("parquet_io") do tmpdir
            # Create test data
            df = DataFrame(
                timestamp = [DateTime(2023, 1, 1, i) for i in 1:3],
                WS_80m = [8.0, 8.5, 9.0]
            )
            sensors = [
                SensorColumn(columnName = :WS_80m, sensorType = "WindSpeed", sensorDirection = "N", height = 80.0, statType = "avg", unit = "m/s")
            ]
            data = TimeSeriesData(df, sensors)

            # Save to CSV with sensors file
            csv_path = joinpath(tmpdir, "output.csv")
            sensors_path = joinpath(tmpdir, "output_sensors.toml")
            source = TimeSeriesSource(csv_path, sensors_path)
            save_timeseries(source, tmpdir, data)

            # Verify files exist
            @test isfile(csv_path)
            @test isfile(sensors_path)

            # Load and verify
            loaded_source = TimeSeriesSource(csv_path, sensors_path)
            loaded = load_timeseries(loaded_source, tmpdir)

            @test nrow(loaded.df) == 3
            @test Set(propertynames(loaded.df)) == Set([:timestamp, :WS_80m])
            @test length(loaded.sensors) == 1
            @test loaded.sensors[1].columnName == :WS_80m
            @test loaded.sensors[1].height == 80.0
            @test loaded.sensors[1].sensorType == "WindSpeed"
        end
    end

    @testset "format auto-detection" begin
        mktempdir_project("parquet_io") do tmpdir
            # Create test data
            df = DataFrame(
                timestamp = [DateTime(2023, 1, 1, i) for i in 1:2],
                WS_80m = [8.0, 8.5]
            )
            sensors = [
                SensorColumn(columnName = :WS_80m, sensorType = "WindSpeed", sensorDirection = "N", height = 80.0, statType = "avg", unit = "m/s")
            ]
            data = TimeSeriesData(df, sensors)

            # Test Parquet auto-detection
            parquet_path = joinpath(tmpdir, "auto.parquet")
            save_timeseries_parquet(parquet_path, data)

            # Load with auto-detection
            auto_source = TimeSeriesSource(parquet_path, nothing)
            auto_loaded = load_timeseries(auto_source, tmpdir)
            @test nrow(auto_loaded.df) == 2

            # Test CSV auto-detection
            csv_path = joinpath(tmpdir, "auto.csv")
            sensors_path = joinpath(tmpdir, "auto_sensors.toml")
            csv_source = TimeSeriesSource(csv_path, sensors_path)
            save_timeseries(csv_source, tmpdir, data)

            # Load with auto-detection
            csv_loaded = load_timeseries(csv_source, tmpdir)
            @test nrow(csv_loaded.df) == 2
        end
    end

    @testset "metadata round-trip preservation" begin
        mktempdir_project("parquet_io") do tmpdir
            # Create test data with various sensor configurations
            df = DataFrame(
                timestamp = [DateTime(2023, 1, 1, i) for i in 1:4],
                WS_80m_N = [7.0, 7.5, 8.0, 8.5],
                WS_100m_N = [8.0, 8.5, 9.0, 9.5],
                WD_80m_NE = [45.0, 46.0, 47.0, 48.0],
                Temp_10m = [15.0, 14.8, 14.6, 14.4]
            )
            sensors = [
                SensorColumn(columnName = :WS_80m_N, sensorType = "WindSpeed", sensorDirection = "N", height = 80.0, statType = "avg", unit = "m/s"),
                SensorColumn(columnName = :WS_100m_N, sensorType = "WindSpeed", sensorDirection = "N", height = 100.0, statType = "avg", unit = "m/s"),
                SensorColumn(columnName = :WD_80m_NE, sensorType = "WindDirection", sensorDirection = "NE", height = 80.0, statType = "avg", unit = "deg"),
                SensorColumn(columnName = :Temp_10m, sensorType = "Temperature", sensorDirection = "N/A", height = 10.0, statType = "avg", unit = "C")
            ]
            original_data = TimeSeriesData(df, sensors)

            # Save to Parquet
            parquet_path = joinpath(tmpdir, "roundtrip.parquet")
            save_timeseries_parquet(parquet_path, original_data)

            # Load from Parquet
            source = TimeSeriesSource(parquet_path, nothing)
            loaded_data = load_timeseries_parquet(source)

            # Verify metadata preserved
            @test length(loaded_data.sensors) == length(original_data.sensors)

            for orig_sensor in original_data.sensors
                loaded_sensor = find_sensor(s -> s.columnName == orig_sensor.columnName, loaded_data.sensors)
                @test loaded_sensor !== nothing
                @test loaded_sensor.sensorType == orig_sensor.sensorType
                @test loaded_sensor.sensorDirection == orig_sensor.sensorDirection
                @test loaded_sensor.height == orig_sensor.height
                @test loaded_sensor.statType == orig_sensor.statType
                @test loaded_sensor.unit == orig_sensor.unit
            end
        end
    end

    @testset "empty dataframe handling" begin
        mktempdir_project("parquet_io") do tmpdir
            # Create empty DataFrame
            df = DataFrame(
                timestamp = DateTime[],
                WS_80m = Float64[]
            )
            sensors = [
                SensorColumn(columnName = :WS_80m, sensorType = "WindSpeed", sensorDirection = "N", height = 80.0, statType = "avg", unit = "m/s")
            ]
            data = TimeSeriesData(df, sensors)

            # Save to Parquet
            parquet_path = joinpath(tmpdir, "empty.parquet")
            save_timeseries_parquet(parquet_path, data)
            @test isfile(parquet_path)
        end
    end

    @testset "load_timeseries with unknown format defaults to CSV" begin
        mktempdir_project("parquet_io") do tmpdir
            # Create a CSV file with .txt extension (unknown format)
            csv_path = joinpath(tmpdir, "test_data.txt")
            sensors_path = joinpath(tmpdir, "test_sensors.toml")

            test_csv_content = """timestamp,WS_80m
2023-01-01T00:00:00,8.5
2023-01-01T00:10:00,8.3
"""
            write(csv_path, test_csv_content)

            sensors_config = Dict{String, Any}(
                "sensors" => [
                    Dict{String, Any}(
                        "columnName" => "WS_80m",
                        "sensorType" => "WindSpeed",
                        "sensorDirection" => "N",
                        "height" => 80.0,
                        "statType" => "avg",
                        "unit" => "m/s"
                    )
                ]
            )
            open(sensors_path, "w") do io
                TOML.print(io, sensors_config)
            end

            # Load with unknown format - should default to CSV
            source = TimeSeriesSource(csv_path, sensors_path)
            ts_data = load_timeseries(source, tmpdir)

            @test nrow(ts_data.df) == 2
            @test ts_data.df[1, :WS_80m] == 8.5
            @test ts_data.df[2, :WS_80m] == 8.3
        end
    end

    @testset "error handling" begin
        mktempdir_project("parquet_io") do tmpdir
            # Test missing data file
            source = TimeSeriesSource(joinpath(tmpdir, "missing.csv"), joinpath(tmpdir, "sensors.toml"))
            @test_throws ErrorException load_timeseries(source, tmpdir)

            # Test missing sensors file for CSV
            csv_path = joinpath(tmpdir, "data.csv")
            write(csv_path, "timestamp,WS_80m\n2023-01-01T00:00:00,8.5")
            source2 = TimeSeriesSource(csv_path, joinpath(tmpdir, "missing.toml"))
            @test_throws ErrorException load_timeseries(source2, tmpdir)

            # Test CSV format without sensors file specified
            source3 = TimeSeriesSource(csv_path, nothing)
            @test_throws ErrorException load_timeseries(source3, tmpdir)
        end
    end

    @testset "TimeSeriesSource with relative paths" begin
        mktempdir_project("parquet_io") do tmpdir
            # Create subdirectory structure
            data_dir = joinpath(tmpdir, "data")
            mkdir(data_dir)

            # Create test CSV
            csv_path = joinpath(data_dir, "test.csv")
            sensors_path = joinpath(data_dir, "sensors.toml")

            write(csv_path, "timestamp,WS_80m\n2023-01-01T00:00:00,8.5")

            sensors_config = Dict{String, Any}(
                "sensors" => [
                    Dict{String, Any}(
                        "columnName" => "WS_80m",
                        "sensorType" => "WindSpeed",
                        "sensorDirection" => "N",
                        "height" => 80.0,
                        "statType" => "avg",
                        "unit" => "m/s"
                    )
                ]
            )
            open(sensors_path, "w") do io
                TOML.print(io, sensors_config)
            end

            # Use relative path from tmpdir
            source = TimeSeriesSource("data/test.csv", "data/sensors.toml")
            ts_data = load_timeseries(source, tmpdir)

            @test nrow(ts_data.df) == 1
            @test ts_data.df[1, :WS_80m] == 8.5
        end
    end

    @testset "parquet with different statTypes" begin
        mktempdir_project("parquet_io") do tmpdir
            # Create data with non-avg statType
            df = DataFrame(
                timestamp = [DateTime(2023, 1, 1, i) for i in 1:2],
                WS_80m_max = [12.0, 12.5],
                WS_80m_min = [5.0, 5.5]
            )
            sensors = [
                SensorColumn(columnName = :WS_80m_max, sensorType = "WindSpeed", sensorDirection = "N", height = 80.0, statType = "max", unit = "m/s"),
                SensorColumn(columnName = :WS_80m_min, sensorType = "WindSpeed", sensorDirection = "N", height = 80.0, statType = "min", unit = "m/s")
            ]
            original_data = TimeSeriesData(df, sensors)

            # Save and reload
            parquet_path = joinpath(tmpdir, "stat_types.parquet")
            save_timeseries_parquet(parquet_path, original_data)

            source = TimeSeriesSource(parquet_path, nothing)
            loaded = load_timeseries_parquet(source)

            # Verify statType preserved
            max_sensor = find_sensor(s -> s.columnName == :WS_80m_max, loaded.sensors)
            min_sensor = find_sensor(s -> s.columnName == :WS_80m_min, loaded.sensors)

            @test max_sensor !== nothing
            @test max_sensor.statType == "max"
            @test min_sensor !== nothing
            @test min_sensor.statType == "min"
        end
    end
end
