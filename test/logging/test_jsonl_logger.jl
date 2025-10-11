using Test
using CleanMastProject.CleanMastLogging.CleanMastLogger.JSONLLogger
using Logging
using JSON

@testset "JSONL Logger Tests" begin
    @testset "Basic logging" begin
        mktempdir() do tmpdir
            log_file = joinpath(tmpdir, "test.1.jsonl")
            logger = JSONLFileLogger(log_file, "test-job", 1)

            with_logger(logger) do
                @info "Test message 1"
                @warn "Test warning"
                @error "Test error"
            end

            @test isfile(log_file)
            lines = readlines(log_file)
            @test length(lines) == 3

            log1 = JSON.parse(lines[1])
            @test log1["level"] == "Info"
            @test log1["job_name"] == "test-job"
            @test log1["worker_id"] == 1
            @test log1["message"] == "Test message 1"
            @test haskey(log1, "timestamp")
        end
    end

    @testset "Multiline messages" begin
        mktempdir() do tmpdir
            log_file = joinpath(tmpdir, "test.1.jsonl")
            logger = JSONLFileLogger(log_file, "test-job", 1)

            with_logger(logger) do
                @info "Line 1\nLine 2\nLine 3"
            end

            line = readline(log_file)
            log = JSON.parse(line)

            @test log["message"] isa Vector
            @test length(log["message"]) == 3
            @test log["message"][1] == "Line 1"
        end
    end

    @testset "Error with exception" begin
        mktempdir() do tmpdir
            log_file = joinpath(tmpdir, "test.1.jsonl")
            logger = JSONLFileLogger(log_file, "test-job", 1)

            with_logger(logger) do
                try
                    error("Test error")
                catch e
                    @error "Caught error" exception=(e, catch_backtrace())
                end
            end

            line = readline(log_file)
            log = JSON.parse(line)

            @test log["level"] == "Error"
            @test haskey(log, "error_type")
            @test log["error_type"] == "ErrorException"
            @test haskey(log, "stacktrace")
            @test log["stacktrace"] isa Vector
        end
    end
end
