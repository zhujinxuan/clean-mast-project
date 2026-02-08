"""
    RecommendAnalyzeReconstructCrossCommand.jl

Recommend command for analyze-reconstruct-cross.
Reads reconstruct-single.toml and generates analyze-reconstruct-cross.toml configuration.
"""
module RecommendAnalyzeReconstructCrossCommand

using TOML
using ...Types.ReconstructSingleConfig: ReconstructSingleConfiguration
using ...Types.ReportReconstructCrossConfig: ReportReconstructCrossConfiguration, ReportReconstructCrossMast, ReportReconstructCrossSettings
using ...Types.Utils: from_dict, to_dict, strip_nothing_values
using ...CleanMastUtils: load_dict

export execute

"""
    execute(dir::String)

Generate analyze-reconstruct-cross.toml configuration from reconstruct-single.toml.

# Arguments
- `dir::String`: Project directory containing reconstruct-single.toml

# Description
This command:
1. Reads reconstruct-single.toml to find all reconstructed mast data
2. Uses the output paths from reconstruct-single as input for cross-mast analysis
3. Creates analyze-reconstruct-cross.toml with all masts and default settings

# Example
```bash
julia bin/CleanMast.jl recommend analyze-reconstruct-cross ./project
```

This will generate ./project/analyze-reconstruct-cross.toml
"""
function execute(dir::String)
    println("🔍 Scanning for reconstructed mast data...")
    
    # Read reconstruct-single.toml
    reconstruct_single_path = joinpath(dir, "reconstruct-single.toml")
    if !isfile(reconstruct_single_path)
        error("reconstruct-single.toml not found. Please run 'recommend reconstruct-single' first.")
    end
    
    # Load reconstruct-single configuration
    config_dict = load_dict(reconstruct_single_path)
    reconstruct_config = from_dict(ReconstructSingleConfiguration, config_dict)
    
    println("📋 Found $(length(reconstruct_config.masts)) reconstructed masts")
    
    # Create analyze-reconstruct-cross configuration
    analyze_config = create_analyze_config(reconstruct_config)
    
    # Save configuration file
    output_path = joinpath(dir, "analyze-reconstruct-cross.toml")
    config_dict = to_dict(analyze_config)
    
    open(output_path, "w") do io
        TOML.print(io, strip_nothing_values(Dict{String, Any}(config_dict)))
    end
    
    println("✅ Generated analyze-reconstruct-cross.toml at: $output_path")
    println("📊 Configuration includes:")
    for mast in analyze_config.masts
        println("  - $(mast.name): $(mast.input.data)")
    end
    println("🎯 Output directory: $(analyze_config.analyze.output_dir)")
    println("📝 Report language: $(analyze_config.analyze.language) (Chinese)")
end

"""
    create_analyze_config(reconstruct_config)

Create analyze-reconstruct-cross configuration from reconstruct-single configuration.
"""
function create_analyze_config(reconstruct_config::ReconstructSingleConfiguration)::ReportReconstructCrossConfiguration
    # Convert each mast's output to input for analysis
    # Update file extension from .csv to .parquet
    masts = map(reconstruct_config.masts) do mast
        output_path = mast.output
        input_path = replace(output_path, r"\.csv$" => ".parquet")
        ReportReconstructCrossMast(
            name = mast.name,
            input = input_path  # Output from reconstruct-single becomes input for analysis
        )
    end
    
    # Create settings with Chinese defaults
    settings = ReportReconstructCrossSettings(
        output_dir = "./analyze-reconstruct-cross",
        include_plots = true,
        language = "zh"
    )
    
    return ReportReconstructCrossConfiguration(masts, settings)
end

end # module 