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
            SensorColumn(:speed_100m, "WindSpeed", "", 100.0, "avg"),
            SensorColumn(:speed_80m, "WindSpeed", "", 80.0, "avg")
        ]
    )

    @testset "Basic Icing Detection" begin
        rule = Rule("Icing Detection", "WindSpeed", 
                   HeightFilter(nothing, nothing),
                   IcingCriteria(7200, 0.02))
        violations = ProcessIcing.apply(rule, test_data)
        
        # Check we have violations for both constant periods
        @test length(violations) ≥ 18
        
        # Check that violations are continuous in time for each column
        speed_100m_violations = filter(v -> v.column == :speed_100m, violations)
        speed_80m_violations = filter(v -> v.column == :speed_80m, violations)
        
        @test !isempty(speed_100m_violations)
        @test !isempty(speed_80m_violations)
        
        # Check timestamps are continuous
        for violations in [speed_100m_violations, speed_80m_violations]
            timestamps = sort!([v.timestamp for v in violations])
            for i in 1:length(timestamps)-1
                @test timestamps[i+1] - timestamps[i] == Minute(10)
            end
        end
    end

    @testset "Height-Specific Icing" begin
        rule = Rule("High Level Icing", "WindSpeed", 
                   HeightFilter(90.0, nothing),
                   IcingCriteria(7200, 0.02))
        violations = ProcessIcing.apply(rule, test_data)
        
        @test !isempty(violations)
        # All violations should be for speed_100m
        @test all(v -> v.column == :speed_100m, violations)
    end
end
