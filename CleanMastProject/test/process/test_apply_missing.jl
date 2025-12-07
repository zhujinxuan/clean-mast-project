# test/test_process.jl

using Test
using DataFrames
using Dates
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.Types.CleanRules
using CleanMastProject.DataClean.Rules.Process
using CleanMastProject.DataClean.Rules.ProcessTypes

function mk_time_series()
  df = DataFrame(
                 timestamp = DateTime(2024,1,1):Hour(1):DateTime(2024,1,2),
                 ws_10m = Vector{Union{Missing, Float64}}(repeat([5.0], 25)),
                 ws_20m = Vector{Union{Missing, Float64}}(repeat([6.0], 25)),
                 wd_10m = Vector{Union{Missing, Float64}}(repeat([180.0], 25))
                )

  sensors = [
             SensorColumn(:ws_10m, "WindSpeed", "N", 10.0, "avg", "m/s"),
             SensorColumn(:ws_20m, "WindSpeed", "N", 20.0, "avg", "m/s"),
             SensorColumn(:wd_10m, "WindDirection", "N", 10.0, "avg", "deg")
            ]

  TimeSeriesData(df, sensors)
end

ws_rule = Rule(
               "Test Rule",
               "WindSpeed",
               HeightFilter(nothing, nothing),
               ManualCriteria(),
              )

@testset "apply_missing!" begin
  @testset "basic violation handling" begin
    time_series = mk_time_series()
    violations = [
                  RuleViolation(ws_rule, DateTime(2024,1,1), :ws_10m),
                  RuleViolation(ws_rule, DateTime(2024,1,1,1), :ws_10m)
                 ]

    apply_missing!(violations, time_series)

    @test ismissing(time_series.df[1, :ws_10m])
    @test ismissing(time_series.df[2, :ws_10m])
    @test time_series.df[3, :ws_10m] == 5.0
  end

  @testset "multiple columns" begin
    time_series = mk_time_series()
    violations = [
                  RuleViolation(ws_rule, DateTime(2024,1,1), :ws_10m),
                  RuleViolation(ws_rule, DateTime(2024,1,1), :ws_20m)
                 ]

    apply_missing!(violations, time_series)

    @test ismissing(time_series.df[1, :ws_10m])
    @test ismissing(time_series.df[1, :ws_20m])
    @test !ismissing(time_series.df[2, :wd_10m])
  end

  @testset "nonexistent column" begin
    time_series = mk_time_series()
    violations = [
                  RuleViolation(ws_rule, DateTime(2024,1,1), :nonexistent)
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
