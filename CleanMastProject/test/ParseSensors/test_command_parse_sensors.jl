# test/ParseSensors/test_command_parse_sensors.jl

using Test
using CleanMastProject.ParseSensors.CommandParseSensors
using CleanMastProject.ParseSensors.CommandParseSensors: validate_utf8_encoding
using CSV, TOML, DataFrames, Parquet2, DataAPI

@testset "CommandParseSensors Integration Tests" begin

    @testset "Encoding Validation" begin
        mktempdir() do temp_dir
            # Test 1: UTF-8 file passes validation
            utf8_path = joinpath(temp_dir, "utf8_test.txt")
            write(utf8_path, "Timestamp\tWindSpeed\n2024-01-01 00:00:00\t10.5\n")
            @test validate_utf8_encoding(utf8_path) == true

            # Test 2: ASCII file passes validation (subset of UTF-8)
            ascii_path = joinpath(temp_dir, "ascii_test.txt")
            write(ascii_path, "Timestamp,Value\n1,2\n3,4\n")
            @test validate_utf8_encoding(ascii_path) == true

            # Test 3: Missing file throws error
            missing_path = joinpath(temp_dir, "nonexistent.txt")
            @test_throws ErrorException validate_utf8_encoding(missing_path)

            # Test 4: Non-UTF-8 encoding (Latin-1 with 0xFC) fails with ErrorException
            latin1_path = joinpath(temp_dir, "latin1_test.txt")
            # 0xFC is ü in Latin-1, not valid UTF-8
            write(latin1_path, "Timestamp\tValue\n2024-01-01\t\xFC\n")
            @test_throws ErrorException validate_utf8_encoding(latin1_path)
        end
    end

    # Note: These tests will require creating a temporary project structure
    # with data files and a parse-sensors.toml to be effective.
    # This will be implemented fully later.

    @testset "End-to-end parsing" begin
        mktempdir() do temp_dir
            # 1. Create dummy data file with enough lines for header detection
            data_path = joinpath(temp_dir, "test_data.txt")
            write(data_path, "Timestamp\tWindSpeed_80m_N_mps\tPressure_hPa\n" *
                             "2024-01-01 00:00:00\t10.5\t1012\n" *
                             "2024-01-01 00:10:00\t11.2\t1013\n" *
                             "2024-01-01 00:20:00\t11.5\t1013\n" *
                             "2024-01-01 00:30:00\t12.1\t1014\n" *
                             "2024-01-01 00:40:00\t12.3\t1014\n")

            # 2. Create dummy sensor format TOML
            sensor_format_path = joinpath(temp_dir, "test_format.toml")
            write(sensor_format_path, """
                timestamp_column = "Timestamp"
                timestamp_format = "yyyy-mm-dd HH:MM:SS"
                delim = "\t"

                [[columns]]
                match = "{sensorType}_{height}m_{sensorDirection}_{unit}"
                format = "{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}"

                [[columns]]
                match = "{sensorType}_{unit}"
                format = "{sensorType}_{statType}_{unit}"

                [[mappings]]
                [mappings.match]
                sensorType = "WindSpeed"
                [mappings.rule]
                statType = "avg"

                [[mappings]]
                [mappings.match]
                sensorType = "Pressure"
                [mappings.rule]
                unit = "Pa"
                statType = "avg"
                multiplier = 100.0
                height = 10.0
            """)

            # 3. Create dummy parse-sensors.toml
            config_path = joinpath(temp_dir, "parse-sensors.toml")
            write(config_path, """
                [[masts]]
                input = "test_data.txt"
                sensor = "./test_format.toml"
            """)

            # 4. Run the command
            CommandParseSensors.execute(config_path)

            # 5. Check the output files (now Parquet with embedded metadata)
            output_parquet_path = joinpath(temp_dir, "raw", "test_data.parquet")

            @test isfile(output_parquet_path)

            # 6. Verify Parquet content
            ds = Parquet2.readfile(output_parquet_path)
            df = DataFrame(ds)
            @test names(df) == ["timestamp", "WindSpeed_80m_N_avg_mps", "Pressure_avg_Pa"]
            @test df[1, "Pressure_avg_Pa"] == 101200.0 # Check multiplier

            # 7. Verify embedded sensor metadata in Parquet column metadata
            # Extract sensors from column metadata
            sensors = []
            for col in ds[1]
                col_name = Parquet2.name(col)
                if col_name == "timestamp"
                    continue
                end
                col_meta = DataAPI.metadata(col)
                if !isnothing(col_meta) && haskey(col_meta, "sensorType")
                    push!(sensors, col_meta)
                end
            end

            @test length(sensors) == 2

            ws_sensor = first(filter(s -> s["sensorType"] == "WindSpeed", sensors))
            @test ws_sensor["height"] == "80.0"
            @test ws_sensor["sensorDirection"] == "N"
        end
    end

end 