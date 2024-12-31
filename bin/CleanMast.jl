#!/usr/bin/env julia

# Activate the project environment relative to this script's location
using Pkg
project_path = abspath(joinpath(@__DIR__, ".."))
Pkg.activate(project_path)
using ArgParse
using CleanMastProject.Command.CheckConfig
using CleanMastProject.Command.CheckSensors
using CleanMastProject.Command.CleanData
using CleanMastProject.Command.TowerShading
using CleanMastProject.Command.ReconstructSingleMast
using CleanMastProject.Command.QuickStart
using CleanMastProject.Command.CleanFiles
using CleanMastProject.Command.ReconstructMeso

const COMMAND_HANDLERS = Dict(
    "check:config" => CheckConfig.execute,
    "check:sensors" => CheckSensors.execute,
    "clean:data" => CleanData.execute,
    "clean:files" => CleanFiles.execute,
    "tower:shading" => TowerShading.execute,
    "reconstruct:single_mast" => ReconstructSingleMast.execute,
    "reconstruct:meso" => ReconstructMeso.execute,
    "quickstart" => QuickStart.execute,
)

function main()
    args = Base.ARGS
    command, dir = parse_arguments(args)
    
    handler = get(COMMAND_HANDLERS, command) do
        error("无效的命令: $command")
    end
    
    handler(dir)
end

function parse_arguments(args::Vector{String})
    s = ArgParseSettings()
    @add_arg_table! s begin
        "command"
        help = "要执行的命令，如 check:config, check:sensors"
        arg_type = String
        required = true

        "--dir"
        help = "指定配置文件所在的目录"
        arg_type = String
        required = true
    end
    parsed_args = parse_args(args, s)
    command = parsed_args["command"]
    return command, get(parsed_args, "dir", "")
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
