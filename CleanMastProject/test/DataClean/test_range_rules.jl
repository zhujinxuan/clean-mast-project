# test/test_range_rules.jl
using Test
using DataFrames
using Dates
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.Types.CleanRules
using CleanMastProject.DataClean.Rules.ProcessRange
using CleanMastProject.DataClean.Rules.ProcessTypes

@testset "Range Rule Tests" begin
    base_time = DateTime(2024,1,1)
    test_data = TimeSeriesData(
        DataFrame(
            timestamp = base_time:Hour(1):(base_time + Hour(5)),
            speed_100m = [5.0, 15.0, 25.0, -1.0, 55.0, missing],
            speed_80m = [4.0, 14.0, 24.0, 0.0, 51.0, 10.0],
            temp_80m = [-20.0, -5.0, 15.0, 35.0, 65.0, missing],
            dir_100m = [-10.0, 45.0, 180.0, 270.0, 370.0, missing]
        ),
        [
            SensorColumn(:speed_100m, "WindSpeed", "", 100.0, "avg", "m/s"),
            SensorColumn(:speed_80m, "WindSpeed", "", 80.0, "avg", "m/s"),
            SensorColumn(:temp_80m, "Temperature", "", 80.0, "avg", "C"),
            SensorColumn(:dir_100m, "WindDirection", "", 100.0, "avg", "deg")
        ]
    )

    @testset "Wind Speed Range" begin
        rule = Rule("Wind Speed Range", "WindSpeed", 
                   HeightFilter(nothing, nothing),
                   RangeCriteria(0.0, 50.0))
        result = ProcessRange.apply(rule, test_data)
        @test length(result) == 3  # -1.0, 55.0, 51.0
        @test all(map(x -> x.timestamp, result) .∈ Ref([base_time + Hour(3), base_time + Hour(4)]))
    end

    @testset "Temperature Range" begin
        rule = Rule("Temperature Range", "Temperature", 
                   HeightFilter(nothing, nothing),
                   RangeCriteria(-30.0, 50.0))
        result = ProcessRange.apply(rule, test_data)
        @test length(result) == 1  # 65.0
        @test result[1].timestamp == base_time + Hour(4)
    end

    @testset "Wind Direction Range" begin
        rule = Rule("Direction Range", "WindDirection", 
                   HeightFilter(nothing, nothing),
                   RangeCriteria(0.0, 360.0))
        result = ProcessRange.apply(rule, test_data)
        @test length(result) == 2  # -10.0, 370.0
    end
end
