# 文件：./test/MastTimeSeries/test_parsing_column.jl

using Test
using YAML
using DataFrames
using Dates
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
        format = "Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}"
        mappings = [
            MappingRule(
                Dict("sensorType" => "Anem"),
                RuleOutcome(sensorType="WindSpeed", unit="m/s")
            ),
            MappingRule(
                Dict("sensorType" => "Vane"),
                RuleOutcome(sensorType="WindDirection", unit="deg")
            )
        ]

        # Test valid column names
        result = parse_column_name("Ch1_Anem_80m_315_Avg_mps", format, mappings)
        @test result !== nothing
        @test result.columnName == Symbol("Ch1_Anem_80m_315_Avg_mps")
        @test result.sensorType == "WindSpeed"
        @test result.height == 80.0
        @test result.sensorDirection == "315"
        @test result.statType == "Avg"
        @test result.unit == "m/s"

        # Test invalid column names
        @test parse_column_name("Invalid_Format", format, mappings) === nothing
    end

    @testset "Parse Column Name with Unit Conversion" begin
        format = "Ch{channel}_{sensorType}_{height}m_{statType}_{unit}"
        mappings = [
            MappingRule(
                Dict("sensorType" => "Analog", "unit" => "hPa"),
                RuleOutcome(sensorType="Pressure", unit="Pa", multiplier=100.0)
            ),
            MappingRule(
                Dict("sensorType" => "Analog", "unit" => "C"),
                RuleOutcome(sensorType="Temperature", unit="C")
            )
        ]

        # Test pressure conversion
        result = parse_column_name("Ch1_Analog_80m_Avg_hPa", format, mappings)
        @test result !== nothing
        @test result.sensorType == "Pressure"
        @test result.unit == "Pa"

        # Test temperature without conversion
        result = parse_column_name("Ch2_Analog_80m_Avg_C", format, mappings)
        @test result !== nothing
        @test result.sensorType == "Temperature"
        @test result.unit == "C"
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
            )
        ]

        sensor_config = SensorConfig(
            "Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}",
            "Timestamp",
            "yyyy-mm-dd HH:MM:SS",
            nothing,
            mappings
        )

        metadata = parse_column_metadata(df, sensor_config)

        @test length(metadata) == 3
        @test any(m -> m.columnName == Symbol("Ch1_Anem_80m_315_Avg_mps") && m.sensorType == "WindSpeed", metadata)
        @test any(m -> m.columnName == Symbol("Ch2_Vane_80m_315_Avg_deg") && m.sensorType == "WindDirection", metadata)
        @test any(m -> m.columnName == Symbol("Ch3_Analog_80m_Avg_hPa") && m.sensorType == "Pressure" && m.unit == "Pa", metadata)
    end

    @testset "Multiple Matching Rules" begin
        format = "Ch{channel}_{sensorType}_{height}m_{statType}_{unit}"
        mappings = [
            MappingRule(
                Dict("sensorType" => "Anem"),
                RuleOutcome(sensorType="WindSpeed")
            ),
            MappingRule(
                Dict("statType" => "Avg"),
                RuleOutcome(statType="avg")
            ),
            MappingRule(
                Dict("unit" => "mps"),
                RuleOutcome(unit="m/s")
            )
        ]

        result = parse_column_name("Ch1_Anem_80m_Avg_mps", format, mappings)
        @test result !== nothing
        @test result.sensorType == "WindSpeed"
        @test result.statType == "avg"
        @test result.unit == "m/s"
    end

    @testset "Load Preset Format" begin
        mktempdir() do temp_dir
            # Create a temporary format file
            format_path = joinpath(temp_dir, "test.yaml")
            format_config = Dict(
                "column_format" => "Ch{channel}_{sensorType}_{height}m_{statType}_{unit}",
                "timestamp_column" => "Timestamp",
                "timestamp_format" => "yyyy-mm-dd HH:MM:SS",
                "delim" => "\t",
                "mappings" => [
                    Dict(
                        "match" => Dict("sensorType" => "Anem"),
                        "rule" => Dict(
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
            @test sensor_config.column_format == "Ch{channel}_{sensorType}_{height}m_{statType}_{unit}"
            @test sensor_config.timestamp_column == "Timestamp"
            @test sensor_config.delim == "\t"
            @test length(sensor_config.mappings) == 1
            @test sensor_config.mappings[1].rule.sensorType == "WindSpeed"
            @test sensor_config.mappings[1].rule.unit == "m/s"
            @test sensor_config.mappings[1].rule.multiplier == 1.0
        end
    end
end
