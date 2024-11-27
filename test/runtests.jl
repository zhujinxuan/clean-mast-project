# 文件：./test/runtests.jl

using Test

include("../src/CleanMastProject.jl")
# Include all test files
include("test_MastTimeSeries_parsing.jl")
include("test_range_rules.jl")

# Add other test files here as needed
