"""
    RecommendTrainReconstructCrossCommand.jl

Command to generate train-reconstruct-cross.toml configuration files.
Discovers mast data files and suggests appropriate training configurations.
"""
module RecommendTrainReconstructCrossCommand

using Dates
using TOML
using ...Types.ReconstructSingleConfig: ReconstructSingleConfiguration
using ...Types.TrainReconstructCrossConfig: TrainReconstructCrossConfiguration, TrainCrossMast, TrainCrossSettings
using ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict

export execute

"""
    execute(project_dir::String)

Generate train-reconstruct-cross.toml configuration file based on reconstruct-single.toml output.

# Arguments
- `project_dir::String`: Project directory containing reconstruct-single.toml

# Workflow
1. Read reconstruct-single.toml to get reconstructed mast data paths
2. Generate cross-mast training configuration using those outputs
3. Save configuration to TOML file
"""
function execute(project_dir::String)
    println("🔍 Reading reconstruct-single configuration...")
    
    # 1. Read reconstruct-single.toml
    reconstruct_config = find_reconstructed_single_config(project_dir)
    
    # 2. Generate configuration
    config = create_train_config(reconstruct_config)
    
    # 3. Save configuration file
    output_file = joinpath(project_dir, "train-reconstruct-cross.toml")
    open(output_file, "w") do io
        TOML.print(io, to_dict(config))
    end
    
    println("💾 Saved configuration to: $output_file")
    println("📝 Generated with training parameters:")
    println("   - min_overlap_days: 90.0")
    println("   - min_data_points: 200")
    println("   - min_correlation: 0.7")
    println("   - max_std_deviation: 12.5")
    println("   - max_abs_offset: 45.0")
    println("✅ Run: julia bin/CleanMast.jl train reconstruct-cross $output_file")
end

"""
    discover_reconstructed_masts(project_dir)

Discover reconstructed mast data by reading reconstruct-single.toml configuration.
Uses the output paths from reconstruct-single as input for cross-mast training.
"""
function find_reconstructed_single_config(project_dir::String)::ReconstructSingleConfiguration
    # Read reconstruct-single.toml
    reconstruct_single_path = joinpath(project_dir, "reconstruct-single.toml")
    if !isfile(reconstruct_single_path)
        @error "reconstruct-single.toml not found. Please run 'recommend reconstruct-single' first."
        return Vector{Dict{String, String}}()
    end
    
    # Load reconstruct-single configuration
    config_dict = load_dict(reconstruct_single_path)
    return from_dict(ReconstructSingleConfiguration, config_dict)
end

"""
    create_train_config(reconstruct_config, project_dir)

Create train-reconstruct-cross configuration dictionary.
"""
function create_train_config(reconstruct_config::ReconstructSingleConfiguration)::TrainReconstructCrossConfiguration
    masts = map(m -> TrainCrossMast(m.name, m.output), reconstruct_config.masts)
    return TrainReconstructCrossConfiguration(
        masts,
        TrainCrossSettings(
            output_dir="./train-reconstruct-cross",
            min_overlap_days = 90.0,
            min_data_points = 200,
            min_correlation = 0.7,
            max_std_deviation = 12.5,
            max_abs_offset = 45.0,
            exclude_nan_results = true
        )
    )
end

end # module 