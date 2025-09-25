module RecommendReportReconstructSingleCommand

using YAML
using ...Types.ReconstructSingleConfig: ReconstructSingleConfiguration
using ...Types.TowerShadingConfig: TowerShadingConfiguration
using ...Types.Utils: from_dict
using ...CleanMastUtils: load_dict

export execute

"""
    execute(project_dir::String)

Generate report-reconstruct-single.yaml configuration for analyzing reconstruction effectiveness.

# Arguments
- `project_dir::String`: Project directory containing reconstruction configurations

# Algorithm
1. Read tower-shading.toml to get initial processed data sources
2. Read reconstruct-single.toml to get reconstruction outputs (if available)
3. Create configuration comparing before/after reconstruction data
4. Save to report-masts/report-reconstruct-single.yaml
"""
function execute(project_dir::String)
    println("🔍 Generating report-reconstruct-single configuration...")

    # 1. Read tower-shading.toml (before reconstruction data)
    shading_config = load_shading_config(project_dir)

    # 2. Try to read reconstruct-single.toml (after reconstruction data)
    single_config = try_load_single_config(project_dir)

    # 3. Build report configuration for each mast
    report_masts = map(shading_config.masts) do shading_mast
        mast_name = shading_mast.name

        # Find corresponding reconstruction output (if available)
        single_mast = isnothing(single_config) ? nothing : find_mast_in_single_config(single_config, mast_name)

        if isnothing(single_mast)
            @warn "No reconstruct-single configuration found for mast: $mast_name. Using tower-shading output as both before and after."
            # Use tower-shading output as both before and after if no reconstruction exists
            before_data = shading_mast.output
            after_data = shading_mast.output
        else
            # Use tower-shading as before, reconstruct-single output as after
            before_data = shading_mast.output
            after_data = single_mast.output
        end

        Dict(
            "name" => mast_name,
            "before_reconstruction" => Dict(
                "csv" => before_data.data,
                "sensorConfig" => before_data.sensors
            ),
            "after_reconstruction" => Dict(
                "csv" => after_data.data,
                "sensorConfig" => after_data.sensors
            )
        )
    end

    # 4. Create final configuration
    config = Dict(
        "masts" => report_masts,
        "output" => Dict(
            "dir" => "./report-masts/reconstruct-single"
        )
    )

    # 5. Save configuration to report-masts directory
    report_masts_dir = joinpath(project_dir, "report-masts")
    if !isdir(report_masts_dir)
        mkpath(report_masts_dir)
        println("📁 Created report-masts directory: $report_masts_dir")
    end

    output_file = joinpath(report_masts_dir, "report-reconstruct-single.yaml")
    open(output_file, "w") do io
        YAML.write(io, config)
    end

    println("✓ Generated report-reconstruct-single.yaml with $(length(report_masts)) masts")
    println("📁 Configuration saved to: $output_file")
    println("📋 Use with: julia bin/CleanMast.jl report reconstruct-single $output_file")

    return config
end

"""
    load_shading_config(project_dir::String)::TowerShadingConfiguration

Load and parse tower-shading.toml configuration.
"""
function load_shading_config(project_dir::String)::TowerShadingConfiguration
    shading_path = joinpath(project_dir, "tower-shading.toml")
    if !isfile(shading_path)
        error("tower-shading.toml not found in $project_dir. Please run 'recommend tower-shading' first.")
    end

    config_dict = load_dict(shading_path)
    return from_dict(TowerShadingConfiguration, config_dict)
end

"""
    try_load_single_config(project_dir::String)::Union{ReconstructSingleConfiguration, Nothing}

Try to load and parse reconstruct-single.toml configuration. Returns nothing if file doesn't exist.
"""
function try_load_single_config(project_dir::String)::Union{ReconstructSingleConfiguration, Nothing}
    single_path = joinpath(project_dir, "reconstruct-single.toml")
    if !isfile(single_path)
        println("ℹ️  reconstruct-single.toml not found - will compare tower-shading data with itself")
        return nothing
    end

    config_dict = load_dict(single_path)
    return from_dict(ReconstructSingleConfiguration, config_dict)
end

"""
    find_mast_in_single_config(config::ReconstructSingleConfiguration, mast_name::String)

Find a mast configuration in the reconstruct-single config by name.
"""
function find_mast_in_single_config(config::ReconstructSingleConfiguration, mast_name::String)
    idx = findfirst(m -> m.name == mast_name, config.masts)
    return isnothing(idx) ? nothing : config.masts[idx]
end

end # module