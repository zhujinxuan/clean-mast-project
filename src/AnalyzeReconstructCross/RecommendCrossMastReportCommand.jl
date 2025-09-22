"""
    RecommendCrossMastReportCommand.jl

Recommend command for cross-mast report generation.
Reads reconstruct-single.toml and generates analyze-reconstruct-cross.toml configuration for reporting.
"""
module RecommendCrossMastReportCommand

using TOML
using ...Types.ReconstructSingleConfig: ReconstructSingleConfiguration
using ...Types.AnalyzeReconstructCrossConfig: AnalyzeReconstructCrossConfiguration, AnalyzeReconstructCrossMast, AnalyzeReconstructCrossSettings
using ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict

export execute

"""
    execute(project_dir::String)

Generate report-cross-mast.toml configuration for cross-mast report generation.

# Arguments
- `project_dir::String`: Project directory containing reconstruct-single.toml

# Description
This command:
1. Reads reconstruct-single.toml to find all reconstructed mast data
2. Uses the output paths from reconstruct-single as input for cross-mast analysis
3. Creates report-cross-mast.toml with proper report-masts output directory
4. Saves configuration to report-masts/report-cross-mast.toml

# Example
```bash
julia bin/CleanMast.jl recommend cross-mast-report ./project
```

This will generate ./project/report-masts/report-cross-mast.toml
"""
function execute(project_dir::String)
    println("🔍 Generating cross-mast report configuration...")

    # Read reconstruct-single.toml
    reconstruct_single_path = joinpath(project_dir, "reconstruct-single.toml")
    if !isfile(reconstruct_single_path)
        error("reconstruct-single.toml not found. Please run 'recommend reconstruct-single' first.")
    end

    # Load reconstruct-single configuration
    config_dict = load_dict(reconstruct_single_path)
    reconstruct_config = from_dict(ReconstructSingleConfiguration, config_dict)

    # Create analyze masts configuration using reconstruct-single outputs as inputs
    analyze_masts = map(reconstruct_config.masts) do mast
        AnalyzeReconstructCrossMast(
            name = mast.name,
            input = mast.output  # Use output from reconstruct-single as input for analysis
        )
    end

    # Create settings with proper report output directory
    settings = AnalyzeReconstructCrossSettings(
        output_dir = "./report-masts/cross-mast",  # Report goes to report-masts
        include_plots = true,
        language = "zh"
    )

    # Create complete configuration
    config = AnalyzeReconstructCrossConfiguration(
        masts = analyze_masts,
        analyze = settings
    )

    # Create report-masts directory if it doesn't exist
    report_masts_dir = joinpath(project_dir, "report-masts")
    if !isdir(report_masts_dir)
        mkpath(report_masts_dir)
        println("📁 Created report-masts directory: $report_masts_dir")
    end

    # Save configuration to report-masts directory
    output_file = joinpath(report_masts_dir, "report-cross-mast.toml")
    open(output_file, "w") do io
        TOML.print(io, to_dict(config))
    end

    println("✓ Generated report-cross-mast.toml with $(length(analyze_masts)) masts")
    println("📁 Configuration saved to: $output_file")
    println("💡 This configuration will generate reports in: ./report-masts/cross-mast/")

    return config
end

end # module