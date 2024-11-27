# 文件：./test/runtests.jl

using Test

include("../src/CleanMastProject.jl")
# Include all test files
include("test_MastTimeSeries_parsing.jl")

# Add other test files here as needed
