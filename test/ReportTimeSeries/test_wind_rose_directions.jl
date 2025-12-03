using Test
using DataFrames
using CleanMastProject
import CleanMastProject.ReportTimeSeries.WindRose as WR

@testset "Wind Rose Direction Extraction" begin
    @testset "get_primary_secondary_directions" begin
        test_stats = DataFrame(
            sector = 1:16,
            label = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"],
            angle = collect(0.0:22.5:337.5),
            frequency = [0.05, 0.08, 0.12, 0.25, 0.15, 0.03, 0.02, 0.04,
                        0.10, 0.06, 0.03, 0.01, 0.01, 0.01, 0.02, 0.02],
            avg_speed = zeros(16),
            avg_power = zeros(16),
            power_frequency = zeros(16),
            total_power = zeros(16),
            count = ones(Int, 16)
        )

        primary_dir, primary_val, secondary_dir, secondary_val =
            WR.get_primary_secondary_directions(test_stats, :frequency)

        @test primary_dir == "ENE"
        @test primary_val == 25.0
        @test secondary_dir == "E"
        @test secondary_val == 15.0
    end

    @testset "create_direction_summary_list" begin
        test_stats_100m = DataFrame(
            sector = 1:16,
            label = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"],
            angle = collect(0.0:22.5:337.5),
            frequency = [0.05, 0.08, 0.12, 0.25, 0.15, 0.03, 0.02, 0.04,
                        0.10, 0.06, 0.03, 0.01, 0.01, 0.01, 0.02, 0.02],
            avg_speed = zeros(16),
            avg_power = zeros(16),
            power_frequency = zeros(16),
            total_power = zeros(16),
            count = ones(Int, 16)
        )

        test_stats_120m = DataFrame(
            sector = 1:16,
            label = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"],
            angle = collect(0.0:22.5:337.5),
            frequency = [0.06, 0.09, 0.13, 0.22, 0.18, 0.04, 0.03, 0.05,
                        0.08, 0.05, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01],
            avg_speed = zeros(16),
            avg_power = zeros(16),
            power_frequency = zeros(16),
            total_power = zeros(16),
            count = ones(Int, 16)
        )

        stats_by_height = Dict{Float64, DataFrame}(
            100.0 => test_stats_100m,
            120.0 => test_stats_120m
        )

        result = WR.create_direction_summary_list(stats_by_height, :frequency, "风向频率")

        @test occursin("120.0m", result)
        @test occursin("100.0m", result)
        @test occursin("ENE", result)
        @test occursin("E", result)
        @test occursin("%", result)
    end
end
