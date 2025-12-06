using Test
using Dates
using CleanMastProject.ReportFrozenPeriod.PeriodOperations:
    TimePeriod, periods_overlap, compute_intersection, merge_consecutive_periods, calculate_duration_points

@testset "PeriodOperations" begin

    @testset "periods_overlap" begin
        @testset "Complete overlap" begin
            p1 = TimePeriod(DateTime(2024, 1, 1, 0, 0), DateTime(2024, 1, 1, 12, 0), 72)
            p2 = TimePeriod(DateTime(2024, 1, 1, 3, 0), DateTime(2024, 1, 1, 9, 0), 36)
            @test periods_overlap(p1, p2) == true
            @test periods_overlap(p2, p1) == true  # Symmetric
        end

        @testset "Partial overlap" begin
            p1 = TimePeriod(DateTime(2024, 1, 1, 0, 0), DateTime(2024, 1, 1, 6, 0), 36)
            p2 = TimePeriod(DateTime(2024, 1, 1, 3, 0), DateTime(2024, 1, 1, 9, 0), 36)
            @test periods_overlap(p1, p2) == true
            @test periods_overlap(p2, p1) == true
        end

        @testset "Adjacent periods (touching endpoints)" begin
            p1 = TimePeriod(DateTime(2024, 1, 1, 0, 0), DateTime(2024, 1, 1, 6, 0), 36)
            p2 = TimePeriod(DateTime(2024, 1, 1, 6, 0), DateTime(2024, 1, 1, 12, 0), 36)
            @test periods_overlap(p1, p2) == true  # Touch at endpoint
        end

        @testset "No overlap" begin
            p1 = TimePeriod(DateTime(2024, 1, 1, 0, 0), DateTime(2024, 1, 1, 6, 0), 36)
            p2 = TimePeriod(DateTime(2024, 1, 1, 12, 0), DateTime(2024, 1, 1, 18, 0), 36)
            @test periods_overlap(p1, p2) == false
            @test periods_overlap(p2, p1) == false
        end
    end

    @testset "compute_intersection" begin
        @testset "All three periods overlap" begin
            p1 = TimePeriod(DateTime(2024, 1, 1, 0, 0), DateTime(2024, 1, 1, 12, 0), 72)
            p2 = TimePeriod(DateTime(2024, 1, 1, 3, 0), DateTime(2024, 1, 1, 15, 0), 72)
            p3 = TimePeriod(DateTime(2024, 1, 1, 6, 0), DateTime(2024, 1, 1, 9, 0), 18)

            intersection = compute_intersection(p1, p2, p3)

            @test intersection.start_time == DateTime(2024, 1, 1, 6, 0)  # Latest start
            @test intersection.end_time == DateTime(2024, 1, 1, 9, 0)    # Earliest end
            @test intersection.duration_points == 0  # Placeholder (recalculated later)
        end

        @testset "Narrow intersection window" begin
            p1 = TimePeriod(DateTime(2024, 1, 1, 0, 0), DateTime(2024, 1, 1, 7, 0), 42)
            p2 = TimePeriod(DateTime(2024, 1, 1, 6, 0), DateTime(2024, 1, 1, 13, 0), 42)
            p3 = TimePeriod(DateTime(2024, 1, 1, 6, 30), DateTime(2024, 1, 1, 8, 0), 9)

            intersection = compute_intersection(p1, p2, p3)

            @test intersection.start_time == DateTime(2024, 1, 1, 6, 30)
            @test intersection.end_time == DateTime(2024, 1, 1, 7, 0)
        end

        @testset "Identical periods" begin
            p1 = TimePeriod(DateTime(2024, 1, 1, 0, 0), DateTime(2024, 1, 1, 6, 0), 36)
            p2 = TimePeriod(DateTime(2024, 1, 1, 0, 0), DateTime(2024, 1, 1, 6, 0), 36)
            p3 = TimePeriod(DateTime(2024, 1, 1, 0, 0), DateTime(2024, 1, 1, 6, 0), 36)

            intersection = compute_intersection(p1, p2, p3)

            @test intersection.start_time == DateTime(2024, 1, 1, 0, 0)
            @test intersection.end_time == DateTime(2024, 1, 1, 6, 0)
        end
    end

    @testset "merge_consecutive_periods" begin
        rep_interval = Minute(10)

        @testset "Two consecutive periods (touching)" begin
            p1 = TimePeriod(DateTime(2024, 1, 1, 0, 0), DateTime(2024, 1, 1, 1, 0), 6)
            p2 = TimePeriod(DateTime(2024, 1, 1, 1, 10), DateTime(2024, 1, 1, 2, 0), 5)

            merged = merge_consecutive_periods([p1, p2], rep_interval)

            @test length(merged) == 1
            @test merged[1].start_time == DateTime(2024, 1, 1, 0, 0)
            @test merged[1].end_time == DateTime(2024, 1, 1, 2, 0)
            @test merged[1].duration_points == 11  # 6 + 5
        end

        @testset "Two overlapping periods" begin
            p1 = TimePeriod(DateTime(2024, 1, 1, 0, 0), DateTime(2024, 1, 1, 2, 0), 12)
            p2 = TimePeriod(DateTime(2024, 1, 1, 1, 0), DateTime(2024, 1, 1, 3, 0), 12)

            merged = merge_consecutive_periods([p1, p2], rep_interval)

            @test length(merged) == 1
            @test merged[1].start_time == DateTime(2024, 1, 1, 0, 0)
            @test merged[1].end_time == DateTime(2024, 1, 1, 3, 0)  # Max end
            @test merged[1].duration_points == 24  # 12 + 12
        end

        @testset "Two non-consecutive periods" begin
            p1 = TimePeriod(DateTime(2024, 1, 1, 0, 0), DateTime(2024, 1, 1, 1, 0), 6)
            p2 = TimePeriod(DateTime(2024, 1, 1, 2, 0), DateTime(2024, 1, 1, 3, 0), 6)

            merged = merge_consecutive_periods([p1, p2], rep_interval)

            @test length(merged) == 2  # Not merged (gap too large)
            @test merged[1].start_time == DateTime(2024, 1, 1, 0, 0)
            @test merged[2].start_time == DateTime(2024, 1, 1, 2, 0)
        end

        @testset "Multiple periods with mixed consecutive/non-consecutive" begin
            p1 = TimePeriod(DateTime(2024, 1, 1, 0, 0), DateTime(2024, 1, 1, 1, 0), 6)
            p2 = TimePeriod(DateTime(2024, 1, 1, 1, 10), DateTime(2024, 1, 1, 2, 0), 5)
            p3 = TimePeriod(DateTime(2024, 1, 1, 2, 10), DateTime(2024, 1, 1, 3, 0), 5)
            p4 = TimePeriod(DateTime(2024, 1, 1, 5, 0), DateTime(2024, 1, 1, 6, 0), 6)

            merged = merge_consecutive_periods([p1, p2, p3, p4], rep_interval)

            @test length(merged) == 2
            # First group: p1 + p2 + p3
            @test merged[1].start_time == DateTime(2024, 1, 1, 0, 0)
            @test merged[1].end_time == DateTime(2024, 1, 1, 3, 0)
            @test merged[1].duration_points == 16  # 6 + 5 + 5
            # Second group: p4 alone
            @test merged[2].start_time == DateTime(2024, 1, 1, 5, 0)
            @test merged[2].end_time == DateTime(2024, 1, 1, 6, 0)
            @test merged[2].duration_points == 6
        end

        @testset "Unsorted input gets sorted" begin
            p1 = TimePeriod(DateTime(2024, 1, 1, 5, 0), DateTime(2024, 1, 1, 6, 0), 6)
            p2 = TimePeriod(DateTime(2024, 1, 1, 0, 0), DateTime(2024, 1, 1, 1, 0), 6)
            p3 = TimePeriod(DateTime(2024, 1, 1, 1, 10), DateTime(2024, 1, 1, 2, 0), 5)

            merged = merge_consecutive_periods([p1, p2, p3], rep_interval)

            @test length(merged) == 2
            # Should merge p2 + p3 after sorting
            @test merged[1].start_time == DateTime(2024, 1, 1, 0, 0)
            @test merged[1].end_time == DateTime(2024, 1, 1, 2, 0)
        end

        @testset "Empty input" begin
            merged = merge_consecutive_periods(TimePeriod[], rep_interval)
            @test isempty(merged)
        end

        @testset "Single period" begin
            p1 = TimePeriod(DateTime(2024, 1, 1, 0, 0), DateTime(2024, 1, 1, 1, 0), 6)
            merged = merge_consecutive_periods([p1], rep_interval)

            @test length(merged) == 1
            @test merged[1] == p1
        end
    end

    @testset "calculate_duration_points" begin
        rep_interval = Minute(10)

        @testset "Exact multiple of interval" begin
            start_time = DateTime(2024, 1, 1, 0, 0)
            end_time = DateTime(2024, 1, 1, 1, 0)  # 1 hour = 6 intervals

            points = calculate_duration_points(start_time, end_time, rep_interval)

            @test points == 7  # 6 intervals + 1 endpoint = 7 points
        end

        @testset "Non-exact interval (rounds up)" begin
            start_time = DateTime(2024, 1, 1, 0, 0)
            end_time = DateTime(2024, 1, 1, 0, 25)  # 2.5 intervals

            points = calculate_duration_points(start_time, end_time, rep_interval)

            @test points == 4  # ceil(2.5) + 1 = 3 + 1 = 4
        end

        @testset "Single interval" begin
            start_time = DateTime(2024, 1, 1, 0, 0)
            end_time = DateTime(2024, 1, 1, 0, 10)

            points = calculate_duration_points(start_time, end_time, rep_interval)

            @test points == 2  # 1 interval + 1 = 2 points
        end

        @testset "Zero duration" begin
            start_time = DateTime(2024, 1, 1, 0, 0)
            end_time = DateTime(2024, 1, 1, 0, 0)

            points = calculate_duration_points(start_time, end_time, rep_interval)

            @test points == 1  # 0 intervals + 1 = 1 point
        end

        @testset "Long period (6 hours)" begin
            start_time = DateTime(2024, 1, 1, 0, 0)
            end_time = DateTime(2024, 1, 1, 6, 0)

            points = calculate_duration_points(start_time, end_time, rep_interval)

            @test points == 37  # 36 intervals + 1 = 37 points
        end
    end

end
