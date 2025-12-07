module TestTurbulenceNaNFix

using Test
using DataFrames
using Dates
using Statistics
using CleanMastProject.Types.Sector: DIRECTION_16_SECTORS
using CleanMastProject.ReportTimeSeries.Turbulence: calculate_ti_matrix, calculate_ti_series, save_meteodyn_ti

@testset "Turbulence NaN Fix Tests" begin
    @testset "NaN Prevention - Core Fix" begin
        @testset "All missing TI values in sector/bin" begin
            ti_df = DataFrame(
                ws_avg = fill(10.0, 10),
                ws_sd = fill(missing, 10),
                wd = [45.0 + i for i in 1:10],
                ti = fill(missing, 10),
                sector = fill("NNE", 10)
            )

            wind_speed_bins = [0.0, 5.0, 15.0, 30.0]
            mean_ti = 0.15

            result = calculate_ti_matrix(ti_df, wind_speed_bins, mean_ti)

            @test !any(isnan.(result[2, "NNE"]))
            @test result[2, "NNE"] == mean_ti
        end

        @testset "Partial missing with sufficient valid data" begin
            ti_df = DataFrame(
                ws_avg = fill(10.0, 10),
                ws_sd = vcat(fill(1.5, 7), fill(missing, 3)),
                wd = fill(45.0, 10),
                ti = vcat(fill(0.15, 7), fill(missing, 3)),
                sector = fill("NNE", 10)
            )

            wind_speed_bins = [0.0, 5.0, 15.0, 30.0]
            mean_ti = 0.20

            result = calculate_ti_matrix(ti_df, wind_speed_bins, mean_ti)

            @test !isnan(result[2, "NNE"])
            @test result[2, "NNE"] ≈ 0.15 atol=0.001
        end

        @testset "Partial missing with insufficient valid data" begin
            ti_df = DataFrame(
                ws_avg = fill(10.0, 10),
                ws_sd = vcat(fill(1.5, 4), fill(missing, 6)),
                wd = fill(45.0, 10),
                ti = vcat(fill(0.15, 4), fill(missing, 6)),
                sector = fill("NNE", 10)
            )

            wind_speed_bins = [0.0, 5.0, 15.0, 30.0]
            mean_ti = 0.20

            result = calculate_ti_matrix(ti_df, wind_speed_bins, mean_ti)

            @test !isnan(result[2, "NNE"])
            @test result[2, "NNE"] == mean_ti
        end

        @testset "Exactly 5 valid values (boundary case)" begin
            ti_df = DataFrame(
                ws_avg = fill(10.0, 10),
                ws_sd = vcat(fill(1.5, 5), fill(missing, 5)),
                wd = fill(45.0, 10),
                ti = vcat(fill(0.15, 5), fill(missing, 5)),
                sector = fill("NNE", 10)
            )

            wind_speed_bins = [0.0, 5.0, 15.0, 30.0]
            mean_ti = 0.20

            result = calculate_ti_matrix(ti_df, wind_speed_bins, mean_ti)

            @test !isnan(result[2, "NNE"])
            @test result[2, "NNE"] ≈ 0.15 atol=0.001
        end

        @testset "All valid values" begin
            ti_df = DataFrame(
                ws_avg = fill(10.0, 10),
                ws_sd = fill(1.5, 10),
                wd = fill(45.0, 10),
                ti = fill(0.15, 10),
                sector = fill("NNE", 10)
            )

            wind_speed_bins = [0.0, 5.0, 15.0, 30.0]
            mean_ti = 0.20

            result = calculate_ti_matrix(ti_df, wind_speed_bins, mean_ti)

            @test !isnan(result[2, "NNE"])
            @test result[2, "NNE"] ≈ 0.15 atol=0.001
        end
    end

    @testset "Matrix Fallback Logic" begin
        @testset "Mean TI initialization preserved" begin
            ti_df = DataFrame(
                ws_avg = Float64[],
                ws_sd = Float64[],
                wd = Float64[],
                ti = Float64[],
                sector = String[]
            )

            wind_speed_bins = [0.0, 5.0, 15.0, 30.0]
            mean_ti = 0.18

            result = calculate_ti_matrix(ti_df, wind_speed_bins, mean_ti)

            for sector in DIRECTION_16_SECTORS
                @test all(result[!, sector.name] .== mean_ti)
            end
        end

        @testset "Multiple sectors with mixed data quality" begin
            ti_df = DataFrame(
                ws_avg = vcat(
                    fill(10.0, 10),
                    fill(10.0, 10),
                    fill(10.0, 3)
                ),
                ws_sd = vcat(
                    fill(1.5, 10),
                    vcat(fill(1.2, 3), fill(missing, 7)),
                    fill(1.8, 3)
                ),
                wd = vcat(
                    fill(0.0, 10),
                    fill(45.0, 10),
                    fill(90.0, 3)
                ),
                ti = vcat(
                    fill(0.15, 10),
                    vcat(fill(0.12, 3), fill(missing, 7)),
                    fill(0.18, 3)
                ),
                sector = vcat(
                    fill("N", 10),
                    fill("NNE", 10),
                    fill("E", 3)
                )
            )

            wind_speed_bins = [0.0, 5.0, 15.0, 30.0]
            mean_ti = 0.20

            result = calculate_ti_matrix(ti_df, wind_speed_bins, mean_ti)

            @test result[2, "N"] ≈ 0.15 atol=0.001
            @test result[2, "NNE"] == mean_ti
            @test result[2, "E"] == mean_ti
        end

        @testset "No NaN values in any sector column" begin
            ti_df = DataFrame(
                ws_avg = vcat(fill(10.0, 100), fill(missing, 20)),
                ws_sd = vcat(fill(1.5, 50), fill(missing, 70)),
                wd = vcat([float(i % 360) for i in 1:100], fill(missing, 20)),
                ti = vcat(fill(0.15, 50), fill(missing, 70)),
                sector = vcat([DIRECTION_16_SECTORS[i % 16 + 1].name for i in 1:100],
                             fill(missing, 20))
            )

            wind_speed_bins = collect(0.0:5.0:30.0)
            mean_ti = 0.16

            result = calculate_ti_matrix(ti_df, wind_speed_bins, mean_ti)

            for sector in DIRECTION_16_SECTORS
                @test !any(isnan.(result[!, sector.name]))
            end
        end
    end

    @testset "Integration with TI Calculation" begin
        @testset "Missing ws_sd propagates to ti" begin
            df = DataFrame(
                ws_avg = [10.0, 12.0, 8.0],
                ws_sd = [1.5, missing, 1.2],
                wd = [45.0, 90.0, 135.0]
            )

            result = calculate_ti_series(df, :ws_avg, :ws_sd, :wd)

            @test !ismissing(result[1, :ti])
            @test ismissing(result[2, :ti])
            @test !ismissing(result[3, :ti])
        end

        @testset "Missing ws_avg propagates to ti" begin
            df = DataFrame(
                ws_avg = [10.0, missing, 8.0],
                ws_sd = [1.5, 1.3, 1.2],
                wd = [45.0, 90.0, 135.0]
            )

            result = calculate_ti_series(df, :ws_avg, :ws_sd, :wd)

            @test !ismissing(result[1, :ti])
            @test ismissing(result[2, :ti])
            @test !ismissing(result[3, :ti])
        end

        @testset "TI formula verification" begin
            df = DataFrame(
                ws_avg = [10.0, 0.5, 1.0, 15.0],
                ws_sd = [1.5, 0.1, 0.15, 2.1],
                wd = [45.0, 90.0, 135.0, 180.0]
            )

            result = calculate_ti_series(df, :ws_avg, :ws_sd, :wd)

            @test result[1, :ti] ≈ 1.5 / 10.0 atol=0.001
            @test result[2, :ti] ≈ 0.1 / 1.0 atol=0.001
            @test result[3, :ti] ≈ 0.15 / 1.0 atol=0.001
            @test result[4, :ti] ≈ 2.1 / 15.0 atol=0.001
        end
    end

    @testset "End-to-End Workflow" begin
        @testset "Realistic sparse data scenario" begin
            n_total = 1000
            n_valid = Int(floor(0.7 * n_total))
            n_missing = n_total - n_valid

            ws_avg_values = vcat(
                rand(4.0:0.1:25.0, n_valid),
                fill(missing, n_missing)
            )
            ws_sd_values = vcat(
                rand(0.5:0.01:3.0, n_valid),
                fill(missing, n_missing)
            )
            wd_values = vcat(
                rand(0.0:1.0:359.0, n_valid),
                fill(missing, n_missing)
            )

            df = DataFrame(
                ws_avg = ws_avg_values,
                ws_sd = ws_sd_values,
                wd = wd_values
            )

            result = calculate_ti_series(df, :ws_avg, :ws_sd, :wd)

            valid_ti_count = count(!ismissing, result.ti)
            @test valid_ti_count == n_valid

            mean_ti = mean(skipmissing(result.ti))
            wind_speed_bins = collect(0.0:1.0:30.0)

            ti_matrix = calculate_ti_matrix(result, wind_speed_bins, mean_ti)

            for sector in DIRECTION_16_SECTORS
                @test !any(isnan.(ti_matrix[!, sector.name]))
            end
        end

        @testset "Low wind speed bins with rare data" begin
            ti_df = DataFrame(
                ws_avg = vcat(fill(0.5, 2), fill(10.0, 100)),
                ws_sd = vcat(fill(0.1, 2), fill(1.5, 100)),
                wd = vcat([45.0, 45.0], rand(0.0:1.0:359.0, 100)),
                ti = vcat(fill(0.20, 2), fill(0.15, 100)),
                sector = vcat(fill("NNE", 2),
                             [DIRECTION_16_SECTORS[i % 16 + 1].name for i in 1:100])
            )

            wind_speed_bins = [0.0, 1.0, 5.0, 15.0, 30.0]
            mean_ti = 0.16

            result = calculate_ti_matrix(ti_df, wind_speed_bins, mean_ti)

            @test result[1, "NNE"] == mean_ti
            @test !isnan(result[2, "NNE"])
        end

        @testset "Prevailing vs non-prevailing wind sectors" begin
            ti_df = DataFrame(
                ws_avg = vcat(fill(10.0, 100), fill(10.0, 10)),
                ws_sd = vcat(fill(1.5, 100), fill(1.2, 10)),
                wd = vcat(fill(45.0, 100), fill(180.0, 10)),
                ti = vcat(fill(0.15, 100), fill(0.12, 10)),
                sector = vcat(fill("NNE", 100), fill("S", 10))
            )

            wind_speed_bins = [0.0, 5.0, 15.0, 30.0]
            mean_ti = 0.18

            result = calculate_ti_matrix(ti_df, wind_speed_bins, mean_ti)

            @test result[2, "NNE"] ≈ 0.15 atol=0.001
            @test result[2, "S"] ≈ 0.12 atol=0.001
        end
    end

    @testset "File Output Validation" begin
        @testset "No NaN strings in meteodyn file" begin
            mktempdir() do tmpdir
                ti_matrix = DataFrame(
                    v_min = [0.0, 5.0, 10.0],
                    v_max = [5.0, 10.0, 15.0]
                )

                for sector in DIRECTION_16_SECTORS
                    ti_matrix[!, sector.name] = [0.15, 0.14, 0.13]
                end

                save_meteodyn_ti(tmpdir, ti_matrix, 100.0)

                output_file = joinpath(tmpdir, "meteodyn_ti_100.0m.txt")
                @test isfile(output_file)

                content = read(output_file, String)
                @test !occursin("NaN", content)
                @test !occursin("nan", content)
            end
        end

        @testset "All values are valid floats" begin
            mktempdir() do tmpdir
                ti_matrix = DataFrame(
                    v_min = [0.0, 5.0, 10.0],
                    v_max = [5.0, 10.0, 15.0]
                )

                for sector in DIRECTION_16_SECTORS
                    ti_matrix[!, sector.name] = [0.15, 0.14, 0.13]
                end

                save_meteodyn_ti(tmpdir, ti_matrix, 80.0)

                output_file = joinpath(tmpdir, "meteodyn_ti_80.0m.txt")
                lines = readlines(output_file)

                @test parse(Int, lines[1]) == 3

                for line in lines[2:end]
                    values = split(line, "\t")
                    for val in values
                        parsed = parse(Float64, val)
                        @test !isnan(parsed)
                        @test !isinf(parsed)
                    end
                end
            end
        end

        @testset "Fallback values present where expected" begin
            mktempdir() do tmpdir
                ti_df = DataFrame(
                    ws_avg = fill(10.0, 3),
                    ws_sd = fill(missing, 3),
                    wd = fill(45.0, 3),
                    ti = fill(missing, 3),
                    sector = fill("NNE", 3)
                )

                wind_speed_bins = [0.0, 5.0, 15.0, 30.0]
                mean_ti = 0.17

                ti_matrix = calculate_ti_matrix(ti_df, wind_speed_bins, mean_ti)

                save_meteodyn_ti(tmpdir, ti_matrix, 100.0)

                output_file = joinpath(tmpdir, "meteodyn_ti_100.0m.txt")
                lines = readlines(output_file)

                for line in lines[2:end]
                    values = split(line, "\t")
                    for val in values[2:end]
                        parsed = parse(Float64, val)
                        @test parsed ≈ mean_ti atol=0.001
                    end
                end
            end
        end
    end
end

end
