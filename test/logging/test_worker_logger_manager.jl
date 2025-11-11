using Test
using Logging
using CleanMastProject.CleanMastLogging

@testset "WorkerLoggerManager Tests" begin
    mktempdir() do tmpdir
        @testset "Constructor" begin
            manager = WorkerLoggerManager(
                tmpdir,
                "test_job";
                max_threads=100
            )

            @test length(manager.loggers) == 100
            @test all(isnothing, manager.loggers)
            @test manager.config_dir == tmpdir
            @test manager.config_basename == "test_job"
            @test manager.terminal_level == Logging.Info
            @test manager.file_level == Logging.Debug
        end

        @testset "get_logger - basic functionality" begin
            manager = WorkerLoggerManager(tmpdir, "test_job")

            logger1 = get_logger(manager, 1)
            @test logger1 !== nothing
            @test manager.loggers[1] === logger1

            logger1_again = get_logger(manager, 1)
            @test logger1_again === logger1
        end

        @testset "get_logger - multiple thread IDs" begin
            manager = WorkerLoggerManager(tmpdir, "test_job")

            logger2 = get_logger(manager, 2)
            logger3 = get_logger(manager, 3)
            logger5 = get_logger(manager, 5)

            @test logger2 !== nothing
            @test logger3 !== nothing
            @test logger5 !== nothing
            @test logger2 !== logger3
            @test logger3 !== logger5
            @test manager.loggers[2] === logger2
            @test manager.loggers[3] === logger3
            @test manager.loggers[5] === logger5
        end

        @testset "get_logger - bounds checking" begin
            manager = WorkerLoggerManager(tmpdir, "test_job"; max_threads=10)

            @test_throws ErrorException get_logger(manager, 0)
            @test_throws ErrorException get_logger(manager, 11)
            @test_throws ErrorException get_logger(manager, -1)
            @test_throws ErrorException get_logger(manager, 1000)
        end

        @testset "get_logger - edge cases" begin
            manager = WorkerLoggerManager(tmpdir, "test_job"; max_threads=1000)

            logger1 = get_logger(manager, 1)
            logger1000 = get_logger(manager, 1000)

            @test logger1 !== nothing
            @test logger1000 !== nothing
            @test logger1 !== logger1000
        end

        @testset "cleanup!" begin
            manager = WorkerLoggerManager(tmpdir, "test_job")

            get_logger(manager, 1)
            get_logger(manager, 2)
            get_logger(manager, 3)

            @test manager.loggers[1] !== nothing
            @test manager.loggers[2] !== nothing
            @test manager.loggers[3] !== nothing

            cleanup!(manager)

            @test all(isnothing, manager.loggers)
        end

        @testset "Logging with WorkerLoggerManager" begin
            manager = WorkerLoggerManager(
                tmpdir,
                "test_logging";
                enable_terminal=false,
                enable_file=true
            )

            logger = get_logger(manager, 1)

            with_logger(logger) do
                @info "Test message"
                @warn "Warning message"
            end

            log_file = joinpath(tmpdir, "logs", "test_logging.1.jsonl")
            @test isfile(log_file)

            content = read(log_file, String)
            @test contains(content, "Test message")
            @test contains(content, "Warning message")

            cleanup!(manager)
        end

        if Threads.nthreads() > 1
            @testset "Parallel access" begin
                manager = WorkerLoggerManager(
                    tmpdir,
                    "test_parallel";
                    enable_terminal=false,
                    enable_file=true
                )

                accessed_tids = Set{Int}()
                tid_lock = ReentrantLock()

                Threads.@threads for i in 1:100
                    tid = Threads.threadid()
                    logger = get_logger(manager, tid)

                    lock(tid_lock) do
                        push!(accessed_tids, tid)
                    end

                    with_logger(logger) do
                        @info "Iteration $i on thread $tid"
                    end
                end

                for tid in accessed_tids
                    log_file = joinpath(tmpdir, "logs", "test_parallel.$tid.jsonl")
                    @test isfile(log_file)
                end

                cleanup!(manager)
            end
        else
            @test_broken false  # Parallel test skipped
        end
    end
end
