using Test
using CleanMastProject.PandocUtils

@testset "PandocUtils" begin
    @testset "Pandoc Availability" begin
        @testset "is_pandoc_available returns Bool" begin
            available = PandocUtils.is_pandoc_available()
            @test isa(available, Bool)
        end

        @testset "is_pandoc_available doesn't throw" begin
            result = nothing
            threw_exception = false
            try
                result = PandocUtils.is_pandoc_available()
            catch
                threw_exception = true
            end
            @test !threw_exception
        end
    end

    @testset "Single File Conversion" begin
        mktempdir() do tmpdir
            @testset "Convert valid .typ file" begin
                typ_file = joinpath(tmpdir, "test.typ")
                write(typ_file, """
                    = Test Report

                    This is a test report for pandoc conversion.

                    == Section 1
                    Content here.
                    """)

                if PandocUtils.is_pandoc_available()
                    result = PandocUtils.convert_typ_to_docx(typ_file)
                    @test result == true

                    docx_file = joinpath(tmpdir, "test.docx")
                    @test isfile(docx_file)
                else
                    @info "Pandoc not available, skipping conversion test"
                end
            end

            @testset "Handle missing file" begin
                missing_file = joinpath(tmpdir, "nonexistent.typ")
                result = PandocUtils.convert_typ_to_docx(missing_file)
                @test result == false
            end

            @testset "Handle file with special characters in name" begin
                typ_file = joinpath(tmpdir, "test report.typ")
                write(typ_file, "= Test\n\nContent.")

                if PandocUtils.is_pandoc_available()
                    result = PandocUtils.convert_typ_to_docx(typ_file)
                    @test result == true

                    docx_file = joinpath(tmpdir, "test report.docx")
                    @test isfile(docx_file)
                else
                    @info "Pandoc not available, skipping special character test"
                end
            end
        end
    end

    @testset "Batch Conversion" begin
        @testset "Convert multiple files recursively" begin
            mktempdir() do tmpdir
                subdir = joinpath(tmpdir, "subdir")
                mkpath(subdir)

                file1 = joinpath(tmpdir, "report1.typ")
                file2 = joinpath(tmpdir, "report2.typ")
                file3 = joinpath(subdir, "nested.typ")

                write(file1, "= Report 1\n\nContent 1.")
                write(file2, "= Report 2\n\nContent 2.")
                write(file3, "= Nested Report\n\nNested content.")

                if PandocUtils.is_pandoc_available()
                    count = PandocUtils.convert_typ_files(tmpdir; recursive=true)
                    @test count == 3

                    @test isfile(joinpath(tmpdir, "report1.docx"))
                    @test isfile(joinpath(tmpdir, "report2.docx"))
                    @test isfile(joinpath(subdir, "nested.docx"))
                else
                    @info "Pandoc not available, skipping batch recursive test"
                end
            end
        end

        @testset "Convert files non-recursively" begin
            mktempdir() do tmpdir
                subdir = joinpath(tmpdir, "subdir")
                mkpath(subdir)

                file1 = joinpath(tmpdir, "report1.typ")
                file2 = joinpath(tmpdir, "report2.typ")
                file3 = joinpath(subdir, "nested.typ")

                write(file1, "= Report 1\n\nContent 1.")
                write(file2, "= Report 2\n\nContent 2.")
                write(file3, "= Nested Report\n\nNested content.")

                if PandocUtils.is_pandoc_available()
                    count = PandocUtils.convert_typ_files(tmpdir; recursive=false)
                    @test count == 2

                    @test isfile(joinpath(tmpdir, "report1.docx"))
                    @test isfile(joinpath(tmpdir, "report2.docx"))
                    @test !isfile(joinpath(subdir, "nested.docx"))
                else
                    @info "Pandoc not available, skipping batch non-recursive test"
                end
            end
        end

        @testset "Handle empty directory" begin
            mktempdir() do tmpdir
                empty_dir = joinpath(tmpdir, "empty")
                mkpath(empty_dir)

                count = PandocUtils.convert_typ_files(empty_dir; recursive=true)
                @test count == 0
            end
        end

        @testset "Handle missing directory" begin
            mktempdir() do tmpdir
                missing_dir = joinpath(tmpdir, "nonexistent")
                count = PandocUtils.convert_typ_files(missing_dir; recursive=true)
                @test count == 0
            end
        end
    end

    @testset "Helper Function" begin
        mktempdir() do tmpdir
            @testset "convert_main_report" begin
                typ_file = joinpath(tmpdir, "report.typ")
                write(typ_file, "= Main Report\n\nContent.")

                if PandocUtils.is_pandoc_available()
                    result = PandocUtils.convert_main_report(tmpdir, "report.typ")
                    @test result == true
                    @test isfile(joinpath(tmpdir, "report.docx"))
                else
                    @info "Pandoc not available, skipping helper function test"
                end
            end

            @testset "convert_main_report with custom filename" begin
                typ_file = joinpath(tmpdir, "custom.typ")
                write(typ_file, "= Custom Report\n\nContent.")

                if PandocUtils.is_pandoc_available()
                    result = PandocUtils.convert_main_report(tmpdir, "custom.typ")
                    @test result == true
                    @test isfile(joinpath(tmpdir, "custom.docx"))
                else
                    @info "Pandoc not available, skipping custom filename test"
                end
            end
        end
    end

    @testset "User Wrapper Functions" begin
        mktempdir() do tmpdir
            @testset "pandoc_try_convert with valid file" begin
                typ_file = joinpath(tmpdir, "test.typ")
                write(typ_file, "= Test\n\nContent.")

                threw_exception = false
                try
                    PandocUtils.pandoc_try_convert(tmpdir, "test.typ")
                catch
                    threw_exception = true
                end
                @test !threw_exception

                if PandocUtils.is_pandoc_available()
                    @test isfile(joinpath(tmpdir, "test.docx"))
                end
            end

            @testset "pandoc_try_convert with missing file" begin
                threw_exception = false
                try
                    PandocUtils.pandoc_try_convert(tmpdir, "missing.typ")
                catch
                    threw_exception = true
                end
                @test !threw_exception
            end

            @testset "pandoc_try_convert_all with directory" begin
                file1 = joinpath(tmpdir, "report1.typ")
                file2 = joinpath(tmpdir, "report2.typ")
                write(file1, "= Report 1\n")
                write(file2, "= Report 2\n")

                threw_exception = false
                try
                    PandocUtils.pandoc_try_convert_all(tmpdir)
                catch
                    threw_exception = true
                end
                @test !threw_exception

                if PandocUtils.is_pandoc_available()
                    @test isfile(joinpath(tmpdir, "report1.docx"))
                    @test isfile(joinpath(tmpdir, "report2.docx"))
                end
            end

            @testset "pandoc_try_convert_all with empty directory" begin
                empty_dir = joinpath(tmpdir, "empty")
                mkpath(empty_dir)

                threw_exception = false
                try
                    PandocUtils.pandoc_try_convert_all(empty_dir)
                catch
                    threw_exception = true
                end
                @test !threw_exception
            end

            @testset "pandoc_try_convert_all non-recursive" begin
                subdir = joinpath(tmpdir, "subdir2")
                mkpath(subdir)
                file1 = joinpath(tmpdir, "top.typ")
                file2 = joinpath(subdir, "nested.typ")
                write(file1, "= Top\n")
                write(file2, "= Nested\n")

                threw_exception = false
                try
                    PandocUtils.pandoc_try_convert_all(tmpdir; recursive=false)
                catch
                    threw_exception = true
                end
                @test !threw_exception

                if PandocUtils.is_pandoc_available()
                    @test isfile(joinpath(tmpdir, "top.docx"))
                    @test !isfile(joinpath(subdir, "nested.docx"))
                end
            end
        end
    end

    @testset "Integration Tests" begin
        mktempdir() do tmpdir
            @testset "End-to-end workflow" begin
                typ_content = """
                = Wind Resource Assessment Report

                == Executive Summary
                This report provides analysis of wind measurement data.

                == Data Coverage
                The measurement period spans from 2023-01 to 2023-12.

                == Wind Speed Analysis
                Average wind speed at 100m: 7.5 m/s

                == Conclusion
                The site shows good wind resource potential.
                """

                typ_file = joinpath(tmpdir, "full_report.typ")
                write(typ_file, typ_content)

                if PandocUtils.is_pandoc_available()
                    result = PandocUtils.convert_typ_to_docx(typ_file)
                    @test result == true

                    docx_file = joinpath(tmpdir, "full_report.docx")
                    @test isfile(docx_file)
                    @test filesize(docx_file) > 0
                else
                    @info "Pandoc not available, skipping integration test"
                end
            end
        end
    end
end
