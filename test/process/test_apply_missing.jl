# test/test_process.jl

using Test
using DataFrames
using Dates
using CleanMastProject.MastTimeSeries
using CleanMastProject.CleanMastRules.Process
using CleanMastProject.CleanMastRules.ProcessTypes

function mk_time_series()
    df = DataFrame(
        timestamp = DateTime(2024,1,1):Hour(1):DateTime(2024,1,2),
        ws_10m = repeat([5.0], 25),
        ws_20m = repeat([6.0], 25),
        wd_10m = repeat([180.0], 25)
    )
    
    sensors = [
        SensorColumn(:ws_10m, "WindSpeed", "N", 10.0, "avg"),
        SensorColumn(:ws_20m, "WindSpeed", "N", 20.0, "avg"),
        SensorColumn(:wd_10m, "WindDirection", "N", 10.0, "avg")
    ]
    
    TimeSeriesData(df, sensors)
end

@testset "apply_missing!" begin
    @testset "basic violation handling" begin
        time_series = mk_time_series()
        violations = [
            RuleViolation(DateTime(2024,1,1), :ws_10m, "Test Rule"),
            RuleViolation(DateTime(2024,1,1,1), :ws_10m, "Test Rule")
        ]
        
        apply_missing!(violations, time_series)
        
        @test ismissing(time_series.df[1, :ws_10m])
        @test ismissing(time_series.df[2, :ws_10m])
        @test time_series.df[3, :ws_10m] == 5.0
    end
    
    @testset "multiple columns" begin
        time_series = mk_time_series()
        violations = [
            RuleViolation(DateTime(2024,1,1), :ws_10m, "Test Rule"),
            RuleViolation(DateTime(2024,1,1), :ws_20m, "Test Rule")
        ]
        
        apply_missing!(violations, time_series)
        
        @test ismissing(time_series.df[1, :ws_10m])
        @test ismissing(time_series.df[1, :ws_20m])
        @test !ismissing(time_series.df[1, :wd_10m])
    end
    
    @testset "nonexistent column" begin
        time_series = mk_time_series()
        violations = [
            RuleViolation(DateTime(2024,1,1), :nonexistent, "Test Rule")
        ]
        
        @test_logs (:warn, "Column nonexistent not found in DataFrame") begin
            apply_missing!(violations, time_series)
        end
    end
    
    @testset "empty violations" begin
        time_series = mk_time_series()
        original_df = copy(time_series.df)
        violations = RuleViolation[]
        
        apply_missing!(violations, time_series)
        
        @test time_series.df == original_df
    end
end
