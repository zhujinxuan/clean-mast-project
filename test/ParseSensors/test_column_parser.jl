# test/ParseSensors/test_column_parser.jl

using Test
using CleanMastProject.ParseSensors.ColumnParser
using CleanMastProject.Types.ParseSensorsConfig: SensorColumnConfig, MappingRule, RuleOutcome, PatternConfig
using CleanMastProject.Types.SensorColumns: ParsedSensor

@testset "ColumnParser Tests" begin
    
    @testset "Placeholder Extraction" begin
        format = "Ch{channel}_{sensorType}_{height}m_{sensorDirection}"
        placeholders = extract_format_placeholders(format)
        @test placeholders == ["channel", "sensorType", "height", "sensorDirection"]
    end

    @testset "Regex Creation from Match" begin
        format = "Type{sensorType}_H{height}"
        placeholders = ["sensorType", "height"]
        patterns = Dict("sensorType" => "[A-Z]+", "height" => "[0-9]+")
        
        regex = create_regex_from_match(format, placeholders, patterns)
        
        @test regex == r"^Type(?<sensorType>[A-Z]+)_H(?<height>[0-9]+)$"
        
        m = match(regex, "TypeWS_H120")
        @test m[:sensorType] == "WS"
        @test m[:height] == "120"
    end

    @testset "Basic Column Parsing (from legacy tests)" begin
        column_configs = [
            SensorColumnConfig(
                "Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}",
                "{sensorType}_{height}m_{statType}_{sensorDirection} [{unit}]",
                nothing
            )
        ]
        mappings = [
            MappingRule(Dict("sensorType" => "Anem"), RuleOutcome(sensorType="WindSpeed", unit="m/s")),
            MappingRule(Dict("sensorType" => "Vane"), RuleOutcome(sensorType="WindDirection", unit="deg")),
            MappingRule(Dict("statType" => "Avg"), RuleOutcome(statType="avg"))
        ]

        original_name = "Ch1_Anem_80m_315_Avg_mps"
        result = parse_column_name(original_name, column_configs, mappings)
        
        @test result !== nothing
        @test result.originalColumnName == Symbol(original_name)
        @test result.sensorType == "WindSpeed"
        @test result.height == 80.0
        @test result.sensorDirection == "315"
        @test result.statType == "avg"
        @test result.unit == "m/s"
        # Test the new formatted name
        @test result.columnName == Symbol("WindSpeed_80m_avg_315 [m/s]")
    end

    @testset "Parsing with Unit Conversion (from legacy tests)" begin
        column_configs = [
            SensorColumnConfig(
                "Ch{channel}_{sensorType}_{height}m_{statType}_{unit}",
                "{sensorType}_{height}m_{statType} [{unit}]",
                nothing
            )
        ]
        mappings = [
            MappingRule(Dict("sensorType" => "Analog", "unit" => "hPa"), RuleOutcome(sensorType="Pressure", unit="Pa", multiplier=100.0)),
            MappingRule(Dict("statType" => "Avg"), RuleOutcome(statType="avg"))
        ]

        original_name = "Ch1_Analog_80m_Avg_hPa"
        result = parse_column_name(original_name, column_configs, mappings)

        @test result !== nothing
        @test result.sensorType == "Pressure"
        @test result.unit == "Pa"
        @test result.multiplier == 100.0
        @test result.columnName == Symbol("Pressure_80m_avg [Pa]")
    end

    @testset "Column Parsing with Custom Regex Patterns" begin
        column_configs = [
            SensorColumnConfig(
                "{sensorType}_{height}{direction}",
                "WindSpeed_{height}m_{sensorDirection}",
                PatternConfig(Dict("direction" => "[AB]"))
            )
        ]
        mappings = [
            MappingRule(Dict("direction" => "A"), RuleOutcome(sensorDirection="A")),
            MappingRule(Dict("direction" => "B"), RuleOutcome(sensorDirection="B"))
        ]
        
        result_A = parse_column_name("WS_120A", column_configs, mappings)
        @test result_A !== nothing
        @test result_A.sensorType == "WS"
        @test result_A.height == 120.0
        @test result_A.sensorDirection == "A"
        @test result_A.columnName == Symbol("WindSpeed_120m_A")

        result_B = parse_column_name("WS_100B", column_configs, mappings)
        @test result_B !== nothing
        @test result_B.sensorDirection == "B"

        result_C = parse_column_name("WS_80C", column_configs, mappings)
        @test result_C === nothing
    end

end 