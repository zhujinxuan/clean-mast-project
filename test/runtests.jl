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
include("ReconstructSingleMast/test_wind_speed_training.jl")
include("ReconstructSingleMast/test_direction_training.jl")
# Add other test files here as needed

@testset "CleanMast.jl" begin
    include("test_reconstruct_meso.jl")
end
