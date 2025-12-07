#!/usr/bin/env julia

# Activate the CleanMastProject environment
using Pkg
project_path = abspath(joinpath(@__DIR__, "..", "CleanMastProject"))
Pkg.activate(project_path)

using CleanMastProject.CleanMastCli: command_main

if abspath(PROGRAM_FILE) == @__FILE__
    command_main(ARGS)
end
