using Test
using DataFrames
using Dates
using CleanMastProject.Types.CleanMastConfig: TimeRange, ProjectConfig, AnalysisConfig
using CleanMastProject.MastTimeSeries
using CleanMastProject.TowerShading

"""Helper functions for creating test data"""
function create_test_config()::ProjectConfig
    sensor_config = SensorConfig(
        "Ch{channel}_{sensorType}_{height}m_{statType}_{unit}",
        "timestamp",
        "yyyy-mm-dd HH:MM:SS",
        ",",
        1,
        MappingRule[]
    )
    
    mast_config = MastConfig(
        "data.csv",
        sensor_config,
        Rule[]
    )
    
    meso_config = MesoConfig(
        "meso.csv",
        sensor_config
    )
    
    analysis_config = AnalysisConfig(
        TimeRange(DateTime("2024-01-01T00:00:00"), DateTime("2024-01-01T00:20:00")),
        nothing,  # target_height
        nothing   # ti_target_height
    )
    
    return ProjectConfig(mast_config, meso_config, analysis_config)
end

function create_test_sensors()::Vector{SensorColumn}
    return [
        SensorColumn(Symbol("Ch1_WindSpeed_60m_avg_m/s"), "WindSpeed", "270", 60.0, "avg", "m/s"),
        SensorColumn(Symbol("Ch2_WindSpeed_60m_avg_m/s"), "WindSpeed", "90", 60.0, "avg", "m/s"),
        SensorColumn(Symbol("Ch1_WindSpeed_60m_sd_m/s"), "WindSpeed", "270", 60.0, "sd", "m/s"),
        SensorColumn(Symbol("Ch2_WindSpeed_60m_sd_m/s"), "WindSpeed", "90", 60.0, "sd", "m/s"),
        SensorColumn(Symbol("Ch1_WindSpeed_40m_avg_m/s"), "WindSpeed", "270", 40.0, "avg", "m/s"),
        SensorColumn(Symbol("Ch1_Temperature_60m_avg_C"), "Temperature", "N/A", 60.0, "avg", "C")
    ]
end

function create_test_data()::TimeSeriesData
    df = DataFrame(
        :timestamp => [
            DateTime("2024-01-01T00:00:00"),
            DateTime("2024-01-01T00:10:00"),
            DateTime("2024-01-01T00:20:00")
        ],
        Symbol("Ch1_WindSpeed_60m_avg_m/s") => [5.0, 6.0, 4.0],
        Symbol("Ch2_WindSpeed_60m_avg_m/s") => [4.5, 7.0, 3.5],
        Symbol("Ch1_WindSpeed_60m_sd_m/s") => [0.5, 0.6, 0.4],
        Symbol("Ch2_WindSpeed_60m_sd_m/s") => [0.4, 0.8, 0.3],
        Symbol("Ch1_WindSpeed_40m_avg_m/s") => [4.0, 5.0, 3.0],
        Symbol("Ch1_Temperature_60m_avg_C") => [20.0, 21.0, 19.0]
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

    @testset "column_name_generation" begin
        config = create_test_config()
        
        @testset "basic name generation" begin
            name = TowerShading.generate_column_name(config, 60.0, "avg")

            @test occursin("WindSpeed", name)
            @test occursin("Ch2", name)
            @test occursin("60m", name)
            @test occursin("avg", name)
            @test occursin("m/s", name)  # Check for unit
        end
        
        @testset "height rounding" begin
            name = TowerShading.generate_column_name(config, 60.4, "avg")
            @test occursin("60m", name)  # Should round to nearest integer
            @test occursin("m/s", name)   # Check for unit
        end
    end

    @testset "merge_wind_speeds!" begin
        config = create_test_config()
        data = create_test_data()
        
        @testset "basic merging" begin
            result = TowerShading.merge_wind_speeds!(data, data.sensors, config)
            
            # Check that new columns were created
            avg_col = find_tower_column(result.df, "WindSpeed_60m_avg_m/s")
            sd_col = find_tower_column(result.df, "WindSpeed_60m_sd_m/s")
            
            # Check that old columns were removed
            @test !(Symbol("Ch1_WindSpeed_60m_avg_m/s") in propertynames(result.df))
            @test !(Symbol("Ch2_WindSpeed_60m_avg_m/s") in propertynames(result.df))
            
            # Check that merged values are maximum of originals
            @test result.df[1, avg_col] == max(5.0, 4.5)
            @test result.df[2, avg_col] == max(6.0, 7.0)
            @test result.df[2, sd_col] == 0.8
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
            original_sensors = filter(s -> s.columnName in [Symbol("Ch1_WindSpeed_60m_avg_m/s"), 
                                                          Symbol("Ch1_WindSpeed_60m_sd_m/s"),
                                                          Symbol("Ch2_WindSpeed_60m_avg_m/s"), 
                                                          Symbol("Ch2_WindSpeed_60m_sd_m/s")],
                                    result.sensors)
            @test isempty(original_sensors)
        end
        
        @testset "non-wind speed columns preserved" begin
            config = create_test_config()
            data = create_test_data()
            result = TowerShading.merge_wind_speeds!(data, data.sensors, config)
            
            # Temperature column should remain unchanged
            @test Symbol("Ch1_Temperature_60m_avg_C") in propertynames(result.df)
            temp_sensor = filter(s -> s.sensorType == "Temperature", result.sensors)
            @test length(temp_sensor) == 1
        end
    end

    @testset "process_tower_shading integration" begin
        config = create_test_config()
        data = create_test_data()
        
        @testset "complete processing" begin
            config = create_test_config()
            data = create_test_data()
            result = TowerShading.process_tower_shading!(config, data)
            
            # Check overall structure
            @test result isa TimeSeriesData
            data = create_test_data()
            @test nrow(result.df) == nrow(data.df)
            @test ncol(result.df) < ncol(data.df)  # Should have fewer columns after merging
            
            # Check that timestamp is preserved
            @test :timestamp in Symbol.(names(result.df))
            @test result.df[1, :timestamp] == data.df[1, :timestamp]
            
            # Verify merged data
            merged_avg = filter(s -> s.statType == "avg" && 
                                   s.sensorType == "WindSpeed" && 
                                   s.height == 60.0,
                              result.sensors)
            @test length(merged_avg) == 1
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
