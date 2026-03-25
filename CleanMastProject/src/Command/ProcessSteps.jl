module ProcessSteps

using ...DataClean.ProcessCleanCommand
using ...DataClean.RecommendProcessCleanCommand
using ...TowerShading.CommandTowerShading
using ...TowerShading.RecommendTowerShadingCommand
using ...ReconstructSingleMast.CommandReconstructSingle
using ...ReconstructSingleMast.RecommendReconstructSingleCommand
using ...TrainReconstructCross.RecommendTrainReconstructCrossCommand
using ...TrainReconstructCross.TrainReconstructCrossCommand
using ...ReconstructCross.RecommendReconstructCrossCommand
using ...ReconstructCross.ProcessReconstructCrossCommand
using ...TrainMeso.CommandTrainMeso
using ...TrainMeso.RecommendTrainMesoCommand
using ...ReconstructMeso.CommandReconstructMeso
using ...ReconstructMeso.RecommendReconstructMesoCommand
using ...RepresentativeYear.CommandRepresentativeYear
using ...RepresentativeYear.RecommendRepresentativeYearCommand
using ...Types.ParseSensorsConfig: ParseSensorsConfiguration, from_dict
using ...Types.ReconstructSingleConfig: ReconstructSingleConfiguration
using ...CleanMastUtils: load_dict

export execute, list_steps

"""
    is_single_mast_project(dir::String)::Bool

Check if this is a single mast project by examining parse-sensors.toml or reconstruct-single.toml.
Returns true if there is only one mast configured, false otherwise.
"""
function is_single_mast_project(dir::String)::Bool
    parse_sensors_path = joinpath(dir, "parse-sensors.toml")
    reconstruct_single_path = joinpath(dir, "reconstruct-single.toml")

    # Check parse-sensors.toml to determine project type
    if isfile(parse_sensors_path)
        config_dict = load_dict(parse_sensors_path)
        config = from_dict(ParseSensorsConfiguration, config_dict)
        # Single mast project if there's exactly one mast and no mesos
        return length(config.masts) == 1 && length(config.mesos) == 0
    else
        error("parse-sensors.toml not found. Run `recommend parse-sensors` first to generate it.")
    end
end

"""
    ProcessingStep

Represents a single step in the data processing pipeline.

# Fields
- `number::Int`: Step number (1-based)
- `name::String`: Short name for the step
- `description::String`: Detailed description of what this step does
- `execute_func::Function`: Function to execute this step
- `config_file::Union{String, Nothing}`: Configuration file path (relative to project dir)
- `output_check::Union{String, Nothing}`: Path to check if step is already completed
- `conditional::Bool`: Whether this step is conditional (may be skipped)
"""
struct ProcessingStep
    number::Int
    name::String
    description::String
    execute_func::Function
    config_file::Union{String, Nothing}
    output_check::Union{String, Nothing}
    conditional::Bool
end

"""
    get_all_steps()::Vector{ProcessingStep}

Returns the complete list of processing steps in order.
"""
function get_all_steps()::Vector{ProcessingStep}
    return [
        ProcessingStep(
            1,
            "recommend-clean",
            "Recommend clean data configuration",
            dir -> RecommendProcessCleanCommand.execute(dir),
            "process-clean.toml",
            "process-clean.toml",
            false
        ),
        ProcessingStep(
            2,
            "clean",
            "Clean data using configured rules",
            dir -> ProcessCleanCommand.execute(joinpath(dir, "process-clean.toml")),
            "process-clean.toml",
            "clean",
            false
        ),
        ProcessingStep(
            3,
            "recommend-tower-shading",
            "Recommend tower shading configuration",
            dir -> RecommendTowerShadingCommand.execute(dir),
            "tower-shading.toml",
            "tower-shading.toml",
            false
        ),
        ProcessingStep(
            4,
            "tower-shading",
            "Process tower shading corrections",
            dir -> CommandTowerShading.execute(joinpath(dir, "tower-shading.toml")),
            "tower-shading.toml",
            "tower-shading",
            false
        ),
        ProcessingStep(
            5,
            "recommend-reconstruct-single",
            "Recommend single mast reconstruction configuration",
            dir -> RecommendReconstructSingleCommand.execute(dir),
            "reconstruct-single.toml",
            "reconstruct-single.toml",
            false
        ),
        ProcessingStep(
            6,
            "reconstruct-single",
            "Reconstruct single mast data",
            dir -> CommandReconstructSingle.execute(joinpath(dir, "reconstruct-single.toml")),
            "reconstruct-single.toml",
            "reconstruct-single",
            false
        ),
        ProcessingStep(
            7,
            "recommend-train-cross",
            "Recommend cross-mast training configuration (skip if single mast)",
            dir -> RecommendTrainReconstructCrossCommand.execute(dir),
            "train-reconstruct-cross.toml",
            "train-reconstruct-cross.toml",
            false
        ),
        ProcessingStep(
            8,
            "train-cross",
            "Train cross-mast reconstruction models (skip if single mast)",
            dir -> TrainReconstructCrossCommand.execute(joinpath(dir, "train-reconstruct-cross.toml")),
            "train-reconstruct-cross.toml",
            "train-reconstruct-cross",
            false
        ),
        ProcessingStep(
            9,
            "recommend-reconstruct-cross",
            "Recommend cross-mast reconstruction configuration (skip if single mast)",
            dir -> RecommendReconstructCrossCommand.execute(joinpath(dir, "train-reconstruct-cross", "train-results.toml"), dir),
            nothing,
            "reconstruct-cross.toml",
            false
        ),
        ProcessingStep(
            10,
            "reconstruct-cross",
            "Reconstruct cross-mast data (skip if single mast)",
            dir -> ProcessReconstructCrossCommand.execute(joinpath(dir, "reconstruct-cross.toml")),
            "reconstruct-cross.toml",
            "reconstruct-cross",
            true
        ),
        ProcessingStep(
            11,
            "recommend-train-meso",
            "Recommend mesoscale training configuration",
            dir -> RecommendTrainMesoCommand.execute(dir),
            "train-meso.toml",
            "train-meso.toml",
            false
        ),
        ProcessingStep(
            12,
            "train-meso",
            "Train mesoscale reconstruction models",
            dir -> CommandTrainMeso.execute(joinpath(dir, "train-meso.toml")),
            "train-meso.toml",
            "meso-models",
            false
        ),
        ProcessingStep(
            13,
            "recommend-reconstruct-meso",
            "Recommend mesoscale reconstruction configuration",
            dir -> RecommendReconstructMesoCommand.execute(dir),
            "reconstruct-meso.toml",
            "reconstruct-meso.toml",
            false
        ),
        ProcessingStep(
            14,
            "reconstruct-meso",
            "Reconstruct with mesoscale data",
            dir -> CommandReconstructMeso.execute(joinpath(dir, "reconstruct-meso.toml")),
            "reconstruct-meso.toml",
            "reconstruct-meso",
            false
        ),
        ProcessingStep(
            15,
            "recommend-representative-year",
            "Recommend representative year configuration",
            dir -> RecommendRepresentativeYearCommand.execute(dir),
            "representative-year.toml",
            "representative-year.toml",
            false
        ),
        ProcessingStep(
            16,
            "representative-year",
            "Calibrate to representative year",
            dir -> CommandRepresentativeYear.execute(joinpath(dir, "representative-year.toml")),
            "representative-year.toml",
            "representative-year",
            false
        )
    ]
end

"""
    list_steps()

Print all available processing steps with their numbers and descriptions.
"""
function list_steps()
    steps = get_all_steps()

    println("Available Processing Steps:")
    println("=" ^ 50)

    for step in steps
        conditional_marker = step.conditional ? " [conditional]" : ""
        println("$(lpad(step.number, 2)). $(step.name)$conditional_marker")
        println("    $(step.description)")
        if step.config_file !== nothing
            println("    Config: $(step.config_file)")
        end
        println()
    end

    println("Usage:")
    println("  process steps --all                    # Run all steps")
    println("  process steps --from 5 --to 12        # Run steps 5-12")
    println("  process steps --from 10               # Run from step 10 to end")
    println("  process steps --to 8                  # Run steps 1-8")
    println("  process steps --list                  # Show this list")
end

"""
    validate_step_range(from_step::Union{Int, Nothing}, to_step::Union{Int, Nothing})::Tuple{Int, Int}

Validate and normalize the step range parameters.
Returns a tuple of (start_step, end_step).
"""
function validate_step_range(from_step::Union{Int, Nothing}, to_step::Union{Int, Nothing})::Tuple{Int, Int}
    steps = get_all_steps()
    max_step = length(steps)

    start_step = from_step === nothing ? 1 : from_step
    end_step = to_step === nothing ? max_step : to_step

    if start_step < 1 || start_step > max_step
        error("Invalid --from value: $start_step. Must be between 1 and $max_step.")
    end

    if end_step < 1 || end_step > max_step
        error("Invalid --to value: $end_step. Must be between 1 and $max_step.")
    end

    if start_step > end_step
        error("Invalid range: --from $start_step --to $end_step. Start step must be <= end step.")
    end

    return (start_step, end_step)
end

"""
    is_step_completed(step::ProcessingStep, dir::String)::Bool

Check if a step has already been completed by looking for its output.
"""
function is_step_completed(step::ProcessingStep, dir::String)::Bool
    if step.output_check === nothing
        return false
    end

    output_path = joinpath(dir, step.output_check)
    return isfile(output_path) || isdir(output_path)
end

"""
    execute_step(step::ProcessingStep, dir::String)

Execute a single processing step with error handling and progress reporting.
"""
function execute_step(step::ProcessingStep, dir::String)
    println("\n$(step.number). $(step.description)...")

    # Check if this is a cross-mast step and we have a single mast project
    cross_mast_steps = [7, 8, 9, 10]  # recommend-train-cross, train-cross, recommend-reconstruct-cross, reconstruct-cross
    if step.number in cross_mast_steps && is_single_mast_project(dir)
        println("   ⏭️  Skipping cross-mast step (single mast project detected)")
        return
    end

    # Check if step is conditional and should be skipped
    if step.conditional && step.config_file !== nothing
        config_path = joinpath(dir, step.config_file)
        if !isfile(config_path)
            println("   ⏭️  Skipping conditional step (config not found: $(step.config_file))")
            return
        end
    end

    try
        step.execute_func(dir)
        println("   ✅ Step $(step.number) completed successfully")
    catch e
        println("   ❌ Step $(step.number) failed: $e")
        rethrow(e)
    end
end

"""
    execute(dir::String; all::Bool = false, from_step::Union{Int, Nothing} = nothing,
            to_step::Union{Int, Nothing} = nothing, list_only::Bool = false)

Execute processing steps based on the specified parameters.

# Arguments
- `dir::String`: Project directory containing configurations
- `all::Bool`: Execute all steps (equivalent to --from 1 --to 16)
- `from_step::Union{Int, Nothing}`: Starting step number
- `to_step::Union{Int, Nothing}`: Ending step number
- `list_only::Bool`: Only list available steps without executing

# Examples
```julia
ProcessSteps.execute("./project", all=true)                    # Run all steps
ProcessSteps.execute("./project", from_step=5, to_step=12)     # Run steps 5-12
ProcessSteps.execute("./project", from_step=10)               # Run from step 10 to end
ProcessSteps.execute("./project", list_only=true)             # List all steps
```
"""
function execute(dir::String; all::Bool = false, from_step::Union{Int, Nothing} = nothing,
                to_step::Union{Int, Nothing} = nothing, list_only::Bool = false)

    if list_only
        list_steps()
        return
    end

    if isempty(dir)
        error("Project directory is required when not using --list option")
    end

    # Handle --all option
    if all
        from_step = 1
        to_step = nothing
    end

    # Validate and normalize step range
    (start_step, end_step) = validate_step_range(from_step, to_step)

    steps = get_all_steps()
    selected_steps = steps[start_step:end_step]

    println("Processing steps $start_step-$end_step for project: $dir")
    println("Total steps to execute: $(length(selected_steps))")

    completed_steps = 0

    for step in selected_steps
        try
            execute_step(step, dir)
            completed_steps += 1
        catch e
            println("\n❌ Processing stopped at step $(step.number) due to error:")
            println("   $e")
            println("\nCompleted: $completed_steps/$(length(selected_steps)) steps")
            println("To resume, use: process steps --from $(step.number)")
            rethrow(e)
        end
    end

    println("\n🎉 Processing completed successfully!")
    println("Executed steps $start_step-$end_step ($completed_steps steps total)")
end


end # module