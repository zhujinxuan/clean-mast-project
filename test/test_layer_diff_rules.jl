# test/test_layer_diff_rules.jl
using Test
using DataFrames
using Dates
using CleanMastProject.CleanMastRules.ProcessLayerDiff

@testset "Layer Difference Rule Tests" begin
  base_time = DateTime(2024,1,1)
  test_data = TimeSeriesData(
    DataFrame(
      timestamp = base_time:Hour(1):(base_time + Hour(6)),
      dir_100m = [300.0, 300.0, 180.0, 190.0, 200.0, 210.0, 200],
      dir_80m = [10.0, 350.0, 160.0, 185.0, 205.0, 200.0,100],
      dir_60m = [5.0, 355.0, 165.0, 187.0, 203.0, 205.0, 5],
      speed_100m = [10.0, 12.0, 15.0, 10.0, 8.0, 10.0,2.0],
      speed_80m = [8.0, 8.0, 8.0, 15.0, 12.0, 10.0,2.0],
      speed_60m = [7.0, 7.0, 7.0, 7.0, 7.0, 7.0,2.0]
    ),
    [
      SensorColumn(:dir_100m, "WindDirection", "", 100.0, "avg", "deg"),
      SensorColumn(:dir_80m, "WindDirection", "", 80.0, "avg", "deg"),
      SensorColumn(:dir_60m, "WindDirection", "", 60.0, "avg", "deg"),
      SensorColumn(:speed_100m, "WindSpeed", "", 100.0, "avg", "m/s"),
      SensorColumn(:speed_80m, "WindSpeed", "", 80.0, "avg", "m/s"),
      SensorColumn(:speed_60m, "WindSpeed", "", 60.0, "avg", "m/s")
    ]
  )

  @testset "Wind Speed Layer Difference" begin
    rule = Rule("Speed Layer Diff", "WindSpeed", 
                HeightFilter(70.0, nothing),
                LayerDifferenceCriteria(
                20.0,
                RangeCriteria(nothing, 2.0),
                RangeCriteria(nothing, nothing)
                ))
    violations = ProcessLayerDiff.apply(rule, test_data)
    @test !isempty(violations)

    # Violations should only be for upper layer columns
    @test all(v -> v.column ∈ [:speed_100m, :speed_80m], violations)
    timestamps_100m = map(x -> x.timestamp, filter(x -> x.column == :speed_100m, violations))
    sort!(timestamps_100m)
    @test all(timestamps_100m.== test_data.df[[2,3,4,5],:timestamp])
    timestamps_80m = map(x -> x.timestamp, filter(x -> x.column == :speed_80m, violations))
    sort!(timestamps_80m)
    @test all(timestamps_80m.== test_data.df[[4,5,6],:timestamp])
  end

  @testset "Wind Direction Layer Difference" begin
    rule = Rule("Direction Layer Diff", "WindDirection", 
                HeightFilter(70.0, nothing),
                LayerDifferenceCriteria(
                20.0,
                RangeCriteria(nothing, 22.5),
                RangeCriteria(3.0, 25.0)
                ))
    violations = ProcessLayerDiff.apply(rule, test_data)

    @test !isempty(violations)
    # Should have violations for wrap-around cases
    wrap_violations = filter(v -> v.timestamp ∈ [base_time, base_time + Hour(1)], violations)
    @test !isempty(wrap_violations)

    # All violations should be for upper layer columns
    @test all(v -> v.column ∈ [:dir_100m, :dir_80m], violations)
  end
end
