using Test
using CleanMastProject.ReportUtils
using CleanMastProject.Types.MastTimeSeries: TimeSeriesSource

@testset "ReportUtils" begin
    @testset "adjust_path_for_report_masts" begin
        # Test basic path adjustment
        @test adjust_path_for_report_masts("./clean/data.parquet") == "../clean/data.parquet"
        @test adjust_path_for_report_masts("./raw/M2501.parquet") == "../raw/M2501.parquet"
        
        # Test path without ./ prefix
        @test adjust_path_for_report_masts("clean/data.parquet") == "../clean/data.parquet"
        
        # Test nothing input returns nothing
        @test adjust_path_for_report_masts(nothing) === nothing
        
        # Test various path formats
        @test adjust_path_for_report_masts("./reconstruct-single/M2501.parquet") == "../reconstruct-single/M2501.parquet"
        @test adjust_path_for_report_masts("./representative-year/M2501.parquet") == "../representative-year/M2501.parquet"
    end
    
    @testset "adjust_timeseries_source_for_report_masts" begin
        # Test with both data and sensors
        source1 = TimeSeriesSource("./clean/data.parquet", "./clean/data.sensors.toml")
        adjusted1 = adjust_timeseries_source_for_report_masts(source1)
        @test adjusted1.data == "../clean/data.parquet"
        @test adjusted1.sensors == "../clean/data.sensors.toml"
        
        # Test with nothing sensors (Parquet with embedded metadata)
        source2 = TimeSeriesSource("./clean/data.parquet", nothing)
        adjusted2 = adjust_timeseries_source_for_report_masts(source2)
        @test adjusted2.data == "../clean/data.parquet"
        @test adjusted2.sensors === nothing
        
        # Test with paths without ./ prefix
        source3 = TimeSeriesSource("clean/data.parquet", "clean/data.sensors.toml")
        adjusted3 = adjust_timeseries_source_for_report_masts(source3)
        @test adjusted3.data == "../clean/data.parquet"
        @test adjusted3.sensors == "../clean/data.sensors.toml"
    end
end
