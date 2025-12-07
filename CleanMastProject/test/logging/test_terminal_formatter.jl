using Test
using CleanMastProject.CleanMastLogging.CleanMastLogger.TerminalFormatter
using CleanMastProject.CleanMastLogging.CleanMastLogger.Utils
using Logging
using TerminalLoggers

@testset "Terminal Formatter Tests" begin
    @testset "Logger creation" begin
        buffer = IOBuffer()
        logger = create_terminal_logger("test-job", 1, Logging.Info; stream=buffer)

        @test logger isa TerminalLoggers.TerminalLogger
    end

    @testset "Formatted output" begin
        buffer = IOBuffer()
        logger = create_terminal_logger("test-job", 1, Logging.Info; stream=buffer)

        with_logger(logger) do
            @info "Test message"
        end

        output = String(take!(buffer))
        clean_output = strip_ansi(output)

        @test contains(clean_output, "[test-job:1]")
        @test contains(clean_output, "INFO")
        @test contains(clean_output, "Test message")
    end

    @testset "Multiple log levels" begin
        buffer = IOBuffer()
        logger = create_terminal_logger("test-job", 1, Logging.Debug; stream=buffer)

        with_logger(logger) do
            @debug "Debug message"
            @info "Info message"
            @warn "Warn message"
            @error "Error message"
        end

        output = String(take!(buffer))
        clean_output = strip_ansi(output)

        @test contains(clean_output, "DEBUG")
        @test contains(clean_output, "INFO")
        @test contains(clean_output, "WARN")
        @test contains(clean_output, "ERROR")
    end
end
