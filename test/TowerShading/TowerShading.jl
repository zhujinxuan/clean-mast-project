using Test
using DataFrames
using Dates
using CleanMastProject.Types.CleanMastConfig: ConfigTimeRange, ProjectConfig, AnalysisConfig, MastConfig, MesoConfig
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.TowerShading

"""Helper functions for creating test data"""
function create_test_config()::ProjectConfig
    mast_config = MastConfig(
        "test-mast",
    )
    
    meso_config = MesoConfig(
        "test-meso"
    )
    
    analysis_config = AnalysisConfig(
        ConfigTimeRange(DateTime("2024-01-01T00:00:00"), DateTime("2024-01-01T00:20:00"))
    )
    
    return ProjectConfig(mast_config, meso_config, analysis_config)
end

function create_test_sensors()::Vector{SensorColumn}
    return [
        SensorColumn(Symbol("Ch1_WindSpeed_60m_270_avg_m/s"), "WindSpeed", "270", 60.0, "avg", "m/s"),
        SensorColumn(Symbol("Ch2_WindSpeed_60m_90_avg_m/s"), "WindSpeed", "90", 60.0, "avg", "m/s"),
        SensorColumn(Symbol("Ch1_WindSpeed_60m_270_sd_m/s"), "WindSpeed", "270", 60.0, "sd", "m/s"),
        SensorColumn(Symbol("Ch2_WindSpeed_60m_90_sd_m/s"), "WindSpeed", "90", 60.0, "sd", "m/s"),
        SensorColumn(Symbol("Ch1_WindSpeed_40m_270_avg_m/s"), "WindSpeed", "270", 40.0, "avg", "m/s"),
        SensorColumn(Symbol("Ch1_Temperature_60m_N/A_avg_C"), "Temperature", "N/A", 60.0, "avg", "C")
    ]
end

function create_test_data()::TimeSeriesData
    df = DataFrame(
        :timestamp => [
            DateTime("2024-01-01T00:00:00"),
            DateTime("2024-01-01T00:10:00"),
            DateTime("2024-01-01T00:20:00")
        ],
        Symbol("Ch1_WindSpeed_60m_270_avg_m/s") => [5.0, 6.0, 4.0],
        Symbol("Ch2_WindSpeed_60m_90_avg_m/s") => [4.5, 7.0, 3.5],
        Symbol("Ch1_WindSpeed_60m_270_sd_m/s") => [0.5, 0.6, 0.4],
        Symbol("Ch2_WindSpeed_60m_90_sd_m/s") => [0.4, 0.8, 0.3],
        Symbol("Ch1_WindSpeed_40m_270_avg_m/s") => [4.0, 5.0, 3.0],
        Symbol("Ch1_Temperature_60m_N/A_avg_C") => [20.0, 21.0, 19.0]
    )
    
    return TimeSeriesData(df, create_test_sensors())
end

function find_tower_column(df::DataFrame, suffix::String)
    # Find columns that start with "Ch" followed by digits
    pattern = r"Ch(\d+)_(.+)"
    matching_cols = filter(col -> occursin(pattern, String(col)), propertynames(df))
    
    for col in matching_cols
        m = match(pattern, String(col))
        if m !== nothing
            number = parse(Int, m.captures[1])
            col_suffix = m.captures[2]
            if number >= 200 && col_suffix == suffix
                return col
            end
        end
    end
    error("No column found matching pattern Ch{200+}_$suffix")
end

@testset "TowerShading" begin
    @testset "find_nearby_sensors" begin
        sensors = create_test_sensors()
        
        @testset "exact height match" begin
            nearby = TowerShading.find_nearby_sensors("WindSpeed", sensors, 60.0)
            @test length(nearby) == 4  # Should find all 60m sensors
            @test all(sensors[i].height == 60.0 for i in nearby)
        end
        
        @testset "within tolerance" begin
            nearby = TowerShading.find_nearby_sensors("WindSpeed", sensors, 61.0, 2.0)
            @test length(nearby) == 4  # Should still find 60m sensors
        end
        
        @testset "outside tolerance" begin
            nearby = TowerShading.find_nearby_sensors("WindSpeed", sensors, 65.0, 2.0)
            @test isempty(nearby)  # Should find no sensors
        end
    end

    @testset "get_preferred_height" begin
        @testset "multiple of 10" begin
            heights = [59.5, 60.2]
            @test TowerShading.get_preferred_height(heights) == 60.0
        end
        
        @testset "not multiple of 10" begin
            heights = [58.3, 59.1]
            @test TowerShading.get_preferred_height(heights) == 59.0
        end
        
        @testset "single height" begin
            heights = [45.0]
            @test TowerShading.get_preferred_height(heights) == 45.0
        end
    end

    @testset "create_merged_sensor" begin
        sensors = create_test_sensors()
        
        @testset "basic merging" begin
            stat_sensors = filter(s -> s.height == 60.0 && s.statType == "avg", sensors)
            new_sensor = TowerShading.create_merged_sensor(stat_sensors, 60.0)
            
            @test new_sensor.columnName == Symbol("WindSpeed_60m_avg_m/s")
            @test new_sensor.sensorType == "WindSpeed"
            @test new_sensor.sensorDirection == "N/A"
            @test new_sensor.height == 60.0
            @test new_sensor.statType == "avg"
            @test new_sensor.unit == "m/s"
        end
        
        @testset "height rounding" begin
            stat_sensors = filter(s -> s.height == 60.0 && s.statType == "avg", sensors)
            new_sensor = TowerShading.create_merged_sensor(stat_sensors, 60.0)
            
            @test occursin("60m", String(new_sensor.columnName))
            @test new_sensor.height == 60.0
        end
    end

    @testset "merge_wind_speeds!" begin
        @testset "basic merging" begin
            config = create_test_config()
            data = create_test_data()
            result = TowerShading.merge_wind_speeds!(data, data.sensors, config)
            
            # Check that new columns were created
            merged_avg = filter(s -> s.statType == "avg" && s.height == 60.0 && s.sensorType == "WindSpeed", result.sensors)
            @test length(merged_avg) == 1
            @test merged_avg[1].columnName == Symbol("WindSpeed_60m_avg_m/s")
            
            # Check that old columns were removed
            @test !(Symbol("Ch1_WindSpeed_60m_270_avg_m/s") in propertynames(result.df))
            @test !(Symbol("Ch2_WindSpeed_60m_90_avg_m/s") in propertynames(result.df))
            
            # Check that merged values are maximum of originals
            @test result.df[1, Symbol("WindSpeed_60m_avg_m/s")] == max(5.0, 4.5)
            @test result.df[2, Symbol("WindSpeed_60m_avg_m/s")] == max(6.0, 7.0)
        end
        
        @testset "sensor metadata" begin
            config = create_test_config()
            data = create_test_data()
            result = TowerShading.merge_wind_speeds!(data, data.sensors, config)
            
            # Check that new sensors were added
            merged_sensors = filter(s -> s.sensorDirection == "N/A" && 
                                       s.sensorType == "WindSpeed", 
                                  result.sensors)
            @test !isempty(merged_sensors)
            
            # Check that old sensors were removed
            original_sensors = filter(s -> s.columnName in [Symbol("Ch1_WindSpeed_60m_270_avg_m/s"), 
                                                          Symbol("Ch1_WindSpeed_60m_270_sd_m/s"),
                                                          Symbol("Ch2_WindSpeed_60m_90_avg_m/s"), 
                                                          Symbol("Ch2_WindSpeed_60m_90_sd_m/s")],
                                    result.sensors)
            @test isempty(original_sensors)
        end
        
        @testset "non-wind speed columns preserved" begin
            config = create_test_config()
            data = create_test_data()
            result = TowerShading.merge_wind_speeds!(data, data.sensors, config)
            
            # Temperature column should remain unchanged
            @test Symbol("Ch1_Temperature_60m_N/A_avg_C") in propertynames(result.df)
            temp_sensor = filter(s -> s.sensorType == "Temperature", result.sensors)
            @test length(temp_sensor) == 1
        end
    end

    @testset "calculate_max_between_columns" begin
        df = DataFrame(
            col1 = [1.0, missing, 3.0, missing],
            col2 = [missing, 2.0, 5.0, missing],
            col3 = [2.0, 1.0, 4.0, missing]
        )
        
        @testset "basic functionality" begin
            result = TowerShading.calculate_max_between_columns(df, [:col1, :col2, :col3])
            @test isequal(result, [2.0, 2.0, 5.0, missing])
        end
        
        @testset "subset of columns" begin
            result = TowerShading.calculate_max_between_columns(df, [:col1, :col2])
            @test isequal(result, [1.0, 2.0, 5.0, missing])
        end
        
        @testset "single column" begin
            result = TowerShading.calculate_max_between_columns(df, [:col1])
            @test isequal(result, [1.0, missing, 3.0, missing])
        end
        
        @testset "all missing row" begin
            df_with_missing = DataFrame(
                col1 = [1.0, missing],
                col2 = [2.0, missing]
            )
            result = TowerShading.calculate_max_between_columns(df_with_missing, [:col1, :col2])
            @test isequal(result, [2.0, missing])
        end
    end
end
