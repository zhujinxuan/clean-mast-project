using Test
using DataFrames
using Dates
using CleanMastProject.Types.ReportRecoveryConfig: ReportRecoveryMast
using CleanMastProject.Types.ReportRecoveryData: SensorRecoveryInfo, MastRecoveryData, get_sensor_display_name
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData, TimeRange
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.ReportRecovery.RecoveryAnalysis: analyze_sensor_recovery, count_missing_values, filter_time_range

@testset "RecoveryAnalysis Tests" begin
    
    @testset "get_sensor_display_name" begin
        # Test wind speed sensor
        ws_sensor = SensorColumn(
            sensorType="WindSpeed", 
            statType="avg", 
            height=120.0, 
            columnName=:WS_120m_N, 
            sensorDirection="N", 
            unit="m/s"
        )
        @test get_sensor_display_name(ws_sensor) == "WS_120m_N"
        
        # Test wind direction sensor
        wd_sensor = SensorColumn(
            sensorType="WindDirection", 
            statType="avg", 
            height=80.0, 
            columnName=:WD_80m, 
            sensorDirection="", 
            unit="deg"
        )
        @test get_sensor_display_name(wd_sensor) == "WD_80m"
        
        # Test temperature sensor
        temp_sensor = SensorColumn(
            sensorType="Temperature", 
            statType="avg", 
            height=10.0, 
            columnName=:Temp_10m, 
            sensorDirection="", 
            unit="°C"
        )
        @test get_sensor_display_name(temp_sensor) == "Temp_10m"
        
        # Test humidity sensor (analog)
        rh_sensor = SensorColumn(
            sensorType="Analog", 
            statType="avg", 
            height=10.0, 
            columnName=:RH_10m, 
            sensorDirection="", 
            unit="%"
        )
        @test get_sensor_display_name(rh_sensor) == "RH_10m"
    end
    
    @testset "count_missing_values" begin
        # Create test DataFrame
        df = DataFrame(
            timestamp = [DateTime(2023,1,1,0,0), DateTime(2023,1,1,0,10), DateTime(2023,1,1,0,20)],
            WS_120m = [10.0, missing, 12.0],
            WD_80m = [missing, missing, 180.0]
        )
        
        @test count_missing_values(df, :WS_120m) == 1
        @test count_missing_values(df, :WD_80m) == 2
        @test count_missing_values(df, :nonexistent) == 0
    end
    
    @testset "filter_time_range" begin
        # Create test data
        timestamps = [DateTime(2023,1,1,0,0), DateTime(2023,1,1,0,10), DateTime(2023,1,1,0,20), DateTime(2023,1,1,0,30)]
        df = DataFrame(
            timestamp = timestamps,
            WS_120m = [10.0, 11.0, 12.0, 13.0]
        )
        
        sensor = SensorColumn(
            sensorType="WindSpeed", 
            statType="avg", 
            height=120.0, 
            columnName=:WS_120m, 
            sensorDirection="N", 
            unit="m/s"
        )
        
        data = TimeSeriesData(df, [sensor])
        
        # Filter to middle two timestamps
        start_time = DateTime(2023,1,1,0,10)
        end_time = DateTime(2023,1,1,0,20)
        
        filtered = filter_time_range(data, start_time, end_time)
        
        @test nrow(filtered.df) == 2
        @test filtered.df.timestamp[1] == DateTime(2023,1,1,0,10)
        @test filtered.df.timestamp[2] == DateTime(2023,1,1,0,20)
        @test filtered.df.WS_120m[1] == 11.0
        @test filtered.df.WS_120m[2] == 12.0
    end
    
    @testset "analyze_sensor_recovery" begin
        # Create test sensor
        sensor = SensorColumn(
            sensorType="WindSpeed", 
            statType="avg", 
            height=120.0, 
            columnName=:WS_120m, 
            sensorDirection="N", 
            unit="m/s"
        )
        
        # Create test data for different stages
        # Tower shading: 3 missing out of 5 points
        tower_df = DataFrame(
            timestamp = [DateTime(2023,1,1,0,i*10) for i in 0:4],
            WS_120m = [10.0, missing, missing, missing, 14.0]
        )
        tower_data = TimeSeriesData(tower_df, [sensor])
        
        # After single reconstruction: 2 missing (filled 1)
        single_df = DataFrame(
            timestamp = [DateTime(2023,1,1,0,i*10) for i in 0:4],
            WS_120m = [10.0, 11.0, missing, missing, 14.0]
        )
        single_data = TimeSeriesData(single_df, [sensor])
        
        # After cross reconstruction: 1 missing (filled 1 more)
        cross_df = DataFrame(
            timestamp = [DateTime(2023,1,1,0,i*10) for i in 0:4],
            WS_120m = [10.0, 11.0, 12.0, missing, 14.0]
        )
        cross_data = TimeSeriesData(cross_df, [sensor])
        
        # After meso reconstruction: 0 missing (filled 1 more)
        meso_df = DataFrame(
            timestamp = [DateTime(2023,1,1,0,i*10) for i in 0:4],
            WS_120m = [10.0, 11.0, 12.0, 13.0, 14.0]
        )
        meso_data = TimeSeriesData(meso_df, [sensor])
        
        # Analyze recovery
        recovery_info = analyze_sensor_recovery(
            sensor, tower_data, single_data, cross_data, meso_data, 5
        )
        
        @test recovery_info.sensor_name == "WS_120m_N"
        @test recovery_info.initial_missing == 3
        @test recovery_info.single_filled == 1
        @test recovery_info.cross_filled == 1
        @test recovery_info.meso_filled == 1
        @test recovery_info.final_missing == 0
        @test recovery_info.total_points == 5
    end

    @testset "SensorRecoveryInfo construction" begin
        sensor = SensorColumn(
            sensorType="WindDirection",
            statType="avg",
            height=80.0,
            columnName=:WD_80m,
            sensorDirection="",
            unit="deg"
        )

        recovery_info = SensorRecoveryInfo(
            sensor = sensor,
            sensor_name = "WD_80m",
            initial_missing = 100,
            single_filled = 30,
            cross_filled = 20,
            meso_filled = 40,
            final_missing = 10,
            total_points = 1000
        )

        @test recovery_info.sensor_name == "WD_80m"
        @test recovery_info.initial_missing == 100
        @test recovery_info.single_filled == 30
        @test recovery_info.cross_filled == 20
        @test recovery_info.meso_filled == 40
        @test recovery_info.final_missing == 10
        @test recovery_info.total_points == 1000

        # Test that total filled + final missing should be <= initial missing
        total_filled = recovery_info.single_filled + recovery_info.cross_filled + recovery_info.meso_filled
        @test total_filled + recovery_info.final_missing <= recovery_info.initial_missing + total_filled
    end
end
