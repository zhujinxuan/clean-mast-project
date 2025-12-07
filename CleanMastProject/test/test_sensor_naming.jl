module TestSensorNaming

using Test
using CleanMastProject.Types.SensorColumns: SensorColumn, create_sensor_short_name, get_sensor_style_short_name

@testset "Sensor Naming Conventions" begin
    
    @testset "get_sensor_style_short_name" begin
        # Test standard sensor type mappings
        @test get_sensor_style_short_name("WindSpeed") == "WS"
        @test get_sensor_style_short_name("WindDirection") == "WD"
        @test get_sensor_style_short_name("Temperature") == "TEMP"
        @test get_sensor_style_short_name("Pressure") == "PRES"
        @test get_sensor_style_short_name("Humidity") == "HUM"
        @test get_sensor_style_short_name("SolarRadiation") == "RAD"
        @test get_sensor_style_short_name("Precipitation") == "PREC"
        
        # Test unknown sensor type (should return original)
        @test get_sensor_style_short_name("UnknownSensor") == "UnknownSensor"
        @test get_sensor_style_short_name("CustomType") == "CustomType"
    end
    
    @testset "create_sensor_short_name - Average Sensors" begin
        # Average wind speed sensor with direction
        ws_sensor = SensorColumn(
            columnName = :WS_120m_N_avg,
            sensorType = "WindSpeed",
            sensorDirection = "N",
            height = 120.0,
            statType = "avg",
            unit = "m/s"
        )
        @test create_sensor_short_name(ws_sensor) == "WS:120m:N"
        
        # Average wind direction sensor with direction  
        wd_sensor = SensorColumn(
            columnName = :WD_100m_S_avg,
            sensorType = "WindDirection", 
            sensorDirection = "S",
            height = 100.0,
            statType = "avg",
            unit = "deg"
        )
        @test create_sensor_short_name(wd_sensor) == "WD:100m:S"
        
        # Average sensor without direction (N/A)
        temp_sensor = SensorColumn(
            columnName = :TEMP_10m_avg,
            sensorType = "Temperature",
            sensorDirection = "N/A", 
            height = 10.0,
            statType = "avg",
            unit = "°C"
        )
        @test create_sensor_short_name(temp_sensor) == "TEMP:10m"
        
        # Test fractional height
        pressure_sensor = SensorColumn(
            columnName = :PRES_2_5m_avg,
            sensorType = "Pressure",
            sensorDirection = "N/A",
            height = 2.5,
            statType = "avg", 
            unit = "hPa"
        )
        @test create_sensor_short_name(pressure_sensor) == "PRES:2.5m"
    end
    
    @testset "create_sensor_short_name - Non-Average Sensors" begin
        # Maximum wind speed sensor with direction
        ws_max_sensor = SensorColumn(
            columnName = :WS_120m_N_max,
            sensorType = "WindSpeed",
            sensorDirection = "N",
            height = 120.0,
            statType = "max",
            unit = "m/s"
        )
        @test create_sensor_short_name(ws_max_sensor) == "WS:120m:N:max"
        
        # Minimum wind speed sensor with direction
        ws_min_sensor = SensorColumn(
            columnName = :WS_80m_E_min,
            sensorType = "WindSpeed", 
            sensorDirection = "E",
            height = 80.0,
            statType = "min",
            unit = "m/s"
        )
        @test create_sensor_short_name(ws_min_sensor) == "WS:80m:E:min"
        
        # Standard deviation sensor without direction
        ws_std_sensor = SensorColumn(
            columnName = :WS_60m_std,
            sensorType = "WindSpeed",
            sensorDirection = "N/A",
            height = 60.0,
            statType = "std", 
            unit = "m/s"
        )
        @test create_sensor_short_name(ws_std_sensor) == "WS:60m:std"
        
        # Custom statType with direction
        custom_sensor = SensorColumn(
            columnName = :TEMP_40m_NE_p95,
            sensorType = "Temperature",
            sensorDirection = "NE", 
            height = 40.0,
            statType = "p95",
            unit = "°C"
        )
        @test create_sensor_short_name(custom_sensor) == "TEMP:40m:NE:p95"
    end
    
    @testset "create_sensor_short_name - Edge Cases" begin
        # Test complex direction
        complex_dir_sensor = SensorColumn(
            columnName = :WS_140m_NNE_avg,
            sensorType = "WindSpeed",
            sensorDirection = "NNE",
            height = 140.0,
            statType = "avg",
            unit = "m/s"
        )
        @test create_sensor_short_name(complex_dir_sensor) == "WS:140m:NNE"
        
        # Test unknown sensor type
        unknown_sensor = SensorColumn(
            columnName = :CUSTOM_50m_W_avg,
            sensorType = "CustomSensorType",
            sensorDirection = "W",
            height = 50.0,
            statType = "avg", 
            unit = "units"
        )
        @test create_sensor_short_name(unknown_sensor) == "CustomSensorType:50m:W"
        
        # Test zero height
        zero_height_sensor = SensorColumn(
            columnName = :PRES_0m_avg,
            sensorType = "Pressure",
            sensorDirection = "N/A",
            height = 0.0,
            statType = "avg",
            unit = "hPa"
        )
        @test create_sensor_short_name(zero_height_sensor) == "PRES:0m"
        
        # Test large height
        high_sensor = SensorColumn(
            columnName = :WS_250m_N_avg,
            sensorType = "WindSpeed",
            sensorDirection = "N",
            height = 250.0,
            statType = "avg",
            unit = "m/s"
        )
        @test create_sensor_short_name(high_sensor) == "WS:250m:N"
    end
    
    @testset "create_sensor_short_name - Documentation Examples" begin
        # Test examples from documentation
        
        # ✅ Correct Examples from docs:
        # WS:140m:N (avg wind speed)
        ws_example = SensorColumn(
            columnName = :test, sensorType = "WindSpeed", sensorDirection = "N",
            height = 140.0, statType = "avg", unit = "m/s"
        )
        @test create_sensor_short_name(ws_example) == "WS:140m:N"
        
        # WD:120m (avg wind direction, no direction)
        wd_example = SensorColumn(
            columnName = :test, sensorType = "WindDirection", sensorDirection = "N/A", 
            height = 120.0, statType = "avg", unit = "deg"
        )
        @test create_sensor_short_name(wd_example) == "WD:120m"
        
        # TEMP:10m:max (max temperature with direction)
        temp_max_example = SensorColumn(
            columnName = :test, sensorType = "Temperature", sensorDirection = "N/A",
            height = 10.0, statType = "max", unit = "°C"
        )
        @test create_sensor_short_name(temp_max_example) == "TEMP:10m:max"
        
        # WS:80m:E:std (std wind speed with direction)
        ws_std_example = SensorColumn(
            columnName = :test, sensorType = "WindSpeed", sensorDirection = "E",
            height = 80.0, statType = "std", unit = "m/s" 
        )
        @test create_sensor_short_name(ws_std_example) == "WS:80m:E:std"
    end
end

end # module