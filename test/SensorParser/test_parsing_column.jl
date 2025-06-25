using Test
using YAML
using DataFrames
using Dates
using CleanMastProject.Types.Utils
using CleanMastProject.SensorParser
using CleanMastProject.CleanMastConfig
using CleanMastProject.Types.CleanMastConfig
using CleanMastProject.Types.SensorColumns: SensorColumn

@testset "SensorParser Tests" begin
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
        @test result.columnName == Symbol(original_name)  # No renaming in SensorParser
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
        @test result.columnName == Symbol(original_pressure_name)  # No renaming in SensorParser
        @test result.sensorType == "Pressure"
        @test result.unit == "Pa"
        @test result.multiplier == 100.0

        # Test temperature without conversion
        original_temp_name = "Ch2_Analog_80m_Avg_C"
        result = parse_column_name(original_temp_name, formats, mappings)
        @test result !== nothing
        @test result.originalColumnName == Symbol(original_temp_name)
        @test result.columnName == Symbol(original_temp_name)  # No renaming in SensorParser
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
        @test ws_sensor.columnName == Symbol("Ch1_Anem_80m_315_Avg_mps")  # No renaming in SensorParser
        @test ws_sensor.statType == "avg"
        
        # Check wind direction sensor
        wd_sensor = first(filter(m -> m.sensorType == "WindDirection", metadata))
        @test wd_sensor.originalColumnName == Symbol("Ch2_Vane_80m_315_Avg_deg")
        @test wd_sensor.columnName == Symbol("Ch2_Vane_80m_315_Avg_deg")  # No renaming in SensorParser
        @test wd_sensor.statType == "avg"
        
        # Check pressure sensor
        pressure_sensor = first(filter(m -> m.sensorType == "Pressure", metadata))
        @test pressure_sensor.originalColumnName == Symbol("Ch3_Analog_80m_Avg_hPa")
        @test pressure_sensor.columnName == Symbol("Ch3_Analog_80m_Avg_hPa")  # No renaming in SensorParser
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
        @test result.columnName == Symbol(original_name)  # No renaming in SensorParser
        @test result.sensorType == "WindSpeed"
        @test result.statType == "avg"
        @test result.unit == "m/s"
        @test result.multiplier == 1.0
    end

    @testset "Normalize Timestamp" begin
        df = DataFrame(
            "TimeStamp" => ["2024-01-01 00:00:00", "2024-01-01 00:10:00"],
            "Value" => [1.0, 2.0]
        )
        
        # Test timestamp normalization
        normalize_timestamp!(df, "TimeStamp")
        @test names(df)[1] == "timestamp"  # Check column renamed
        @test eltype(df.timestamp) == DateTime  # Check type conversion
        @test df.timestamp[1] == DateTime(2024,1,1,0,0,0)
        
        # Test error on missing column
        df_bad = DataFrame("Value" => [1.0])
        @test_throws ArgumentError normalize_timestamp!(df_bad, "TimeStamp")
    end

    @testset "Apply Multipliers" begin
        df = DataFrame(
            "timestamp" => [DateTime(2024,1,1)],
            "pressure" => [1013.25],
            "temperature" => [20.0]
        )
        
        sensors = [
            SensorColumn(Symbol("pressure"), "", "Pressure", "", 10.0, "avg", "Pa", 
                        multiplier=100.0, originalColumnName=Symbol("pressure")),
            SensorColumn(Symbol("temperature"), "", "Temperature", "", 10.0, "avg", "C", 
                        multiplier=nothing, originalColumnName=Symbol("temperature"))
        ]
        
        # Apply multipliers
        apply_multipliers!(df, sensors)
        
        # Check values
        @test df.pressure[1] ≈ 101325.0  # 1013.25 * 100
        @test df.temperature[1] == 20.0  # Unchanged
    end

    @testset "String to Regex Conversion" begin
        @test string_to_regex_or_string("/pattern/") isa Regex
        @test string_to_regex_or_string("normal") isa String
        @test string_to_regex_or_string("/^Data/") isa Regex
        @test match(string_to_regex_or_string("/^Data/"), "Data") !== nothing
        @test match(string_to_regex_or_string("/^Data/"), "NotData") === nothing
    end

    @testset "Generate CSV Options" begin
        sensor_config = SensorConfig(
            ["Ch{channel}_{sensorType}_{height}m"],
            "Timestamp",
            "yyyy-mm-dd HH:MM:SS",
            "\t",
            1,
            Vector{MappingRule}()
        )
        
        opts = generate_csv_opts(sensor_config, "")
        @test opts[:skipto] == 2
        @test opts[:header] == 1
        @test opts[:dateformat] == "yyyy-mm-dd HH:MM:SS"
        @test opts[:delim] == "\t"
        
        # Test with regex skip pattern
        sensor_config_regex = SensorConfig(
            ["Ch{channel}_{sensorType}_{height}m"],
            "Timestamp",
            "yyyy-mm-dd HH:MM:SS",
            ",",
            ["/^Data/", "/^Timestamp/"],
            Vector{MappingRule}()
        )
        
        # Note: We can't test the actual regex skip functionality here
        # as it requires a real file to read. That would be better tested
        # in integration tests.
    end
end 