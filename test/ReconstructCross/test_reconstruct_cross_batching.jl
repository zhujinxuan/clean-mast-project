"""
Unit tests for reconstruct-cross job batching logic.
Tests the create_job_batches function to ensure correct parallel job scheduling.
"""

using Test
using CleanMastProject.Types.ReconstructCrossConfig: ReconstructionJob

# Import the function we're testing
using CleanMastProject.ReconstructCross.ProcessReconstructCrossCommand: create_job_batches

@testset "Job Batching" begin
    @testset "Simple case: 3 targets, multiple jobs per target" begin
        jobs = [
            ReconstructionJob(
                target_mast="M01", source_mast="M02",
                model_dir="./models/M01/M02", priority=1,
                speed_correlation=0.8, direction_std=10.0,
                data_coverage_days=365.0, variables=["windspeed"]
            ),
            ReconstructionJob(
                target_mast="M02", source_mast="M01",
                model_dir="./models/M02/M01", priority=2,
                speed_correlation=0.8, direction_std=10.0,
                data_coverage_days=365.0, variables=["windspeed"]
            ),
            ReconstructionJob(
                target_mast="M01", source_mast="M03",
                model_dir="./models/M01/M03", priority=3,
                speed_correlation=0.75, direction_std=12.0,
                data_coverage_days=300.0, variables=["windspeed"]
            ),
            ReconstructionJob(
                target_mast="M02", source_mast="M03",
                model_dir="./models/M02/M03", priority=4,
                speed_correlation=0.75, direction_std=12.0,
                data_coverage_days=300.0, variables=["windspeed"]
            ),
            ReconstructionJob(
                target_mast="M03", source_mast="M01",
                model_dir="./models/M03/M01", priority=5,
                speed_correlation=0.7, direction_std=15.0,
                data_coverage_days=250.0, variables=["windspeed"]
            ),
        ]

        batches = create_job_batches(jobs)

        # Test 1: Correct number of batches
        # M01 has 2 jobs, M02 has 2 jobs, M03 has 1 job → need 2 batches
        @test length(batches) == 2

        # Test 2: Each batch has unique targets
        for batch in batches
            targets = [job.target_mast for job in batch]
            @test length(targets) == length(unique(targets))
        end

        # Test 3: All jobs are scheduled (no jobs lost)
        total_jobs = sum(length(batch) for batch in batches)
        @test total_jobs == length(jobs)

        # Test 4: Verify specific batch structure
        @test length(batches[1]) == 3
        @test length(batches[2]) == 2

        # Test 5: Verify first batch has one job per target
        batch1_targets = [job.target_mast for job in batches[1]]
        @test "M01" in batch1_targets
        @test "M02" in batch1_targets
        @test "M03" in batch1_targets
    end

    @testset "Edge case: All jobs target same mast" begin
        jobs = [
            ReconstructionJob(
                target_mast="M01", source_mast="M02",
                model_dir="./models/M01/M02", priority=1,
                speed_correlation=0.8, direction_std=10.0,
                data_coverage_days=365.0, variables=["windspeed"]
            ),
            ReconstructionJob(
                target_mast="M01", source_mast="M03",
                model_dir="./models/M01/M03", priority=2,
                speed_correlation=0.75, direction_std=12.0,
                data_coverage_days=300.0, variables=["windspeed"]
            ),
            ReconstructionJob(
                target_mast="M01", source_mast="M04",
                model_dir="./models/M01/M04", priority=3,
                speed_correlation=0.7, direction_std=15.0,
                data_coverage_days=250.0, variables=["windspeed"]
            ),
        ]

        batches = create_job_batches(jobs)

        # Should create 3 batches (sequential, can't parallelize)
        @test length(batches) == 3
        @test all(length(batch) == 1 for batch in batches)

        # Verify all target same mast
        for batch in batches
            @test batch[1].target_mast == "M01"
        end
    end

    @testset "Edge case: All jobs target different masts" begin
        jobs = [
            ReconstructionJob(
                target_mast="M01", source_mast="M02",
                model_dir="./models/M01/M02", priority=1,
                speed_correlation=0.8, direction_std=10.0,
                data_coverage_days=365.0, variables=["windspeed"]
            ),
            ReconstructionJob(
                target_mast="M02", source_mast="M01",
                model_dir="./models/M02/M01", priority=2,
                speed_correlation=0.8, direction_std=10.0,
                data_coverage_days=365.0, variables=["windspeed"]
            ),
            ReconstructionJob(
                target_mast="M03", source_mast="M01",
                model_dir="./models/M03/M01", priority=3,
                speed_correlation=0.75, direction_std=12.0,
                data_coverage_days=300.0, variables=["windspeed"]
            ),
        ]

        batches = create_job_batches(jobs)

        # Should create 1 batch (all can run in parallel)
        @test length(batches) == 1
        @test length(batches[1]) == 3

        # Verify all targets are different
        targets = [job.target_mast for job in batches[1]]
        @test length(unique(targets)) == 3
    end

    @testset "Edge case: Empty jobs list" begin
        jobs = ReconstructionJob[]
        batches = create_job_batches(jobs)
        @test length(batches) == 0
    end

    @testset "Edge case: Single job" begin
        jobs = [
            ReconstructionJob(
                target_mast="M01", source_mast="M02",
                model_dir="./models/M01/M02", priority=1,
                speed_correlation=0.8, direction_std=10.0,
                data_coverage_days=365.0, variables=["windspeed"]
            )
        ]

        batches = create_job_batches(jobs)

        @test length(batches) == 1
        @test length(batches[1]) == 1
        @test batches[1][1].target_mast == "M01"
    end

    @testset "Complex case: 11 targets with varying job counts (simulates tgl-group1-10masts)" begin
        # Create a realistic scenario: 11 masts, each has 1-10 jobs
        jobs = ReconstructionJob[]
        priority_counter = 1

        for target_idx in 1:11
            target_name = "M$(lpad(target_idx, 2, '0'))"
            # Each target has different number of source masts (1-10)
            num_sources = min(target_idx, 10)

            for source_idx in 1:num_sources
                source_name = "M$(lpad(mod(source_idx + target_idx, 11) + 1, 2, '0'))"
                if source_name != target_name
                    push!(jobs, ReconstructionJob(
                        target_mast=target_name,
                        source_mast=source_name,
                        model_dir="./models/$target_name/$source_name",
                        priority=priority_counter,
                        speed_correlation=0.7 + 0.1 * rand(),
                        direction_std=10.0 + 5.0 * rand(),
                        data_coverage_days=200.0 + 100.0 * rand(),
                        variables=["windspeed", "winddirection"]
                    ))
                    priority_counter += 1
                end
            end
        end

        batches = create_job_batches(jobs)

        # Test invariants
        @test !isempty(batches)

        # All jobs scheduled
        total_scheduled = sum(length(batch) for batch in batches)
        @test total_scheduled == length(jobs)

        # Each batch has unique targets
        for (i, batch) in enumerate(batches)
            targets = [job.target_mast for job in batch]
            @test length(targets) == length(unique(targets))
        end

        # First batch should have maximum parallelism (up to 11 jobs)
        @test length(batches[1]) <= 11

        # Count jobs per target
        target_counts = Dict{String, Int}()
        for job in jobs
            target_counts[job.target_mast] = get(target_counts, job.target_mast, 0) + 1
        end

        # Number of batches should equal maximum jobs for any single target
        max_jobs_per_target = maximum(values(target_counts))
        @test length(batches) == max_jobs_per_target
    end

    @testset "Job order preservation within batches" begin
        # Jobs are processed in order they appear
        jobs = [
            ReconstructionJob(
                target_mast="M01", source_mast="M02",
                model_dir="./models/M01/M02", priority=1,
                speed_correlation=0.8, direction_std=10.0,
                data_coverage_days=365.0, variables=["windspeed"]
            ),
            ReconstructionJob(
                target_mast="M02", source_mast="M03",
                model_dir="./models/M02/M03", priority=2,
                speed_correlation=0.8, direction_std=10.0,
                data_coverage_days=365.0, variables=["windspeed"]
            ),
            ReconstructionJob(
                target_mast="M01", source_mast="M04",
                model_dir="./models/M01/M04", priority=3,
                speed_correlation=0.75, direction_std=12.0,
                data_coverage_days=300.0, variables=["windspeed"]
            ),
        ]

        batches = create_job_batches(jobs)

        # First M01 job should appear in batch 1
        @test batches[1][1].target_mast == "M01"
        @test batches[1][1].source_mast == "M02"

        # Second M01 job should appear in batch 2
        @test batches[2][1].target_mast == "M01"
        @test batches[2][1].source_mast == "M04"
    end
end
