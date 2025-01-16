module TestTurbulenceIntensity

using Test
using DataFrames
using Dates
using Statistics
using CSV
using CleanMastProject.Types.CleanMastConfig: TimeRange, ProjectConfig, AnalysisConfig, MappingRule, SensorConfig, MastConfig, MesoConfig, Rule
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, SensorColumn
using CleanMastProject.Types.Sector: DIRECTION_SECTORS
using CleanMastProject.TurbulenceIntensity

"""Helper function to create test config"""
function create_test_config(;
    ti_target_height::Union{Nothing, Float64}=nothing,
    target_height::Union{Nothing, Float64}=nothing,
    data_path::String="data.csv"
)::ProjectConfig
    time_range = TimeRange(nothing, nothing)
    analysis_config = AnalysisConfig(time_range, target_height, ti_target_height)
    
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
function create_test_data()::TimeSeriesData
    # Create timestamps for 1 hour of 10-minute data
    timestamps = collect(
        DateTime(2024,1,1,0):Minute(10):DateTime(2024,1,1,1)
    )
    
    # Create sensors at different heights
    sensors = [
        # 80m sensors
        SensorColumn(Symbol("Ch1_WindSpeed_80m_avg_m/s"), "Ch1_WindSpeed_80m_avg_m/s", "WindSpeed", "N", 80.0, "avg", "m/s"),
        SensorColumn(Symbol("Ch1_WindSpeed_80m_sd_m/s"), "Ch1_WindSpeed_80m_sd_m/s", "WindSpeed", "N", 80.0, "sd", "m/s"),
        SensorColumn(Symbol("Ch1_WindDirection_80m_avg_deg"), "Ch1_WindDirection_80m_avg_deg", "WindDirection", "N", 80.0, "avg", "deg"),
        
        # 100m sensors
        SensorColumn(Symbol("Ch2_WindSpeed_100m_avg_m/s"), "Ch2_WindSpeed_100m_avg_m/s", "WindSpeed", "N", 100.0, "avg", "m/s"),
        SensorColumn(Symbol("Ch2_WindSpeed_100m_sd_m/s"), "Ch2_WindSpeed_100m_sd_m/s", "WindSpeed", "N", 100.0, "sd", "m/s"),
        SensorColumn(Symbol("Ch2_WindDirection_100m_avg_deg"), "Ch2_WindDirection_100m_avg_deg", "WindDirection", "N", 100.0, "avg", "deg"),
        
        # 120m sensors
        SensorColumn(Symbol("Ch3_WindSpeed_120m_avg_m/s"), "Ch3_WindSpeed_120m_avg_m/s", "WindSpeed", "N", 120.0, "avg", "m/s"),
        SensorColumn(Symbol("Ch3_WindSpeed_120m_sd_m/s"), "Ch3_WindSpeed_120m_sd_m/s", "WindSpeed", "N", 120.0, "sd", "m/s"),
        SensorColumn(Symbol("Ch3_WindDirection_120m_avg_deg"), "Ch3_WindDirection_120m_avg_deg", "WindDirection", "N", 120.0, "avg", "deg")
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
    
    @testset "calculate_ti_series" begin
        ts = create_test_data()
        ws_avg, ws_sd, wd = find_ti_sensors(ts, 80.0)
        
        ti_df = calculate_ti_series(ts.df, ws_avg.columnName, ws_sd.columnName, wd.columnName)
        
        # Check structure
        @test names(ti_df) == ["ws_avg", "ws_sd", "wd", "ti", "sector"]
        
        # Check TI calculation
        @test all(ti_df.ti .≈ 0.1)  # For 80m data
        @test all(ti_df.sector .== "N")  # All in North sector
    end
    
    @testset "calculate_sector_stats" begin
        ts = create_test_data()
        ws_avg, ws_sd, wd = find_ti_sensors(ts, 80.0)
        ti_df = calculate_ti_series(ts.df, ws_avg.columnName, ws_sd.columnName, wd.columnName)
        
        sector_stats, mean_ti, std_ti, representative_ti = calculate_sector_stats(ti_df)
        
        # Check structure
        @test names(sector_stats) == ["sector", "mean_speed", "ti", "std", "occurrence"]
        
        # Check values for North sector
        north_stats = first(sector_stats[sector_stats.sector .== "N", :])
        @test north_stats.mean_speed ≈ 9.0
        @test north_stats.ti ≈ 0.1
        @test north_stats.occurrence == 7  # Number of timestamps
        
        # Check overall statistics
        @test mean_ti ≈ 0.1
        @test representative_ti ≈ mean_ti + std_ti
    end
    
    @testset "calculate_ti_matrix" begin
        ts = create_test_data()
        ws_avg, ws_sd, wd = find_ti_sensors(ts, 80.0)
        ti_df = calculate_ti_series(ts.df, ws_avg.columnName, ws_sd.columnName, wd.columnName)
        sector_stats, mean_ti, std_ti, _ = calculate_sector_stats(ti_df)
        
        # Test with default bins
        result = calculate_ti_matrix(ti_df, DEFAULT_WIND_SPEED_BINS, mean_ti)
        
        # Check structure
        @test size(result, 2) == 18  # v_min, v_max, and 16 direction sectors
        @test names(result)[1:2] == ["v_min", "v_max"]
        @test all(sector.name in names(result) for sector in DIRECTION_SECTORS)
        
        # Check known TI values
        # Find row for 8-10 m/s bin
        row_80m = findfirst(i -> 8.0 ≤ result.v_min[i] < 10.0, 1:nrow(result))
        @test !ismissing(result[row_80m, "N"])
        @test isapprox(result[row_80m, "N"], 0.1, atol=0.01)
        
        # Check missing sectors are filled with mean_ti
        @test all(result[row_80m, sector.name] == mean_ti for sector in DIRECTION_SECTORS if sector.name != "N")
    end
    
    @testset "process_turbulence_intensity" begin
        ts = create_test_data()
        mktempdir() do temp_dir
            # Create config with temporary directory
            config = create_test_config(
                ti_target_height=80.0,
                data_path=joinpath(temp_dir, "data.csv")
            )
            
            # Process turbulence intensity
            process_turbulence_intensity(config, ts)
            
            # Check output files exist
            @test isfile(joinpath(temp_dir, "analysis", "turbulence_intensity.csv"))
            @test isfile(joinpath(temp_dir, "analysis", "turbulence_intensity_report.csv"))
            @test isfile(joinpath(temp_dir, "analysis", "meteodyn_ti.txt"))
            
            # Check main TI results
            ti_results = CSV.read(
                joinpath(temp_dir, "analysis", "turbulence_intensity.csv"),
                DataFrame
            )
            @test names(ti_results) == ["sector", "mean_speed", "ti", "std", "occurrence"]
            @test "N" in ti_results.sector
            
            # Check report
            report = CSV.read(
                joinpath(temp_dir, "analysis", "turbulence_intensity_report.csv"),
                DataFrame
            )
            @test names(report) == ["mast", "mean_ti", "representative_ti", "ti_std"]
            @test nrow(report) == 1
            @test report.mast[1] == basename(temp_dir)
            
            # Check Meteodyn file format
            meteodyn_lines = readlines(joinpath(temp_dir, "analysis", "meteodyn_ti.txt"))
            @test length(meteodyn_lines) == length(DEFAULT_WIND_SPEED_BINS)
            @test all(length(split(line, "\t")) == 17 for line in meteodyn_lines[2:end])
        end
    end
end

end # module 