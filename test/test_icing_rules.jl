# test/test_icing_rules.jl
using Test
using DataFrames
using Dates

@testset "Icing Rule Tests" begin
    base_time = DateTime(2024,1,1)
    test_data = TimeSeriesData(
        DataFrame(
            timestamp = base_time:Minute(10):(base_time + Hour(4)),
            speed_100m = vcat(
                fill(5.0, 18),  # 3 hours constant
                [5.1, 5.2, 5.3, 5.4, 5.5, 5.6],  # Normal variation
                fill(missing, 1)
            ),
            speed_80m = vcat(
                [5.0, 5.01],  # Small variation
                fill(5.02, 16),  # Constant value
                [5.1, 5.2, 5.3, 5.4, 5.5],  # Normal variation
                fill(missing, 1)
            )
        ),
        [
            SensorColumn("speed_100m", "WindSpeed", "", 100.0, "avg"),
            SensorColumn("speed_80m", "WindSpeed", "", 80.0, "avg")
        ]
    )

    @testset "Basic Icing Detection" begin
        rule = Rule("Icing Detection", "WindSpeed", 
                   HeightFilter(nothing, nothing),
                   IcingCriteria(7200, 0.02))
        result = ProcessIcing.apply(rule, test_data)
        @test length(result.timestamps) ≥ 18
    end

    @testset "Height-Specific Icing" begin
        rule = Rule("High Level Icing", "WindSpeed", 
                   HeightFilter(90.0, nothing),
                   IcingCriteria(7200, 0.02))
        result = ProcessIcing.apply(rule, test_data)
        @test !isempty(result.timestamps)
        @test length(result.columns) == 1
        @test result.columns[1] == "speed_100m"
    end
end
