# 文件：./test/MastTimeSeries/test_parsing_column.jl

using Test
using YAML
using CleanMastProject.MastTimeSeries
using CleanMastProject.CleanMastConfig
using CleanMastProject.Types.CleanMastConfig
using CleanMastProject.Types.MastTimeSeries

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

    @testset "Parse Column Name" begin
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

    @testset "Parse Column Metadata" begin
        df = DataFrame(
            "Timestamp" => DateTime[],
            "Ch1_Anem_80m_315_Avg_mps" => Float64[],
            "Ch2_Vane_80m_315_Avg_deg" => Float64[],
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
            )
        ]

        format = FormatConfig(
            "Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}",
            "Timestamp",
            "yyyy-mm-dd HH:MM:SS",
            nothing,
            mappings
        )

        sensor_config = SensorConfig(format)
        metadata = parse_column_metadata(df, sensor_config)

        @test length(metadata) == 2
        @test any(m -> m.columnName == Symbol("Ch1_Anem_80m_315_Avg_mps"), metadata)
        @test any(m -> m.columnName == Symbol("Ch2_Vane_80m_315_Avg_deg"), metadata)
    end
end
