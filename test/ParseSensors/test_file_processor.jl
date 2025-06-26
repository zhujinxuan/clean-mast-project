# test/ParseSensors/test_file_processor.jl

using Test
using CleanMastProject.ParseSensors.FileProcessor: detect_delimiter, find_header_line, detect_timestamp_format

@testset "FileProcessor Tests" begin

    mktempdir() do temp_dir
        @testset "Delimiter Detection" begin
            # Test with comma
            comma_file = joinpath(temp_dir, "comma.csv")
            write(comma_file, "Header1,Header2\nValue1,Value2\nValue3,Value4\nValue5,Value6\nValue7,Value8\nValue9,Value10")
            @test detect_delimiter(comma_file, 1) == ","

            # Test with tab
            tab_file = joinpath(temp_dir, "tab.csv")
            write(tab_file, "Header1\tHeader2\nValue1\tValue2\nValue3\tValue4\nValue5\tValue6\nValue7\tValue8\nValue9\tValue10")
            @test detect_delimiter(tab_file, 1) == "\t"
        end

        @testset "Header Line Detection" begin
            preamble_file = joinpath(temp_dir, "preamble.txt")
            # Write a file with a preamble and data lines that start with a timestamp
            write(preamble_file, "Preamble 1\nPreamble 2\nHeader1,Header2\n" *
                                 "2024-01-01,2\n2024-01-02,4\n2024-01-03,6\n" *
                                 "2024-01-04,8\n2024-01-05,10\n2024-01-06,12")
            # The header is on line 3. find_header_line should return 3.
            @test find_header_line(preamble_file, nothing, nothing) == 3
            @test find_header_line(preamble_file, nothing, ",") == 3
        end

        @testset "Timestamp Format Detection" begin
            timestamp_file = joinpath(temp_dir, "timestamps.csv")
            write(timestamp_file, "Time,Value\n23/05/2024 10:30,1\n24/05/2024 11:30,2")
            # Delimiter is comma, header is on line 1 (so we skip 0)
            @test detect_timestamp_format(timestamp_file, 1, "Time", ",") == "dd/mm/yyyy HH:MM:SS"
        end
    end

end 