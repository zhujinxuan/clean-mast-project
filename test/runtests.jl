# 文件：./test/runtests.jl

using Test
using Pkg

# 获取 `test` 目录的绝对路径
test_dir = @__DIR__

# 构造相对路径到主项目目录
project_dir = joinpath(test_dir, "..")

# 激活主项目环境
Pkg.activate(project_dir)

# Include all test files
include("MastTimeSeries/test_parsing_column.jl")
include("test_range_rules.jl")
include("test_icing_rules.jl")
include("test_layer_diff_rules.jl")
include("process/test_apply_missing.jl")
include("TowerShading/TowerShading.jl")

macro disabled_testset(args...)
end

@disabled_testset "Single Mast reconstruction" begin
    include("ReconstructSingleMast/test_wind_speed_training.jl")
    include("ReconstructSingleMast/test_direction_training.jl")
end
# Add other test files here as needed


@disabled_testset "Meso reconstruction" begin
    include("ReconstructMeso/test_training.jl")
    include("ReconstructMeso/test_data_processing.jl")
    include("ReconstructMeso/test_reconstruction.jl")
    include("test_reconstruct_meso.jl")
end

@testset "Representative Year" begin
    include("RepresentativeYear/test_analysis.jl")
end
