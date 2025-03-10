using Test
using YAML
using DataFrames
using Dates
using CleanMastProject.Types.Utils
using CleanMastProject.SensorParser
using CleanMastProject.MastTimeSeries
using CleanMastProject.CleanMastConfig
using CleanMastProject.Types.CleanMastConfig
using CleanMastProject.Types.MastTimeSeries

@testset "Sensor Processing Integration Tests" begin
    @testset "Full Sensor Processing Pipeline" begin
        # Create a temporary directory for test files
        mktempdir() do temp_dir
            # Create test data file
            data_file = joinpath(temp_dir, "test_data.csv")
            open(data_file, "w") do io
                write(io, """Data
Timestamp,Ch1_Anem_80m_315_Avg_mps,Ch2_Vane_80m_315_Avg_deg,Ch3_Analog_80m_Avg_hPa
2024-01-01 00:00:00,5.0,180.0,1013.25
2024-01-01 00:10:00,5.5,185.0,1013.30
""")
            end

            # Create sensor config
            sensor_config = SensorConfig(
                ["Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}"],
                "Timestamp",
                "yyyy-mm-dd HH:MM:SS",
                ",",
                ["/^Data/", "/^Timestamp/"],
                [
                    MappingRule(
                        Dict("sensorType" => "Anem"),
                        RuleOutcome(sensorType="WindSpeed", unit="m/s", multiplier=1.0)
                    ),
                    MappingRule(
                        Dict("sensorType" => "Vane"),
                        RuleOutcome(sensorType="WindDirection", unit="deg", multiplier=1.0)
                    ),
                    MappingRule(
                        Dict("sensorType" => "Analog", "unit" => "hPa"),
                        RuleOutcome(sensorType="Pressure", unit="Pa", multiplier=100.0)
                    ),
                    MappingRule(Dict("statType" => "Avg"), RuleOutcome(statType="avg"))
                ]
            )

            # Step 1: Read and parse data using SensorParser
            csv_opts = generate_csv_opts(sensor_config, temp_dir)
            df = CSV.read(data_file, DataFrame; csv_opts...)
            normalize_timestamp!(df, sensor_config.timestamp_column)
            sensors = parse_column_metadata(df, sensor_config)

            # Verify initial parsing
            @test length(sensors) == 3
            @test all(s -> s.originalColumnName == s.columnName, sensors)  # No renaming yet
            @test any(s -> s.sensorType == "WindSpeed" && s.multiplier == 1.0, sensors)
            @test any(s -> s.sensorType == "WindDirection" && s.multiplier == 1.0, sensors)
            @test any(s -> s.sensorType == "Pressure" && s.multiplier == 100.0, sensors)

            # Step 2: Apply multipliers and rename using MastTimeSeries
            df_transformed = rename_and_apply_multipliers!(df, sensors)

            # Verify final state
            @test "Ch1_WindSpeed_80m_315_avg_m/s" in names(df_transformed)
            @test "Ch2_WindDirection_80m_315_avg_deg" in names(df_transformed)
            @test "Ch3_Pressure_80m_avg_Pa" in names(df_transformed)

            # Check values
            @test df_transformed[1, "Ch1_WindSpeed_80m_315_avg_m/s"] == 5.0
            @test df_transformed[1, "Ch2_WindDirection_80m_315_avg_deg"] == 180.0
            @test df_transformed[1, "Ch3_Pressure_80m_avg_Pa"] ≈ 101325.0
            @test df_transformed[2, "Ch1_WindSpeed_80m_315_avg_m/s"] == 5.5
            @test df_transformed[2, "Ch2_WindDirection_80m_315_avg_deg"] == 185.0
            @test df_transformed[2, "Ch3_Pressure_80m_avg_Pa"] ≈ 101330.0
        end
    end

    @testset "Error Handling in Pipeline" begin
        mktempdir() do temp_dir
            # Create test data file with invalid format
            data_file = joinpath(temp_dir, "bad_data.csv")
            open(data_file, "w") do io
                write(io, """Data
Timestamp,Invalid_Column_1,Invalid_Column_2
2024-01-01 00:00:00,5.0,180.0
""")
            end

            sensor_config = SensorConfig(
                ["Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}"],
                "Timestamp",
                "yyyy-mm-dd HH:MM:SS",
                ",",
                ["/^Data/", "/^Timestamp/"],
                [MappingRule(
                    Dict("sensorType" => "Anem"),
                    RuleOutcome(sensorType="WindSpeed", unit="m/s")
                )]
            )

            # Step 1: Read and parse data
            csv_opts = generate_csv_opts(sensor_config, temp_dir)
            df = CSV.read(data_file, DataFrame; csv_opts...)
            normalize_timestamp!(df, sensor_config.timestamp_column)
            
            # Should warn about unparseable columns
            @test_logs (:warn, "Failed to parse column name: Invalid_Column_1") (:warn, "Failed to parse column name: Invalid_Column_2") begin
                sensors = parse_column_metadata(df, sensor_config)
                @test isempty(sensors)  # No valid sensors found
            end
        end
    end

    @testset "Multiple Format Patterns" begin
        mktempdir() do temp_dir
            # Create test data with mixed formats
            data_file = joinpath(temp_dir, "mixed_format.csv")
            open(data_file, "w") do io
                write(io, """Data
Timestamp,Ch1_Anem_80m_315_Avg_mps,Ch2_Vane_80m_Avg_deg
2024-01-01 00:00:00,5.0,180.0
""")
            end

            sensor_config = SensorConfig(
                [
                    "Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}",
                    "Ch{channel}_{sensorType}_{height}m_{statType}_{unit}"
                ],
                "Timestamp",
                "yyyy-mm-dd HH:MM:SS",
                ",",
                ["/^Data/", "/^Timestamp/"],
                [
                    MappingRule(
                        Dict("sensorType" => "Anem"),
                        RuleOutcome(sensorType="WindSpeed", unit="m/s")
                    ),
                    MappingRule(
                        Dict("sensorType" => "Vane"),
                        RuleOutcome(sensorType="WindDirection", unit="deg")
                    ),
                    MappingRule(Dict("statType" => "Avg"), RuleOutcome(statType="avg"))
                ]
            )

            # Process data
            csv_opts = generate_csv_opts(sensor_config, temp_dir)
            df = CSV.read(data_file, DataFrame; csv_opts...)
            normalize_timestamp!(df, sensor_config.timestamp_column)
            sensors = parse_column_metadata(df, sensor_config)

            # Verify both format patterns worked
            @test length(sensors) == 2
            @test any(s -> s.sensorDirection == "315", sensors)  # First format
            @test any(s -> s.sensorDirection == "", sensors)     # Second format

            # Apply transformations
            df_transformed = rename_and_apply_multipliers!(df, sensors)

            # Verify results
            @test "Ch1_WindSpeed_80m_315_avg_m/s" in names(df_transformed)
            @test "Ch2_WindDirection_80m_avg_deg" in names(df_transformed)
            @test df_transformed[1, "Ch1_WindSpeed_80m_315_avg_m/s"] == 5.0
            @test df_transformed[1, "Ch2_WindDirection_80m_avg_deg"] == 180.0
        end
    end
end 