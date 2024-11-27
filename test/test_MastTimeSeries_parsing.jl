# 文件：./test/test_parsing.jl

using Test
using YAML
using .MastTimeSeries
using .CleanMastConfig

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
        # Setup test mappings
        mappings = SensorMappings(
            Dict("Anem" => "WindSpeed", "Vane" => "WindDirection", "Temp" => "Temperature"),
            Dict("Avg" => "avg", "Max" => "max", "Min" => "min", "SD" => "sd"),
            Dict("m/s" => "speed", "Deg" => "degrees", "C" => "celsius")
        )

        @testset "Standard Wind Speed Column" begin
            format = "Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}"
            result = parse_column_name("Ch1_Anem_120.00m_ESE_Avg_m/s", format, mappings)
            
            @test result !== nothing
            @test result.columnName == "Ch1_Anem_120.00m_ESE_Avg_m/s"
            @test result.sensorType == "WindSpeed"
            @test result.height == 120.00
            @test result.sensorDirection == "ESE"
            @test result.statType == "avg"
        end

        @testset "Wind Direction Column" begin
            format = "Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}"
            result = parse_column_name("Ch13_Vane_80.00m_N_Avg_Deg", format, mappings)
            
            @test result !== nothing
            @test result.sensorType == "WindDirection"
            @test result.height == 80.00
            @test result.sensorDirection == "N"
            @test result.statType == "avg"
        end

        @testset "Minimal Format" begin
            format = "{sensorType}_{height}m"
            result = parse_column_name("Anem_60.00m", format, mappings)
            
            @test result !== nothing
            @test result.sensorType == "WindSpeed"
            @test result.height == 60.00
            @test result.sensorDirection == ""  # Default
            @test result.statType == "avg"      # Default
        end

        @testset "Invalid Formats" begin
            format = "Ch{channel}_{sensorType}_{height}m"
            
            # Missing required fields
            @test parse_column_name("Ch1_120.00m", format, mappings) === nothing
            
            # Invalid height format
            @test parse_column_name("Ch1_Anem_invalid_height", format, mappings) === nothing
            
            # Completely wrong format
            @test parse_column_name("Invalid_Format_String", format, mappings) === nothing
        end

        @testset "Custom Format" begin
            format = "Station_{stationId}_{sensorType}_{height}m_{customField}"
            result = parse_column_name("Station_001_Anem_40.00m_Custom", format, mappings)
            
            @test result !== nothing
            @test result.sensorType == "WindSpeed"
            @test result.height == 40.00
            @test result.sensorDirection == ""  # Default
            @test result.statType == "avg"      # Default
        end
    end
end
