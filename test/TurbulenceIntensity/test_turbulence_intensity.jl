module TestTurbulenceIntensity

using Test
using DataFrames
using Dates
using Statistics
using CleanMastProject.Types.CleanMastConfig: TimeRange, ProjectConfig, AnalysisConfig
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, SensorColumn
using CleanMastProject.TurbulenceIntensity

"""Helper function to create test config"""
function create_test_config(;
    ti_target_height::Union{Nothing, Float64}=nothing,
    target_height::Union{Nothing, Float64}=nothing
)::ProjectConfig
    time_range = TimeRange(nothing, nothing)
    analysis_config = AnalysisConfig(time_range, target_height, ti_target_height)
    
    mapping_rules = MappingRule[]
    sensor_config = SensorConfig(
        "Ch{channel}_{sensorType}_{height}m_{statType}_{unit}",
        "timestamp",
        "yyyy-mm-dd HH:MM:SS",
        mapping_rules
    )
    
    mast_config = MastConfig(
        "data.csv",
        1,
        ",",
        sensor_config,
        Rule[]
    )
    
    meso_config = MesoConfig(
        "data.csv",
        1,
        ",",
        sensor_config
    )
    
    ProjectConfig(mast_config, meso_config, analysis_config)
end

"""Helper function to create test time series data"""
function create_test_data()::TimeSeriesData
    # Create timestamps for 1 hour of 10-minute data
    timestamps = collect(
        DateTime(2024,1,1,0):Minute(10):DateTime(2024,1,1,1)
    )
    
    # Create sensors at different heights
    sensors = [
        # 80m sensors
        SensorColumn(Symbol("Ch1_WindSpeed_80m_avg_m/s"), "WindSpeed", "N", 80.0, "avg", "m/s"),
        SensorColumn(Symbol("Ch1_WindSpeed_80m_sd_m/s"), "WindSpeed", "N", 80.0, "sd", "m/s"),
        SensorColumn(Symbol("Ch1_WindDirection_80m_avg_deg"), "WindDirection", "N", 80.0, "avg", "deg"),
        
        # 100m sensors
        SensorColumn(Symbol("Ch2_WindSpeed_100m_avg_m/s"), "WindSpeed", "N", 100.0, "avg", "m/s"),
        SensorColumn(Symbol("Ch2_WindSpeed_100m_sd_m/s"), "WindSpeed", "N", 100.0, "sd", "m/s"),
        SensorColumn(Symbol("Ch2_WindDirection_100m_avg_deg"), "WindDirection", "N", 100.0, "avg", "deg"),
        
        # 120m sensors
        SensorColumn(Symbol("Ch3_WindSpeed_120m_avg_m/s"), "WindSpeed", "N", 120.0, "avg", "m/s"),
        SensorColumn(Symbol("Ch3_WindSpeed_120m_sd_m/s"), "WindSpeed", "N", 120.0, "sd", "m/s"),
        SensorColumn(Symbol("Ch3_WindDirection_120m_avg_deg"), "WindDirection", "N", 120.0, "avg", "deg")
    ]
    
    # Create DataFrame with controlled test data
    df = DataFrame(timestamp = timestamps)
    
    # Add wind speed data with known TI values
    # For 80m: TI ≈ 0.1 for speed 8-10 m/s in N sector
    df[!, Symbol("Ch1_WindSpeed_80m_avg_m/s")] = repeat([9.0], length(timestamps))
    df[!, Symbol("Ch1_WindSpeed_80m_sd_m/s")] = repeat([0.9], length(timestamps))
    df[!, Symbol("Ch1_WindDirection_80m_avg_deg")] = repeat([0.0], length(timestamps))  # North
    
    # For 100m: TI ≈ 0.15 for speed 10-12 m/s in NE sector
    df[!, Symbol("Ch2_WindSpeed_100m_avg_m/s")] = repeat([11.0], length(timestamps))
    df[!, Symbol("Ch2_WindSpeed_100m_sd_m/s")] = repeat([1.65], length(timestamps))
    df[!, Symbol("Ch2_WindDirection_100m_avg_deg")] = repeat([45.0], length(timestamps))  # NE
    
    # For 120m: TI ≈ 0.2 for speed 12-14 m/s in E sector
    df[!, Symbol("Ch3_WindSpeed_120m_avg_m/s")] = repeat([13.0], length(timestamps))
    df[!, Symbol("Ch3_WindSpeed_120m_sd_m/s")] = repeat([2.6], length(timestamps))
    df[!, Symbol("Ch3_WindDirection_120m_avg_deg")] = repeat([90.0], length(timestamps))  # East
    
    TimeSeriesData(df, sensors)
end

@testset "TurbulenceIntensity" begin
    @testset "find_ti_sensors" begin
        ts = create_test_data()
        
        # Test exact height match
        ws_avg, ws_sd, wd = find_ti_sensors(ts, 100.0)
        @test ws_avg.height == 100.0
        @test ws_sd.height == 100.0
        @test wd.height == 100.0
        
        # Test nearest height
        ws_avg, ws_sd, wd = find_ti_sensors(ts, 110.0)
        @test ws_avg.height == 120.0  # Should pick closest
        @test ws_sd.height == 120.0
        @test wd.height == 120.0
        
        # Test height with no sensors
        ws_avg, ws_sd, wd = find_ti_sensors(ts, 200.0)
        @test ws_avg.height == 120.0  # Should pick closest available
        @test ws_sd.height == 120.0
        @test wd.height == 120.0
    end
    
    @testset "calculate_ti_matrix" begin
        ts = create_test_data()
        
        # Test with explicit ti_target_height
        config = create_test_config(ti_target_height=80.0)
        result = calculate_ti_matrix(config, ts)
        
        # Check structure
        @test size(result, 2) == 18  # min_speed, max_speed, and 16 direction sectors
        @test names(result)[1:2] == ["min_speed", "max_speed"]
        @test all(sector in DIRECTION_SECTORS for sector in names(result)[3:end])
        
        # Check known TI values
        # Find row for 8-10 m/s bin
        row_80m = findfirst(i -> 8.0 <= result.min_speed[i] < 10.0, 1:nrow(result))
        @test !ismissing(result[row_80m, "N"])
        @test isapprox(result[row_80m, "N"], 0.1, atol=0.01)
        
        # Test with target_height fallback
        config = create_test_config(target_height=100.0)
        result = calculate_ti_matrix(config, ts)
        
        # Check known TI values for 100m
        row_100m = findfirst(i -> 10.0 <= result.min_speed[i] < 12.0, 1:nrow(result))
        @test !ismissing(result[row_100m, "NE"])
        @test isapprox(result[row_100m, "NE"], 0.15, atol=0.01)
        
        # Test with default height (120m)
        config = create_test_config()
        result = calculate_ti_matrix(config, ts)
        
        # Check known TI values for 120m
        row_120m = findfirst(i -> 12.0 <= result.min_speed[i] < 14.0, 1:nrow(result))
        @test !ismissing(result[row_120m, "E"])
        @test isapprox(result[row_120m, "E"], 0.2, atol=0.01)
        
        # Check that sectors with no data are missing
        @test ismissing(result[row_120m, "N"])
        @test ismissing(result[row_120m, "S"])
        
        # Test with custom wind speed bins
        custom_bins = [0.0, 5.0, 10.0, 15.0, 20.0]
        result = calculate_ti_matrix(config, ts, custom_bins)
        
        # Check structure with custom bins
        @test size(result, 1) == length(custom_bins) - 1
        @test all(result.min_speed .== custom_bins[1:end-1])
        @test all(result.max_speed .== custom_bins[2:end])
        
        # Check TI values in custom bins
        row_120m = findfirst(i -> 10.0 <= result.min_speed[i] < 15.0, 1:nrow(result))
        @test !ismissing(result[row_120m, "E"])
        @test isapprox(result[row_120m, "E"], 0.2, atol=0.01)
    end
end

end # module 