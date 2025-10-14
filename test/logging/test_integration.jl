using Test
using CleanMastProject.CleanMastLogging
using Logging
using JSON

@testset "Integration Tests" begin
    @testset "TeeLogger - both outputs" begin
        mktempdir() do tmpdir
            terminal_buffer = IOBuffer()

            logger = create_cleanmast_logger(
                job_name="test-job",
                worker_id=1,
                config_dir=tmpdir,
                config_basename="test",
                terminal_stream=terminal_buffer
            )

            with_logger(logger) do
                @info "Test message"
                @warn "Test warning"
            end

            terminal_output = String(take!(terminal_buffer))
            @test contains(terminal_output, "[test-job:1]")
            @test contains(terminal_output, "Test message")

            log_file = joinpath(tmpdir, "logs", "test.1.jsonl")
            @test isfile(log_file)

            lines = readlines(log_file)
            @test length(lines) == 2

            log1 = JSON.parse(lines[1])
            @test log1["message"] == "Test message"
        end
    end

    @testset "Terminal only" begin
        mktempdir() do tmpdir
            terminal_buffer = IOBuffer()

            logger = create_cleanmast_logger(
                job_name="test-job",
                worker_id=1,
                config_dir=tmpdir,
                config_basename="test",
                terminal_stream=terminal_buffer,
                enable_file=false
            )

            with_logger(logger) do
                @info "Test message"
            end

            terminal_output = String(take!(terminal_buffer))
            @test contains(terminal_output, "Test message")

            log_file = joinpath(tmpdir, "logs", "test.1.jsonl")
            @test !isfile(log_file)
        end
    end

    @testset "File only" begin
        mktempdir() do tmpdir
            logger = create_cleanmast_logger(
                job_name="test-job",
                worker_id=1,
                config_dir=tmpdir,
                config_basename="test",
                enable_terminal=false
            )

            with_logger(logger) do
                @info "Test message"
            end

            log_file = joinpath(tmpdir, "logs", "test.1.jsonl")
            @test isfile(log_file)

            line = readline(log_file)
            log = JSON.parse(line)
            @test log["message"] == "Test message"
        end
    end

    @testset "Different worker IDs" begin
        mktempdir() do tmpdir
            logger1 = create_cleanmast_logger(
                job_name="test-job",
                worker_id=1,
                config_dir=tmpdir,
                config_basename="test",
                enable_terminal=false
            )

            logger2 = create_cleanmast_logger(
                job_name="test-job",
                worker_id=2,
                config_dir=tmpdir,
                config_basename="test",
                enable_terminal=false
            )

            with_logger(logger1) do
                @info "Worker 1 message"
            end

            with_logger(logger2) do
                @info "Worker 2 message"
            end

            log_file1 = joinpath(tmpdir, "logs", "test.1.jsonl")
            log_file2 = joinpath(tmpdir, "logs", "test.2.jsonl")

            @test isfile(log_file1)
            @test isfile(log_file2)

            log1 = JSON.parse(readline(log_file1))
            log2 = JSON.parse(readline(log_file2))

            @test log1["worker_id"] == 1
            @test log2["worker_id"] == 2
        end
    end
end
