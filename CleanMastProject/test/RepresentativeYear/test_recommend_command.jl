module TestRecommendRepresentativeYearCommand

using Test
using Dates
using CleanMastProject.Types.MastTimeSeries: TimeRange
using CleanMastProject.RepresentativeYear.RecommendRepresentativeYearCommand: select_last_year

@testset "RecommendRepresentativeYearCommand" begin
    @testset "select_last_year" begin
        @testset "Exactly 1 year ending at 23:59:59 (no change)" begin
            # 2023-06-15 to 2024-06-14 23:59:59 (exactly 1 year)
            input = TimeRange(DateTime(2023, 6, 15, 0, 0, 0), DateTime(2024, 6, 14, 23, 59, 59))
            result = select_last_year(input)

            @test result.min == DateTime(2023, 6, 15, 0, 0, 0)
            @test result.max == DateTime(2024, 6, 14, 23, 59, 59)
        end

        @testset "Exactly 1 year ending at 00:00:00 (no change)" begin
            # 2023-01-01 to 2024-01-01 00:00:00 (exactly 1 year + 1 second)
            input = TimeRange(DateTime(2023, 1, 1, 0, 0, 0), DateTime(2024, 1, 1, 0, 0, 0))
            result = select_last_year(input)

            @test result.min == DateTime(2023, 1, 1, 0, 0, 0)
            @test result.max == DateTime(2024, 1, 1, 0, 0, 0)
        end

        @testset "3 years ending at 23:59:59 (select last year)" begin
            # 2022-01-01 to 2024-12-31 23:59:59 (3 years)
            # Should return: 2024-01-01 to 2024-12-31 23:59:59
            input = TimeRange(DateTime(2022, 1, 1, 0, 0, 0), DateTime(2024, 12, 31, 23, 59, 59))
            result = select_last_year(input)

            @test result.min == DateTime(2024, 1, 1, 0, 0, 0)
            @test result.max == DateTime(2024, 12, 31, 23, 59, 59)
        end

        @testset "2 years ending at 23:59:59 (select last year)" begin
            # 2023-01-01 to 2024-12-31 23:59:59 (2 years)
            # Should return: 2024-01-01 to 2024-12-31 23:59:59
            input = TimeRange(DateTime(2023, 1, 1, 0, 0, 0), DateTime(2024, 12, 31, 23, 59, 59))
            result = select_last_year(input)

            @test result.min == DateTime(2024, 1, 1, 0, 0, 0)
            @test result.max == DateTime(2024, 12, 31, 23, 59, 59)
        end

        @testset "2 years ending at 00:00:00 (select last year)" begin
            # 2022-01-01 to 2024-01-01 00:00:00 (exactly 2 years + 1 second)
            # Should return: 2023-01-01 to 2024-01-01 00:00:00
            input = TimeRange(DateTime(2022, 1, 1, 0, 0, 0), DateTime(2024, 1, 1, 0, 0, 0))
            result = select_last_year(input)

            @test result.min == DateTime(2023, 1, 1, 0, 0, 0)
            @test result.max == DateTime(2024, 1, 1, 0, 0, 0)
        end

        @testset "Mid-year period ending at 23:59:59 (3 years)" begin
            # 2021-06-15 to 2024-06-14 23:59:59 (3 years)
            # Rounded end: 2024-06-15 00:00:00
            # Start: 2024-06-15 - 1 year = 2023-06-15 00:00:00
            # Should return: 2023-06-15 to 2024-06-14 23:59:59
            input = TimeRange(DateTime(2021, 6, 15, 0, 0, 0), DateTime(2024, 6, 14, 23, 59, 59))
            result = select_last_year(input)

            @test result.min == DateTime(2023, 6, 15, 0, 0, 0)
            @test result.max == DateTime(2024, 6, 14, 23, 59, 59)
        end

        @testset "Leap year handling (2024 is a leap year)" begin
            # 2022-02-01 to 2024-01-31 23:59:59 (2 years)
            # Rounded end: 2024-02-01 00:00:00
            # Start: 2024-02-01 - 1 year = 2023-02-01 00:00:00
            # Should return: 2023-02-01 to 2024-01-31 23:59:59
            input = TimeRange(DateTime(2022, 2, 1, 0, 0, 0), DateTime(2024, 1, 31, 23, 59, 59))
            result = select_last_year(input)

            @test result.min == DateTime(2023, 2, 1, 0, 0, 0)
            @test result.max == DateTime(2024, 1, 31, 23, 59, 59)
        end

        @testset "Period ending mid-day (not 23:59:59)" begin
            # 2022-01-01 to 2024-12-31 15:30:45 (3 years, ends mid-day)
            # No rounding needed (not 23:59:59)
            # Start: 2024-12-31 15:30:45 - 1 year = 2023-12-31 15:30:45
            input = TimeRange(DateTime(2022, 1, 1, 0, 0, 0), DateTime(2024, 12, 31, 15, 30, 45))
            result = select_last_year(input)

            @test result.min == DateTime(2023, 12, 31, 15, 30, 45)
            @test result.max == DateTime(2024, 12, 31, 15, 30, 45)
        end

        @testset "Realistic scenario: cluster period from recommend reconstruct-meso" begin
            # Typical output from calculate_cluster_optimal_period
            # 2022-02-01 00:00:00 to 2025-01-31 23:59:59 (3 years)
            # Should select: 2024-02-01 00:00:00 to 2025-01-31 23:59:59
            input = TimeRange(DateTime(2022, 2, 1, 0, 0, 0), DateTime(2025, 1, 31, 23, 59, 59))
            result = select_last_year(input)

            @test result.min == DateTime(2024, 2, 1, 0, 0, 0)
            @test result.max == DateTime(2025, 1, 31, 23, 59, 59)
        end

        @testset "Edge case: Period ending at 23:59:58 (within 10min of next day)" begin
            # 2022-01-01 to 2024-12-31 23:59:58
            # Within 10 minutes of next day, should round
            # Rounded end: 2025-01-01 00:00:00
            # Start: 2024-01-01 00:00:00
            input = TimeRange(DateTime(2022, 1, 1, 0, 0, 0), DateTime(2024, 12, 31, 23, 59, 58))
            result = select_last_year(input)

            @test result.min == DateTime(2024, 1, 1, 0, 0, 0)
            @test result.max == DateTime(2024, 12, 31, 23, 59, 58)
        end

        @testset "Edge case: Period ending at 23:50:00 (within 10min of next day)" begin
            # 2022-01-01 to 2024-12-31 23:50:00
            # Within 10 minutes of next day (23:50 + 10min = 00:00 next day)
            # Should round to 2025-01-01 00:00:00
            input = TimeRange(DateTime(2022, 1, 1, 0, 0, 0), DateTime(2024, 12, 31, 23, 50, 0))
            result = select_last_year(input)

            @test result.min == DateTime(2024, 1, 1, 0, 0, 0)
            @test result.max == DateTime(2024, 12, 31, 23, 50, 0)
        end

        @testset "Edge case: Period ending at 23:49:59 (NOT within 10min of next day)" begin
            # 2022-01-01 to 2024-12-31 23:49:59
            # NOT within 10 minutes of next day (23:49:59 + 10min = 23:59:59 same day)
            # Should NOT round
            input = TimeRange(DateTime(2022, 1, 1, 0, 0, 0), DateTime(2024, 12, 31, 23, 49, 59))
            result = select_last_year(input)

            @test result.min == DateTime(2023, 12, 31, 23, 49, 59)
            @test result.max == DateTime(2024, 12, 31, 23, 49, 59)
        end

        @testset "Very long period (5+ years)" begin
            # 2019-01-01 to 2024-12-31 23:59:59 (6 years)
            # Should select last year: 2024-01-01 to 2024-12-31 23:59:59
            input = TimeRange(DateTime(2019, 1, 1, 0, 0, 0), DateTime(2024, 12, 31, 23, 59, 59))
            result = select_last_year(input)

            @test result.min == DateTime(2024, 1, 1, 0, 0, 0)
            @test result.max == DateTime(2024, 12, 31, 23, 59, 59)
        end
    end
end

end
