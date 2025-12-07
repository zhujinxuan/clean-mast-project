# test/ParseSensors/test_command_parse_sensors.jl

using Test
using CleanMastProject.ParseSensors.CommandParseSensors
using CSV, TOML, DataFrames

@testset "CommandParseSensors Integration Tests" begin

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

            # 5. Check the output files
            output_csv_path = joinpath(temp_dir, "raw", "test_data.csv")
            output_toml_path = joinpath(temp_dir, "raw", "test_data.sensors.toml")

            @test isfile(output_csv_path)
            @test isfile(output_toml_path)

            # 6. Verify CSV content
            df = CSV.read(output_csv_path, DataFrame)
            @test names(df) == ["timestamp", "WindSpeed_80m_N_avg_mps", "Pressure_avg_Pa"]
            @test df[1, "Pressure_avg_Pa"] == 101200.0 # Check multiplier

            # 7. Verify TOML content
            sensors_toml = TOML.parsefile(output_toml_path)
            @test length(sensors_toml["sensors"]) == 2
            
            ws_sensor = first(filter(s -> s["sensorType"] == "WindSpeed", sensors_toml["sensors"]))
            @test ws_sensor["height"] == 80.0
            @test ws_sensor["sensorDirection"] == "N"
        end
    end

end 