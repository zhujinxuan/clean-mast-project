# test/test_availability_rules.jl
using Test
using DataFrames
using Dates
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.SensorColumns: SensorColumn
using CleanMastProject.Types.CleanRules
using CleanMastProject.Types.Utils: from_dict
using CleanMastProject.DataClean.Rules.ProcessAvailability
using CleanMastProject.DataClean.Rules.ProcessTypes

@testset "Availability Rule Tests" begin
    base_time = DateTime(2024,1,1)
    test_data = TimeSeriesData(
        DataFrame(
            timestamp = base_time:Hour(1):(base_time + Hour(5)),
            # Availability sensors at different heights
            avail_100m = [95.0, 85.0, 75.0, 60.0, 90.0, missing],  # Below 80% at times 3,4
            avail_80m = [98.0, 70.0, 88.0, 85.0, 92.0, 95.0],     # Below 80% at time 2
            # Other sensors at same heights
            speed_100m = [5.0, 15.0, 25.0, 12.0, 8.0, 10.0],
            speed_80m = [4.0, 14.0, 24.0, 11.0, 7.0, 9.0],
            dir_100m = [45.0, 90.0, 180.0, 270.0, 315.0, 0.0],
            temp_80m = [10.0, 15.0, 20.0, 25.0, 12.0, 18.0]
        ),
        [
            SensorColumn(:avail_100m, "Availability", "", 100.0, "avg", "%"),
            SensorColumn(:avail_80m, "Availability", "", 80.0, "avg", "%"),
            SensorColumn(:speed_100m, "WindSpeed", "", 100.0, "avg", "m/s"),
            SensorColumn(:speed_80m, "WindSpeed", "", 80.0, "avg", "m/s"),
            SensorColumn(:dir_100m, "WindDirection", "", 100.0, "avg", "deg"),
            SensorColumn(:temp_80m, "Temperature", "", 80.0, "avg", "C")
        ]
    )

    @testset "Availability Rule - 100m sensors" begin
        rule = Rule("Lidar Availability Check", "Availability", 
            HeightFilter(100.0, 100.0),  # Only 100m height
            AvailabilityCriteria(80.0)   # 80% threshold
        )

        violations = ProcessAvailability.apply(rule, test_data)

        # Should find violations at timestamps where 100m availability < 80% OR missing
        # That's timestamps 3 (75%), 4 (60%), and 6 (missing) - indices 2, 3, 5
        expected_timestamps = [base_time + Hour(2), base_time + Hour(3), base_time + Hour(5)]

        # All sensors at 100m height should be violated at these times
        expected_columns = [:avail_100m, :speed_100m, :dir_100m]  # All sensors at 100m
        expected_violation_count = length(expected_timestamps) * length(expected_columns)
        
        @test length(violations) == expected_violation_count
        
        # Check that violations contain expected timestamps and columns
        violation_timestamps = [v.timestamp for v in violations]
        violation_columns = [v.column for v in violations]
        
        for timestamp in expected_timestamps
            @test timestamp in violation_timestamps
        end
        
        for col in expected_columns
            @test col in violation_columns
        end
    end

    @testset "Availability Rule - 80m sensors" begin
        rule = Rule("Lidar Availability Check", "Availability", 
            HeightFilter(80.0, 80.0),   # Only 80m height
            AvailabilityCriteria(80.0)  # 80% threshold
        )

        violations = ProcessAvailability.apply(rule, test_data)

        # Should find violations at timestamps where 80m availability < 80%
        # That's timestamp 2 (70%) - index 1 in 0-based
        expected_timestamps = [base_time + Hour(1)]  # Hour 1 (0-based index 1)
        
        # All sensors at 80m height should be violated at these times
        expected_columns = [:avail_80m, :speed_80m, :temp_80m]  # All sensors at 80m
        expected_violation_count = length(expected_timestamps) * length(expected_columns)
        
        @test length(violations) == expected_violation_count
        
        # Check that violations contain expected timestamps and columns
        violation_timestamps = [v.timestamp for v in violations]
        violation_columns = [v.column for v in violations]
        
        for timestamp in expected_timestamps
            @test timestamp in violation_timestamps
        end
        
        for col in expected_columns
            @test col in violation_columns
        end
    end

    @testset "Availability Rule - All heights" begin
        rule = Rule("Lidar Availability Check", "Availability", 
            HeightFilter(nothing, nothing),  # All heights
            AvailabilityCriteria(80.0)       # 80% threshold
        )

        violations = ProcessAvailability.apply(rule, test_data)

        # Should find violations for both 80m and 100m sensors when their respective availability drops
        # 80m: hour 1 (70% < 80%)
        # 100m: hours 2,3,5 (75%, 60% < 80%, missing)

        # Total violations should be:
        # Hour 1: 3 sensors at 80m = 3 violations
        # Hour 2: 3 sensors at 100m = 3 violations
        # Hour 3: 3 sensors at 100m = 3 violations
        # Hour 5: 3 sensors at 100m = 3 violations (missing availability)
        # Total: 12 violations
        @test length(violations) == 12
    end

    @testset "Availability Rule - High threshold (with missing)" begin
        rule = Rule("Lidar Availability Check", "Availability",
            HeightFilter(nothing, nothing),  # All heights
            AvailabilityCriteria(50.0)       # 50% threshold - lower than all numeric values
        )

        violations = ProcessAvailability.apply(rule, test_data)
        # Even with low threshold, missing availability at 100m hour 5 still triggers violations
        # Hour 5: 3 sensors at 100m = 3 violations
        @test length(violations) == 3
    end

    @testset "Availability Rule - Boundary condition (exactly at threshold)" begin
        # Test data with availability exactly at threshold
        boundary_test_data = TimeSeriesData(
            DataFrame(
                timestamp = base_time:Hour(1):(base_time + Hour(2)),
                avail_100m = [80.0, 80.0, 80.0],  # Exactly at threshold
                speed_100m = [5.0, 6.0, 7.0]
            ),
            [
                SensorColumn(:avail_100m, "Availability", "", 100.0, "avg", "%"),
                SensorColumn(:speed_100m, "WindSpeed", "", 100.0, "avg", "m/s")
            ]
        )

        rule = Rule("Boundary Test", "Availability",
            HeightFilter(nothing, nothing),
            AvailabilityCriteria(80.0)
        )

        violations = ProcessAvailability.apply(rule, boundary_test_data)
        # Values exactly at threshold should NOT be violations (only < threshold)
        @test length(violations) == 0
    end

    @testset "Availability Rule - No matching sensors" begin
        # Rule with height filter that doesn't match any sensors
        rule = Rule("No Match Test", "Availability",
            HeightFilter(50.0, 50.0),  # No sensors at 50m
            AvailabilityCriteria(80.0)
        )

        violations = ProcessAvailability.apply(rule, test_data)
        # Should have no violations since no sensors match
        @test length(violations) == 0
    end

    @testset "Config parsing with DataAvailability sensorType" begin
        # Test parsing rule from Dict (simulating TOML file loading)
        config_dict = Dict{String, Any}(
            "name" => "Lidar Availability Check",
            "sensorType" => "DataAvailability",  # Lidar uses this name
            "availability" => Dict("low_threshold" => 80.0)
        )

        rule = from_dict(Rule, config_dict)

        # Verify rule was parsed correctly
        @test rule.name == "Lidar Availability Check"
        @test rule.sensorType == "DataAvailability"
        @test rule.criteria isa AvailabilityCriteria
        @test rule.criteria.low_threshold == 80.0
        @test rule.height.min === nothing
        @test rule.height.max === nothing

        # Now test with sensor that uses "DataAvailability" sensorType
        lidar_test_data = TimeSeriesData(
            DataFrame(
                timestamp = base_time:Hour(1):(base_time + Hour(2)),
                lidar_avail_100m = [95.0, 75.0, 85.0],  # One value below 80%
                lidar_speed_100m = [5.0, 6.0, 7.0]
            ),
            [
                SensorColumn(:lidar_avail_100m, "DataAvailability", "", 100.0, "avg", "%"),
                SensorColumn(:lidar_speed_100m, "WindSpeed", "", 100.0, "avg", "m/s")
            ]
        )

        violations = ProcessAvailability.apply(rule, lidar_test_data)
        # Should find 1 timestamp × 2 sensors = 2 violations
        @test length(violations) == 2
        @test all(v.timestamp == base_time + Hour(1) for v in violations)
    end
end