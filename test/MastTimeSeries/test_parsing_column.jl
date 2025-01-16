# 文件：./test/MastTimeSeries/test_parsing_column.jl

using Test
using YAML
using DataFrames
using Dates
using CleanMastProject.Types.Utils
using CleanMastProject.MastTimeSeries
using CleanMastProject.CleanMastConfig
using CleanMastProject.Types.CleanMastConfig
using CleanMastProject.Types.MastTimeSeries
using CleanMastProject.SensorFormats

@testset "Column Format Parsing Tests" begin
    @testset "Extract Format Placeholders" begin
        format1 = "Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}"
        @test extract_format_placeholders(format1) == 
              ["channel", "sensorType", "height", "sensorDirection", "statType", "unit"]
        
        format2 = "{sensorType}_{height}m_{customField}"
        @test extract_format_placeholders(format2) == 
              ["sensorType", "height", "customField"]
        
        format3 = "Static_Text_{sensorType}_{height}m"
        @test extract_format_placeholders(format3) == 
              ["sensorType", "height"]
    end

    @testset "Create Regex Pattern" begin
        format = "Ch{channel}_{sensorType}_{height}m"
        placeholders = ["channel", "sensorType", "height"]
        regex = create_regex_pattern(format, placeholders)
        
        @test regex isa Regex
        @test match(regex, "Ch1_Anem_80m") !== nothing
        @test match(regex, "Ch2_Vane_60m") !== nothing
        @test match(regex, "Invalid_Format") === nothing
    end

    @testset "Parse Column Name with Basic Mappings" begin
        formats = ["Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}"]
        mappings = [
            MappingRule(
                Dict("sensorType" => "Anem"),
                RuleOutcome(sensorType="WindSpeed", unit="m/s", multiplier=1.0)
            ),
            MappingRule(
                Dict("sensorType" => "Vane"),
                RuleOutcome(sensorType="WindDirection", unit="deg", multiplier=1.0)
            ),
            MappingRule(Dict("statType" => "Avg"), RuleOutcome(statType="avg")),
            MappingRule(Dict("statType" => "Max"), RuleOutcome(statType="max")),
            MappingRule(Dict("statType" => "Min"), RuleOutcome(statType="min")),
            MappingRule(Dict("statType" => "SD"), RuleOutcome(statType="sd"))
        ]

        # Test valid column names
        original_name = "Ch1_Anem_80m_315_Avg_mps"
        result = parse_column_name(original_name, formats, mappings)
        @test result !== nothing
        @test result.originalColumnName == Symbol(original_name)
        @test result.columnName == Symbol("Ch1_WindSpeed_80m_315_avg_m/s")
        @test result.sensorType == "WindSpeed"
        @test result.height == 80.0
        @test result.sensorDirection == "315"
        @test result.statType == "avg"
        @test result.unit == "m/s"
        @test result.multiplier == 1.0

        # Test invalid column names
        @test parse_column_name("Invalid_Format", formats, mappings) === nothing
    end

    @testset "Parse Column Name with Unit Conversion" begin
        formats = ["Ch{channel}_{sensorType}_{height}m_{statType}_{unit}"]
        mappings = [
            MappingRule(
                Dict("sensorType" => "Analog", "unit" => "hPa"),
                RuleOutcome(sensorType="Pressure", unit="Pa", multiplier=100.0)
            ),
            MappingRule(
                Dict("sensorType" => "Analog", "unit" => "C"),
                RuleOutcome(sensorType="Temperature", unit="C", multiplier=1.0)
            ),
            MappingRule(Dict("statType" => "Avg"), RuleOutcome(statType="avg")),
            MappingRule(Dict("statType" => "Max"), RuleOutcome(statType="max")),
            MappingRule(Dict("statType" => "Min"), RuleOutcome(statType="min")),
            MappingRule(Dict("statType" => "SD"), RuleOutcome(statType="sd"))
        ]

        # Test pressure conversion
        original_pressure_name = "Ch1_Analog_80m_Avg_hPa"
        result = parse_column_name(original_pressure_name, formats, mappings)
        @test result !== nothing
        @test result.originalColumnName == Symbol(original_pressure_name)
        @test result.columnName == Symbol("Ch1_Pressure_80m_avg_Pa")
        @test result.sensorType == "Pressure"
        @test result.unit == "Pa"
        @test result.multiplier == 100.0

        # Test temperature without conversion
        original_temp_name = "Ch2_Analog_80m_Avg_C"
        result = parse_column_name(original_temp_name, formats, mappings)
        @test result !== nothing
        @test result.originalColumnName == Symbol(original_temp_name)
        @test result.columnName == Symbol("Ch2_Temperature_80m_avg_C")
        @test result.sensorType == "Temperature"
        @test result.unit == "C"
        @test result.multiplier == 1.0
    end

    @testset "Parse Column Metadata with SensorConfig" begin
        df = DataFrame(
            "Timestamp" => DateTime[],
            "Ch1_Anem_80m_315_Avg_mps" => Float64[],
            "Ch2_Vane_80m_315_Avg_deg" => Float64[],
            "Ch3_Analog_80m_Avg_hPa" => Float64[],
            "Invalid_Column" => Float64[]
        )

        mappings = [
            MappingRule(
                Dict("sensorType" => "Anem"),
                RuleOutcome(sensorType="WindSpeed", unit="m/s")
            ),
            MappingRule(
                Dict("sensorType" => "Vane"),
                RuleOutcome(sensorType="WindDirection", unit="deg")
            ),
            MappingRule(
                Dict("sensorType" => "Analog", "unit" => "hPa"),
                RuleOutcome(sensorType="Pressure", unit="Pa", multiplier=100.0)
            ),
            MappingRule(Dict("statType" => "Avg"), RuleOutcome(statType="avg")),
            MappingRule(Dict("statType" => "Max"), RuleOutcome(statType="max")),
            MappingRule(Dict("statType" => "Min"), RuleOutcome(statType="min")),
            MappingRule(Dict("statType" => "SD"), RuleOutcome(statType="sd"))
        ]

        sensor_config = SensorConfig(
            ["Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}",
             "Ch{channel}_{sensorType}_{height}m_{statType}_{unit}"],
            "Timestamp",
            "yyyy-mm-dd HH:MM:SS",
            nothing,
            1,
            mappings
        )

        metadata = parse_column_metadata(df, sensor_config)

        @test length(metadata) == 3
        
        # Check wind speed sensor
        ws_sensor = first(filter(m -> m.sensorType == "WindSpeed", metadata))
        @test ws_sensor.originalColumnName == Symbol("Ch1_Anem_80m_315_Avg_mps")
        @test ws_sensor.columnName == Symbol("Ch1_WindSpeed_80m_315_avg_m/s")
        @test ws_sensor.statType == "avg"
        
        # Check wind direction sensor
        wd_sensor = first(filter(m -> m.sensorType == "WindDirection", metadata))
        @test wd_sensor.originalColumnName == Symbol("Ch2_Vane_80m_315_Avg_deg")
        @test wd_sensor.columnName == Symbol("Ch2_WindDirection_80m_315_avg_deg")
        @test wd_sensor.statType == "avg"
        
        # Check pressure sensor
        pressure_sensor = first(filter(m -> m.sensorType == "Pressure", metadata))
        @test pressure_sensor.originalColumnName == Symbol("Ch3_Analog_80m_Avg_hPa")
        @test pressure_sensor.columnName == Symbol("Ch3_Pressure_80m_avg_Pa")
        @test pressure_sensor.unit == "Pa"
        @test pressure_sensor.multiplier == 100.0
        @test pressure_sensor.statType == "avg"
    end

    @testset "Multiple Matching Rules" begin
        formats = ["Ch{channel}_{sensorType}_{height}m_{statType}_{unit}"]
        mappings = [
            MappingRule(
                Dict("sensorType" => "Anem"),
                RuleOutcome(sensorType="WindSpeed", multiplier=1.0)
            ),
            MappingRule(
                Dict("unit" => "mps"),
                RuleOutcome(unit="m/s", multiplier=1.0)
            ),
            MappingRule(Dict("statType" => "Avg"), RuleOutcome(statType="avg")),
            MappingRule(Dict("statType" => "Max"), RuleOutcome(statType="max")),
            MappingRule(Dict("statType" => "Min"), RuleOutcome(statType="min")),
            MappingRule(Dict("statType" => "SD"), RuleOutcome(statType="sd"))
        ]

        original_name = "Ch1_Anem_80m_Avg_mps"
        result = parse_column_name(original_name, formats, mappings)
        @test result !== nothing
        @test result.originalColumnName == Symbol(original_name)
        @test result.columnName == Symbol("Ch1_WindSpeed_80m_avg_m/s")
        @test result.sensorType == "WindSpeed"
        @test result.statType == "avg"
        @test result.unit == "m/s"
        @test result.multiplier == 1.0
    end

    @testset "Load Preset Format" begin
        mktempdir() do temp_dir
            # Create a temporary format file
            format_path = joinpath(temp_dir, "test.yaml")
            format_config = Dict(
                "column_formats" => ["Ch{channel}_{sensorType}_{height}m_{statType}_{unit}"],
                "timestamp_column" => "Timestamp",
                "timestamp_format" => "yyyy-mm-dd HH:MM:SS",
                "delim" => "\t",
                "skip_to" => 1,
                "mappings" => [
                    Dict{String, Any}(
                        "match" => Dict{String, Any}("sensorType" => "Anem"),
                        "rule" => Dict{String, Any}(
                            "sensorType" => "WindSpeed",
                            "unit" => "m/s",
                            "multiplier" => 1.0
                        )
                    )
                ]
            )
            open(format_path, "w") do io
                YAML.write(io, format_config)
            end

            # Test loading the format
            sensor_config = from_dict(SensorConfig, format_config)
            @test sensor_config.column_formats == ["Ch{channel}_{sensorType}_{height}m_{statType}_{unit}"]
            @test sensor_config.timestamp_column == "Timestamp"
            @test sensor_config.delim == "\t"
            @test length(sensor_config.mappings) == 1
            @test sensor_config.mappings[1].rule.sensorType == "WindSpeed"
            @test sensor_config.mappings[1].rule.unit == "m/s"
            @test sensor_config.mappings[1].rule.multiplier == 1.0
        end
    end

    @testset "DataFrame Column Transformation" begin
        # Test actual data transformation
        df = DataFrame(
            "Timestamp" => [DateTime(2024,1,1)],
            "Ch1_Anem_80m_315_Avg_mps" => [5.0],
            "Ch2_Vane_80m_315_Avg_deg" => [180.0],
            "Ch3_Analog_80m_Avg_hPa" => [1013.25]
        )

        mappings = [
            MappingRule(
                Dict("sensorType" => "Anem"),
                RuleOutcome(sensorType="WindSpeed", unit="m/s")
            ),
            MappingRule(
                Dict("sensorType" => "Vane"),
                RuleOutcome(sensorType="WindDirection", unit="deg")
            ),
            MappingRule(
                Dict("sensorType" => "Analog", "unit" => "hPa"),
                RuleOutcome(sensorType="Pressure", unit="Pa", multiplier=100.0)
            ),
            MappingRule(Dict("statType" => "Avg"), RuleOutcome(statType="avg")),
            MappingRule(Dict("statType" => "Max"), RuleOutcome(statType="max")),
            MappingRule(Dict("statType" => "Min"), RuleOutcome(statType="min")),
            MappingRule(Dict("statType" => "SD"), RuleOutcome(statType="sd"))
        ]

        sensor_config = SensorConfig(
            ["Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}",
             "Ch{channel}_{sensorType}_{height}m_{statType}_{unit}"],
            "Timestamp",
            "yyyy-mm-dd HH:MM:SS",
            nothing,
            1,
            mappings
        )

        metadata = parse_column_metadata(df, sensor_config)
        
        # Check metadata before transformation
        @test length(metadata) == 3
        
        # Create new DataFrame for transformation
        df_transformed = copy(df)
        
        # Apply transformations
        df_transformed = apply_multipliers!(df_transformed, metadata)
        
        # Check column renames and transformations
        @test !("Ch3_Analog_80m_Avg_hPa" in names(df_transformed))  # Old column should be gone
        @test "Ch3_Pressure_80m_avg_Pa" in names(df_transformed)    # New column should exist
        @test df_transformed[1, "Ch3_Pressure_80m_avg_Pa"] ≈ 101325.0  # 1013.25 * 100
        
        # Check that other columns were preserved but renamed according to sensor type
        @test df_transformed[1, "Ch1_WindSpeed_80m_315_avg_m/s"] == 5.0
        @test df_transformed[1, "Ch2_WindDirection_80m_315_avg_deg"] == 180.0
    end
end
