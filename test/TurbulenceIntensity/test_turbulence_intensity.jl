module TestTurbulenceIntensity

using Test
using DataFrames
using Dates
using Statistics
using CSV
using CleanMastProject.Types.CleanMastConfig: ConfigTimeRange, ProjectConfig, AnalysisConfig, MappingRule, SensorConfig, MastConfig, MesoConfig, Rule
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, SensorColumn
using CleanMastProject.Types.Sector: DIRECTION_16_SECTORS
using CleanMastProject.Types.TurbulenceIntensity: TurbulenceSectorStats, TurbulenceResults
using CleanMastProject.TurbulenceIntensity

"""Helper function to create test config"""
function create_test_config(;
    ti_target_height::Union{Nothing, Float64}=nothing,
    target_height::Union{Nothing, Float64}=nothing,
    data_path::String="data.csv"
)::ProjectConfig
    time_range = ConfigTimeRange(nothing, nothing)
    
    # Convert single values to vectors for the new AnalysisConfig structure
    target_heights = isnothing(target_height) ? Float64[] : [target_height]
    ti_target_heights = isnothing(ti_target_height) ? Float64[] : [ti_target_height]
    
    analysis_config = AnalysisConfig(time_range, target_heights, ti_target_heights)
    
    sensor_config = SensorConfig(
        ["Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}"],
        "Timestamp",
        "yyyy-mm-dd HH:MM:SS",
        nothing,
        1,
        MappingRule[]
    )
    
    mast_config = MastConfig(
        data_path,
        sensor_config,
        Rule[]
    )
    
    meso_config = MesoConfig(
        "meso.csv",
        sensor_config
    )
    
    ProjectConfig(mast_config, meso_config, analysis_config)
end

"""Helper function to create test time series data"""
function create_test_data(;with_missing::Bool=false)::TimeSeriesData
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
        SensorColumn(Symbol("Ch3_WindDirection_120m_avg_deg"), "WindDirection", "N", 120.0, "avg", "deg"),
    ]
    
    # Create DataFrame with controlled test data
    df = DataFrame(timestamp = timestamps)
    
    # Add wind speed data with known TI values
    # For 80m: TI ≈ 0.1 for speed 8-10 m/s in N sector
    df[!, Symbol("Ch1_WindSpeed_80m_avg_m/s")] = Vector{Union{Float64, Missing}}(repeat([9.0], length(timestamps)))
    df[!, Symbol("Ch1_WindSpeed_80m_sd_m/s")] = Vector{Union{Float64, Missing}}(repeat([0.9], length(timestamps)))
    df[!, Symbol("Ch1_WindDirection_80m_avg_deg")] = Vector{Union{Float64, Missing}}(repeat([0.0], length(timestamps)))  # North
    
    # For 100m: TI ≈ 0.15 for speed 10-12 m/s in NE sector
    df[!, Symbol("Ch2_WindSpeed_100m_avg_m/s")] = Vector{Union{Float64, Missing}}(repeat([11.0], length(timestamps)))
    df[!, Symbol("Ch2_WindSpeed_100m_sd_m/s")] = Vector{Union{Float64, Missing}}(repeat([1.65], length(timestamps)))
    df[!, Symbol("Ch2_WindDirection_100m_avg_deg")] = Vector{Union{Float64, Missing}}(repeat([45.0], length(timestamps)))  # NE
    
    # For 120m: TI ≈ 0.2 for speed 12-14 m/s in E sector
    df[!, Symbol("Ch3_WindSpeed_120m_avg_m/s")] = Vector{Union{Float64, Missing}}(repeat([13.0], length(timestamps)))
    df[!, Symbol("Ch3_WindSpeed_120m_sd_m/s")] = Vector{Union{Float64, Missing}}(repeat([2.6], length(timestamps)))
    df[!, Symbol("Ch3_WindDirection_120m_avg_deg")] = Vector{Union{Float64, Missing}}(repeat([90.0], length(timestamps)))  # East
    
    if with_missing
        # Add some missing values
        df[3, Symbol("Ch1_WindSpeed_80m_avg_m/s")] = missing
        df[4, Symbol("Ch1_WindDirection_80m_avg_deg")] = missing
    end
    
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
        ws_avg, ws_sd, wd = find_ti_sensors(ts, 111.0)
        @test ws_avg.height == 120.0  # Should pick closest
        @test ws_sd.height == 120.0
        @test wd.height == 120.0
        
        # Test height with no sensors
        ws_avg, ws_sd, wd = find_ti_sensors(ts, 200.0)
        @test ws_avg.height == 120.0  # Should pick closest available
        @test ws_sd.height == 120.0
        @test wd.height == 120.0
    end
    
    @testset "calculate_ti_series" begin
        ts = create_test_data()
        ws_avg, ws_sd, wd = find_ti_sensors(ts, 80.0)
        
        ti_df = calculate_ti_series(ts.df, ws_avg.columnName, ws_sd.columnName, wd.columnName)
        
        # Check structure
        @test names(ti_df) == ["ws_avg", "ws_sd", "wd", "ti", "sector"]
        
        # Check TI calculation
        @test all(ti_df.ti .≈ 0.1)  # For 80m data
        @test all(ti_df.sector .== "N")  # All in North sector
        
        # Test missing value handling
        ts_missing = create_test_data(with_missing=true)
        ti_df_missing = calculate_ti_series(ts_missing.df, ws_avg.columnName, ws_sd.columnName, wd.columnName)
        @test ismissing(ti_df_missing.ti[3])  # Missing due to missing wind speed
        @test ismissing(ti_df_missing.sector[4])  # Missing due to missing direction
    end
    
    @testset "calculate_sector_stats" begin
        ts = create_test_data()
        ws_avg, ws_sd, wd = find_ti_sensors(ts, 80.0)
        ti_df = calculate_ti_series(ts.df, ws_avg.columnName, ws_sd.columnName, wd.columnName)
        
        sector_stats = calculate_sector_stats(ti_df)
        
        # Check structure
        @test sector_stats isa TurbulenceSectorStats
        @test names(sector_stats.sector_stats) == ["sector", "mean_speed", "ti", "std", "occurrence"]
        
        # Check values for North sector
        north_stats = first(sector_stats.sector_stats[map(s -> isequal(s, "N"), sector_stats.sector_stats.sector), :])
        @test north_stats.mean_speed ≈ 9.0
        @test north_stats.ti ≈ 0.1
        @test north_stats.occurrence == 7  # Number of timestamps
        
        # Check overall statistics
        @test sector_stats.mean_ti ≈ 0.1
        @test sector_stats.representative_ti ≈ sector_stats.mean_ti + sector_stats.std_ti
        
        # Test missing value handling
        ts_missing = create_test_data(with_missing=true)
        ti_df_missing = calculate_ti_series(ts_missing.df, ws_avg.columnName, ws_sd.columnName, wd.columnName)
        sector_stats_missing = calculate_sector_stats(ti_df_missing)
        north_stats_missing = first(sector_stats_missing.sector_stats[map(s -> isequal(s, "N"), sector_stats_missing.sector_stats.sector), :])
        @test north_stats_missing.occurrence == 5  # Two less due to missing values
    end
    
    @testset "calculate_ti_matrix" begin
        ts = create_test_data()
        ws_avg, ws_sd, wd = find_ti_sensors(ts, 80.0)
        ti_df = calculate_ti_series(ts.df, ws_avg.columnName, ws_sd.columnName, wd.columnName)
        sector_stats = calculate_sector_stats(ti_df)
        
        # Test with default bins
        result = calculate_ti_matrix(ti_df, DEFAULT_WIND_SPEED_BINS, sector_stats.mean_ti)
        
        # Check structure
        @test size(result, 2) == 18  # v_min, v_max, and 16 direction sectors
        @test names(result)[1:2] == ["v_min", "v_max"]
        @test all(sector.name in names(result) for sector in DIRECTION_16_SECTORS)
        
        # Check known TI values
        # Find row for 8-10 m/s bin
        row_80m = findfirst(i -> 8.0 ≤ result.v_min[i] < 10.0, 1:nrow(result))
        @test !ismissing(result[row_80m, "N"])
        @test isapprox(result[row_80m, "N"], 0.1, atol=0.01)
        
        # Check missing sectors are filled with mean_ti
        @test all(result[row_80m, sector.name] == sector_stats.mean_ti for sector in DIRECTION_16_SECTORS if sector.name != "N")
        
        # Test missing value handling
        ts_missing = create_test_data(with_missing=true)
        ti_df_missing = calculate_ti_series(ts_missing.df, ws_avg.columnName, ws_sd.columnName, wd.columnName)
        sector_stats_missing = calculate_sector_stats(ti_df_missing)
        result_missing = calculate_ti_matrix(ti_df_missing, DEFAULT_WIND_SPEED_BINS, sector_stats_missing.mean_ti)
        @test result_missing[row_80m, "N"] ≈ 0.1  # Should still be close despite missing values
    end
    
    @testset "process_turbulence_intensity" begin
        ts = create_test_data()
        config = create_test_config(ti_target_height=80.0)
        
        # Process turbulence intensity
        results = process_turbulence_intensity(config, ts)
        
        # Check return type and structure
        @test results isa TurbulenceResults
        @test results.time_series isa DataFrame
        @test results.sector_stats isa TurbulenceSectorStats
        @test results.matrix isa DataFrame
        
        # Test with missing values
        ts_missing = create_test_data(with_missing=true)
        results_missing = process_turbulence_intensity(config, ts_missing)
        @test results_missing isa TurbulenceResults
        @test count(ismissing, results_missing.time_series.sector) == 1  # One missing sector
        @test count(ismissing, results_missing.time_series.ti) == 1  # One missing TI
    end
end

end # module 