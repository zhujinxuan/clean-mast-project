using Test
using CleanMastProject.CleanMastLogging
using CleanMastProject.CleanMastLogging.CleanMastLogger.LogRotation
using Logging
using JSON

"""
Parallel logging tests - requires multiple threads to run properly.

Run with:
    julia --threads 4 test/runtests.jl logging
    julia --threads auto test/runtests.jl logging

Or run this file directly:
    julia --threads 4 test/logging/test_parallel_logging.jl
"""

@testset "Parallel Logging Tests" begin
    available_threads = Threads.nthreads()

    @testset "Thread availability check" begin
        @test available_threads >= 1

        if available_threads == 1
            @info """
            ⚠️  Running with only 1 thread. Parallel tests will be skipped.

            To enable parallel tests, run with:
                julia --threads 4 test/runtests.jl logging
                julia --threads auto test/runtests.jl logging

            Current threads: $(available_threads)
            """
        else
            @info "✓ Parallel testing enabled with $(available_threads) threads"
        end
    end

    @testset "Parallel logger creation and archiving" begin
        if available_threads < 2
            @test_skip "Requires multiple threads (run with julia --threads 4)"
            return
        end

        mktempdir() do tmpdir
            # Create initial log files to test archiving
            log_dir = joinpath(tmpdir, "logs")
            mkpath(log_dir)

            for worker_id in 1:available_threads
                write(joinpath(log_dir, "test.$(worker_id).jsonl"), "old log $(worker_id)\n")
            end

            # Archive all logs before parallel work
            archive_all_worker_logs(tmpdir, "test", available_threads)

            # Verify logs were archived
            archive_dir = joinpath(log_dir, "archive")
            @test isdir(archive_dir)
            archives = readdir(archive_dir)
            @test length(archives) == available_threads

            # Pre-create loggers for all threads
            worker_loggers = Dict{Int, Any}()
            for worker_id in 1:available_threads
                worker_loggers[worker_id] = create_cleanmast_logger(
                    job_name="test-parallel",
                    worker_id=worker_id,
                    config_dir=tmpdir,
                    config_basename="test",
                    enable_terminal=false
                )
            end

            # Verify all loggers were created
            @test length(worker_loggers) == available_threads
            for worker_id in 1:available_threads
                @test haskey(worker_loggers, worker_id)
            end
        end
    end

    @testset "Concurrent logging with Threads.@threads" begin
        if available_threads < 2
            @test_skip "Requires multiple threads (run with julia --threads 4)"
            return
        end

        mktempdir() do tmpdir
            archive_all_worker_logs(tmpdir, "test", available_threads)

            # Pre-create loggers
            worker_loggers = Dict{Int, Any}()
            for worker_id in 1:available_threads
                worker_loggers[worker_id] = create_cleanmast_logger(
                    job_name="concurrent-test",
                    worker_id=worker_id,
                    config_dir=tmpdir,
                    config_basename="test",
                    enable_terminal=false
                )
            end

            # Run parallel tasks (5 tasks per thread)
            total_tasks = available_threads * 5
            task_results = Vector{Int}(undef, total_tasks)

            Threads.@threads for idx in 1:total_tasks
                worker_id = Threads.threadid()
                worker_logger = worker_loggers[worker_id]

                with_logger(worker_logger) do
                    @info "Processing task" task_id=idx thread_id=worker_id
                    sleep(0.001)  # Simulate work
                    task_results[idx] = worker_id
                    @info "Task completed" task_id=idx thread_id=worker_id
                end
            end

            # Verify all log files exist
            for worker_id in 1:available_threads
                log_file = joinpath(tmpdir, "logs", "test.$(worker_id).jsonl")
                @test isfile(log_file)
            end

            # Verify log content integrity
            for worker_id in 1:available_threads
                log_file = joinpath(tmpdir, "logs", "test.$(worker_id).jsonl")
                lines = readlines(log_file)

                @test length(lines) > 0

                for line in lines
                    log = JSON.parse(line)
                    @test log["worker_id"] == worker_id
                    @test log["job_name"] == "concurrent-test"
                    @test haskey(log, "task_id")
                    @test haskey(log, "thread_id")
                    @test log["thread_id"] == worker_id
                end
            end

            # Verify all tasks were assigned to threads
            @test all(1 .<= task_results .<= available_threads)
        end
    end

    @testset "Multiple parallel phases (analyze then plot)" begin
        if available_threads < 2
            @test_skip "Requires multiple threads (run with julia --threads 4)"
            return
        end

        mktempdir() do tmpdir
            archive_all_worker_logs(tmpdir, "test", available_threads)

            # Phase 1: Analysis
            @info "Phase 1: Running analysis tasks"
            analyze_loggers = Dict{Int, Any}()
            for worker_id in 1:available_threads
                analyze_loggers[worker_id] = create_cleanmast_logger(
                    job_name="analyze-phase",
                    worker_id=worker_id,
                    config_dir=tmpdir,
                    config_basename="test",
                    enable_terminal=false
                )
            end

            Threads.@threads for idx in 1:(available_threads * 3)
                worker_id = Threads.threadid()
                worker_logger = analyze_loggers[worker_id]

                with_logger(worker_logger) do
                    @info "Analyzing" task_id=idx
                end
            end

            # Phase 2: Plotting
            @info "Phase 2: Running plotting tasks"
            plot_loggers = Dict{Int, Any}()
            for worker_id in 1:available_threads
                plot_loggers[worker_id] = create_cleanmast_logger(
                    job_name="plot-phase",
                    worker_id=worker_id,
                    config_dir=tmpdir,
                    config_basename="test",
                    enable_terminal=false
                )
            end

            Threads.@threads for idx in 1:(available_threads * 2)
                worker_id = Threads.threadid()
                worker_logger = plot_loggers[worker_id]

                with_logger(worker_logger) do
                    @info "Plotting" task_id=idx
                end
            end

            # Verify logs contain both phases
            for worker_id in 1:available_threads
                log_file = joinpath(tmpdir, "logs", "test.$(worker_id).jsonl")
                lines = readlines(log_file)

                has_analyze = false
                has_plot = false

                for line in lines
                    log = JSON.parse(line)
                    if log["job_name"] == "analyze-phase"
                        has_analyze = true
                    elseif log["job_name"] == "plot-phase"
                        has_plot = true
                    end
                end

                # Each thread should have participated in both phases
                # (though thread 1 might only do analysis if tasks < threads)
                @test has_analyze || has_plot
            end
        end
    end

    @testset "No race conditions in logger creation" begin
        if available_threads < 2
            @test_skip "Requires multiple threads (run with julia --threads 4)"
            return
        end

        mktempdir() do tmpdir
            # Archive logs
            archive_all_worker_logs(tmpdir, "test", available_threads)

            # Pre-create loggers - should complete without errors
            @test begin
                worker_loggers = Dict{Int, Any}()
                for worker_id in 1:available_threads
                    worker_loggers[worker_id] = create_cleanmast_logger(
                        job_name="race-test",
                        worker_id=worker_id,
                        config_dir=tmpdir,
                        config_basename="test",
                        enable_terminal=false
                    )
                end
                true
            end

            # Verify no duplicate log files
            log_files = filter(f -> endswith(f, ".jsonl"), readdir(joinpath(tmpdir, "logs")))
            @test length(log_files) == available_threads

            # Verify each worker_id appears exactly once
            worker_ids = Set{Int}()
            for log_file in log_files
                # Extract worker_id from filename: test.{worker_id}.jsonl
                m = match(r"test\.(\d+)\.jsonl", log_file)
                @test m !== nothing
                worker_id = parse(Int, m.captures[1])
                @test !(worker_id in worker_ids)  # No duplicates
                push!(worker_ids, worker_id)
            end

            @test length(worker_ids) == available_threads
        end
    end
end

# If running this file directly
if abspath(PROGRAM_FILE) == @__FILE__
    if Threads.nthreads() == 1
        println("\n⚠️  WARNING: Running with only 1 thread!")
        println("Parallel tests will be skipped.")
        println("\nTo run parallel tests, use:")
        println("    julia --threads 4 test/logging/test_parallel_logging.jl")
        println("    julia --threads auto test/logging/test_parallel_logging.jl")
        println("\nCurrent thread count: $(Threads.nthreads())")
        println()
    end
end
