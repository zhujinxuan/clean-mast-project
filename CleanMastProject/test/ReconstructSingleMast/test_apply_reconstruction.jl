using Test
using DataFrames
using Dates
using CleanMastProject.ReconstructSingleMast.ProcessData: apply_success_reconstruction!
using CleanMastProject.Types.ReconstructSingleMast: ReconstructedSuccess

@testset "apply_success_reconstruction!" begin
    @testset "single column, single value" begin
        # Create simple DataFrame with missing value
        df = DataFrame(
            :timestamp => [DateTime(2024,1,1,10,0,0), DateTime(2024,1,1,10,10,0)],
            :ws_80m => [8.0, missing]
        )

        # Create reconstruction result
        successes = [
            ReconstructedSuccess(DateTime(2024,1,1,10,10,0), :ws_80m, 8.5)
        ]

        # Apply reconstruction
        apply_success_reconstruction!(df, successes)

        # Verify value was assigned
        @test df[2, :ws_80m] == 8.5
        @test df[1, :ws_80m] == 8.0  # Original value unchanged
    end

    @testset "single column, multiple values" begin
        # Create DataFrame with multiple missing values
        df = DataFrame(
            :timestamp => [
                DateTime(2024,1,1,10,0,0),
                DateTime(2024,1,1,10,10,0),
                DateTime(2024,1,1,10,20,0),
                DateTime(2024,1,1,10,30,0)
            ],
            :ws_100m => [9.0, missing, missing, 9.5]
        )

        # Create multiple reconstruction results for same column
        successes = [
            ReconstructedSuccess(DateTime(2024,1,1,10,10,0), :ws_100m, 9.2),
            ReconstructedSuccess(DateTime(2024,1,1,10,20,0), :ws_100m, 9.3)
        ]

        apply_success_reconstruction!(df, successes)

        # Verify all values assigned correctly
        @test df[1, :ws_100m] == 9.0    # Original
        @test df[2, :ws_100m] == 9.2    # Reconstructed
        @test df[3, :ws_100m] == 9.3    # Reconstructed
        @test df[4, :ws_100m] == 9.5    # Original
    end

    @testset "multiple columns, independent assignment" begin
        # Create DataFrame with missing values in different columns
        df = DataFrame(
            :timestamp => [
                DateTime(2024,1,1,10,0,0),
                DateTime(2024,1,1,10,10,0),
                DateTime(2024,1,1,10,20,0)
            ],
            :ws_80m => [8.0, missing, 8.3],
            :ws_100m => [9.0, 9.2, missing],
            :wd_80m => [45.0, missing, 50.0]
        )

        # Create reconstruction results for different columns
        successes = [
            ReconstructedSuccess(DateTime(2024,1,1,10,10,0), :ws_80m, 8.15),
            ReconstructedSuccess(DateTime(2024,1,1,10,20,0), :ws_100m, 9.25),
            ReconstructedSuccess(DateTime(2024,1,1,10,10,0), :wd_80m, 47.5)
        ]

        apply_success_reconstruction!(df, successes)

        # Verify each column assigned independently
        @test df[2, :ws_80m] == 8.15
        @test df[3, :ws_100m] == 9.25
        @test df[2, :wd_80m] == 47.5

        # Verify other values unchanged
        @test df[1, :ws_80m] == 8.0
        @test df[1, :ws_100m] == 9.0
        @test df[1, :wd_80m] == 45.0
    end

    @testset "empty successes - no-op" begin
        # Create DataFrame
        df = DataFrame(
            :timestamp => [DateTime(2024,1,1,10,0,0), DateTime(2024,1,1,10,10,0)],
            :ws_80m => [8.0, missing]
        )

        # Save original values
        original_value_1 = df[1, :ws_80m]
        original_value_2 = df[2, :ws_80m]

        # Apply with empty successes
        successes = ReconstructedSuccess[]
        apply_success_reconstruction!(df, successes)

        # Verify DataFrame unchanged
        @test df[1, :ws_80m] == original_value_1
        @test ismissing(original_value_2) && ismissing(df[2, :ws_80m])  # Still missing
    end

    @testset "missing value replacement verification" begin
        # Create DataFrame with all missing values in a column
        df = DataFrame(
            :timestamp => [
                DateTime(2024,1,1,10,0,0),
                DateTime(2024,1,1,10,10,0),
                DateTime(2024,1,1,10,20,0)
            ],
            :ws_80m => Vector{Union{Missing, Float64}}([missing, missing, missing])
        )

        # Reconstruct all values
        successes = [
            ReconstructedSuccess(DateTime(2024,1,1,10,0,0), :ws_80m, 8.0),
            ReconstructedSuccess(DateTime(2024,1,1,10,10,0), :ws_80m, 8.2),
            ReconstructedSuccess(DateTime(2024,1,1,10,20,0), :ws_80m, 8.4)
        ]

        apply_success_reconstruction!(df, successes)

        # Verify all missing values replaced
        @test !any(ismissing, df.ws_80m)
        @test df[1, :ws_80m] == 8.0
        @test df[2, :ws_80m] == 8.2
        @test df[3, :ws_80m] == 8.4
    end

    @testset "non-consecutive timestamps" begin
        # Create DataFrame with gaps
        df = DataFrame(
            :timestamp => [
                DateTime(2024,1,1,10,0,0),
                DateTime(2024,1,1,10,10,0),
                DateTime(2024,1,1,10,30,0),  # Gap: 10:20 missing
                DateTime(2024,1,1,10,40,0)
            ],
            :ws_80m => [8.0, missing, missing, 8.5]
        )

        # Reconstruct only specific timestamps
        successes = [
            ReconstructedSuccess(DateTime(2024,1,1,10,10,0), :ws_80m, 8.15),
            ReconstructedSuccess(DateTime(2024,1,1,10,30,0), :ws_80m, 8.35)
        ]

        apply_success_reconstruction!(df, successes)

        # Verify correct timestamps updated
        @test df[1, :ws_80m] == 8.0     # Original
        @test df[2, :ws_80m] == 8.15    # Reconstructed at 10:10
        @test df[3, :ws_80m] == 8.35    # Reconstructed at 10:30
        @test df[4, :ws_80m] == 8.5     # Original
    end

    @testset "overlapping timestamps for different columns" begin
        # Same timestamp needs reconstruction in multiple columns
        df = DataFrame(
            :timestamp => [DateTime(2024,1,1,10,0,0), DateTime(2024,1,1,10,10,0)],
            :ws_80m => [8.0, missing],
            :ws_100m => [9.0, missing],
            :wd_80m => [45.0, missing]
        )

        successes = [
            ReconstructedSuccess(DateTime(2024,1,1,10,10,0), :ws_80m, 8.2),
            ReconstructedSuccess(DateTime(2024,1,1,10,10,0), :ws_100m, 9.3),
            ReconstructedSuccess(DateTime(2024,1,1,10,10,0), :wd_80m, 47.0)
        ]

        apply_success_reconstruction!(df, successes)

        # Verify all columns at same timestamp updated correctly
        @test df[2, :ws_80m] == 8.2
        @test df[2, :ws_100m] == 9.3
        @test df[2, :wd_80m] == 47.0
    end

    @testset "partial column reconstruction" begin
        # Reconstruct some but not all missing values
        df = DataFrame(
            :timestamp => [
                DateTime(2024,1,1,10,0,0),
                DateTime(2024,1,1,10,10,0),
                DateTime(2024,1,1,10,20,0),
                DateTime(2024,1,1,10,30,0)
            ],
            :ws_80m => [8.0, missing, missing, missing]
        )

        # Only reconstruct middle value
        successes = [
            ReconstructedSuccess(DateTime(2024,1,1,10,10,0), :ws_80m, 8.15)
        ]

        apply_success_reconstruction!(df, successes)

        # Verify only specified value assigned
        @test df[1, :ws_80m] == 8.0
        @test df[2, :ws_80m] == 8.15
        @test ismissing(df[3, :ws_80m])  # Still missing
        @test ismissing(df[4, :ws_80m])  # Still missing
    end

    @testset "overwrite existing non-missing values" begin
        # Test that reconstruction can overwrite non-missing values
        # (This might happen if re-running reconstruction)
        df = DataFrame(
            :timestamp => [DateTime(2024,1,1,10,0,0), DateTime(2024,1,1,10,10,0)],
            :ws_80m => [8.0, 8.1]  # Both have values
        )

        successes = [
            ReconstructedSuccess(DateTime(2024,1,1,10,10,0), :ws_80m, 8.5)
        ]

        apply_success_reconstruction!(df, successes)

        # Verify value was overwritten
        @test df[2, :ws_80m] == 8.5
        @test df[1, :ws_80m] == 8.0  # Unchanged
    end
end
