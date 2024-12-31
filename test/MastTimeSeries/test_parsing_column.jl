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
        
        # Test valid matches
        @test match(regex, "Ch1_Anem_120.00m") !== nothing
        @test match(regex, "Ch2_Vane_80.00m") !== nothing
        
        # Test invalid matches
        @test match(regex, "Ch1_Anem_120.00m_extra") === nothing
        @test match(regex, "Wrong_Anem_120.00m") === nothing
    end

    @testset "Parse Column Name" begin
        # Setup test mapping rules
        rules = [
            MappingRule(
                Dict("sensorType" => "Anem"),
                RuleOutcome(sensorType="WindSpeed", unit="m/s")
            ),
            MappingRule(
                Dict("sensorType" => "Vane"),
                RuleOutcome(sensorType="WindDirection", unit="Deg")
            ),
            MappingRule(
                Dict("sensorType" => "Temp"),
                RuleOutcome(sensorType="Temperature", unit="C")
            ),
            MappingRule(
                Dict("statType" => "Avg"),
                RuleOutcome(statType="avg")
            ),
            MappingRule(
                Dict("statType" => "Max"),
                RuleOutcome(statType="max")
            ),
            MappingRule(
                Dict("statType" => "Min"),
                RuleOutcome(statType="min")
            ),
            MappingRule(
                Dict("statType" => "SD"),
                RuleOutcome(statType="sd")
            )
        ]

        @testset "Standard Wind Speed Column" begin
            format = "Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}"
            result = parse_column_name("Ch1_Anem_120.00m_ESE_Avg_m/s", format, rules)
            
            @test result !== nothing
            @test result.columnName == Symbol("Ch1_Anem_120.00m_ESE_Avg_m/s")
            @test result.sensorType == "WindSpeed"
            @test result.height == 120.00
            @test result.sensorDirection == "ESE"
            @test result.statType == "avg"
        end

        @testset "Wind Direction Column" begin
            format = "Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}"
            result = parse_column_name("Ch13_Vane_80.00m_N_Avg_Deg", format, rules)
            
            @test result !== nothing
            @test result.sensorType == "WindDirection"
            @test result.height == 80.00
            @test result.sensorDirection == "N"
            @test result.statType == "avg"
        end

        @testset "Minimal Format" begin
            format = "{sensorType}_{height}m"
            result = parse_column_name("Anem_60.00m", format, rules)
            
            @test result !== nothing
            @test result.sensorType == "WindSpeed"
            @test result.height == 60.00
            @test result.sensorDirection == ""  # Default
            @test result.statType == "avg"
        end

        @testset "Invalid Formats" begin
            format = "Ch{channel}_{sensorType}_{height}m"
            
            @test parse_column_name("Ch1_120.00m", format, rules) === nothing
            @test parse_column_name("Ch1_Anem_invalid_height", format, rules) === nothing
            @test parse_column_name("Invalid_Format_String", format, rules) === nothing
        end

        @testset "Custom Format" begin
            format = "Station_{stationId}_{sensorType}_{height}m_{customField}"
            result = parse_column_name("Station_001_Anem_40.00m_Custom", format, rules)
            
            @test result !== nothing
            @test result.sensorType == "WindSpeed"
            @test result.height == 40.00
            @test result.sensorDirection == ""  # Default
            @test result.statType == "avg"
        end
    end
end
