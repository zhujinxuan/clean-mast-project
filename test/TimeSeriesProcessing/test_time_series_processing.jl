module TestTimeSeriesProcessing

using Test

# Include the individual test modules
include("test_interpolation.jl")
include("test_regularization.jl")

@testset "TimeSeriesProcessing" begin
    @testset "Interpolation" begin
        TestInterpolation.runtests()
    end

    @testset "Regularization" begin
        TestRegularization.runtests()
    end

end

end 