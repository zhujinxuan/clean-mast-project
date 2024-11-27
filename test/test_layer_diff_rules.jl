# test/test_layer_diff_rules.jl
using Test
using DataFrames
using Dates

@testset "Layer Difference Rule Tests" begin
    base_time = DateTime(2024,1,1)
    test_data = TimeSeriesData(
        DataFrame(
            timestamp = base_time:Hour(1):(base_time + Hour(5)),
            dir_100m = [350.0, 10.0, 180.0, 190.0, 200.0, 210.0],
            dir_80m = [10.0, 350.0, 160.0, 185.0, 205.0, 200.0],
            dir_60m = [5.0, 355.0, 165.0, 187.0, 203.0, 205.0],
            speed_100m = [10.0, 12.0, 15.0, 10.0, 8.0, 10.0],
            speed_80m = [8.0, 8.0, 8.0, 15.0, 12.0, 10.0],
            speed_60m = [7.0, 7.0, 7.0, 7.0, 7.0, 7.0]
        ),
        [
            SensorColumn("dir_100m", "WindDirection", "", 100.0, "avg"),
            SensorColumn("dir_80m", "WindDirection", "", 80.0, "avg"),
            SensorColumn("dir_60m", "WindDirection", "", 60.0, "avg"),
            SensorColumn("speed_100m", "WindSpeed", "", 100.0, "avg"),
            SensorColumn("speed_80m", "WindSpeed", "", 80.0, "avg"),
            SensorColumn("speed_60m", "WindSpeed", "", 60.0, "avg")
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
        result = ProcessLayerDiff.apply(rule, test_data)
        @test !isempty(result.timestamps)
    end

    @testset "Wind Direction Layer Difference" begin
        rule = Rule("Direction Layer Diff", "WindDirection", 
                   HeightFilter(70.0, nothing),
                   LayerDifferenceCriteria(
                       20.0,
                       RangeCriteria(nothing, 22.5),
                       RangeCriteria(3.0, 25.0)
                   ))
        result = ProcessLayerDiff.apply(rule, test_data)
        @test !isempty(result.timestamps)
        # Check wrap-around cases (350° vs 10°)
        @test base_time ∈ result.timestamps || (base_time + Hour(1)) ∈ result.timestamps
    end
end
