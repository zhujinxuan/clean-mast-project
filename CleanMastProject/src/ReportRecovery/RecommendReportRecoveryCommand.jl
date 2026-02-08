module RecommendReportRecoveryCommand

using TOML
using ...Types.MastTimeSeries: TimeSeriesSource, adjust_timeseries_source_paths_to_parquet
using ...Types.ReconstructMesoConfig: ReconstructMesoConfiguration, from_dict
using ...Types.ReconstructCrossConfig: ReconstructCrossConfiguration
using ...Types.ReconstructSingleConfig: ReconstructSingleConfiguration
using ...Types.TowerShadingConfig: TowerShadingConfiguration
using ...Types.ReportRecoveryConfig: ReportRecoveryConfiguration, ReportRecoveryMast, ReportRecoveryOutput, to_dict
using ...Types.Utils: from_dict, strip_nothing_values
using ...CleanMastUtils: load_dict

export execute

"""
    adjust_timeseries_source(source::TimeSeriesSource)::TimeSeriesSource

Adjust paths in a TimeSeriesSource to be relative to report-masts/ directory
and convert to Parquet format.
"""
function adjust_timeseries_source(source::TimeSeriesSource)::TimeSeriesSource
    return adjust_timeseries_source_paths_to_parquet(source, "../")
end

"""
    execute(project_dir::String)

Generate report-recovery.toml configuration by tracing data sources through the reconstruction pipeline.

# Arguments
- `project_dir::String`: Project directory containing reconstruct-meso.toml

# Algorithm
1. Read reconstruct-meso.toml to get final mast configurations and time ranges
2. Trace back through reconstruct-cross.toml to find cross-reconstruction inputs
3. Trace back through reconstruct-single.toml to find single-reconstruction inputs  
4. Trace back through tower-shading.toml to find initial processed data
5. Create complete configuration with all data sources for each mast
"""
function execute(project_dir::String)
    println("🔍 Generating report-recovery configuration...")
    
    # 1. Read reconstruct-meso.toml (final stage)
    meso_config = load_meso_config(project_dir)
    
    # 2. Read reconstruct-cross.toml to trace cross-reconstruction inputs (optional)
    cross_config = try_load_cross_config(project_dir)

    # 3. Read reconstruct-single.toml to trace single-reconstruction inputs (optional)
    single_config = try_load_single_config(project_dir)

    # 4. Read tower-shading.toml to trace initial processed data
    shading_config = load_shading_config(project_dir)
    
    # 5. Build recovery configuration for each mast
    recovery_masts = map(meso_config.masts) do meso_mast
        mast_name = meso_mast.name

        # Find corresponding configurations in each stage (some may be optional)
        cross_mast = isnothing(cross_config) ? nothing : find_mast_in_cross_config(cross_config, mast_name)
        single_mast = isnothing(single_config) ? nothing : find_mast_in_single_config(single_config, mast_name)
        shading_mast = find_mast_in_shading_config(shading_config, mast_name)

        if isnothing(shading_mast)
            @warn "Could not find tower-shading configuration for mast: $mast_name"
            return nothing
        end

        # Use fallback data sources if stages are missing, and adjust paths for report-masts/ directory
        tower_shading_source = adjust_timeseries_source(shading_mast.output)
        single_source = adjust_timeseries_source(isnothing(single_mast) ? shading_mast.output : single_mast.output)
        cross_source = isnothing(cross_mast) ? nothing : adjust_timeseries_source(cross_mast.output)

        ReportRecoveryMast(
            name = mast_name,
            tower_shading = tower_shading_source,
            reconstruct_single = single_source,
            reconstruct_cross = cross_source,
            reconstruct_meso = adjust_timeseries_source(meso_mast.output),
            time_range = meso_mast.time_range
        )
    end
    
    # Filter out any failed masts
    valid_masts = filter(x -> !isnothing(x), recovery_masts)
    
    if isempty(valid_masts)
        error("No valid masts found. Please ensure all pipeline configurations exist.")
    end
    
    # Create final configuration with paths relative to report-masts/ directory
    config = ReportRecoveryConfiguration(
        masts = valid_masts,
        output = ReportRecoveryOutput(report_dir = "./recovery")
    )
    
    # Save configuration to report-masts directory
    report_masts_dir = joinpath(project_dir, "report-masts")
    if !isdir(report_masts_dir)
        mkpath(report_masts_dir)
        println("📁 Created report-masts directory: $report_masts_dir")
    end

    output_file = joinpath(report_masts_dir, "report-recovery.toml")
    open(output_file, "w") do io
        TOML.print(io, strip_nothing_values(Dict{String, Any}(to_dict(config))))
    end
    
    println("✓ Generated report-recovery.toml with $(length(valid_masts)) masts")
    println("📁 Configuration saved to: $output_file")
    
    return config
end

"""
    load_meso_config(project_dir::String)::ReconstructMesoConfiguration

Load and parse reconstruct-meso.toml configuration.
"""
function load_meso_config(project_dir::String)::ReconstructMesoConfiguration
    meso_path = joinpath(project_dir, "reconstruct-meso.toml")
    if !isfile(meso_path)
        error("reconstruct-meso.toml not found in $project_dir")
    end
    
    config_dict = load_dict(meso_path)
    return from_dict(ReconstructMesoConfiguration, config_dict)
end

"""
    try_load_cross_config(project_dir::String)::Union{ReconstructCrossConfiguration, Nothing}

Try to load and parse reconstruct-cross.toml configuration. Returns nothing if file doesn't exist.
"""
function try_load_cross_config(project_dir::String)::Union{ReconstructCrossConfiguration, Nothing}
    cross_path = joinpath(project_dir, "reconstruct-cross.toml")
    if !isfile(cross_path)
        println("ℹ️  reconstruct-cross.toml not found - cross-mast reconstruction will be skipped in analysis")
        return nothing
    end

    config_dict = load_dict(cross_path)
    return from_dict(ReconstructCrossConfiguration, config_dict)
end

"""
    try_load_single_config(project_dir::String)::Union{ReconstructSingleConfiguration, Nothing}

Try to load and parse reconstruct-single.toml configuration. Returns nothing if file doesn't exist.
"""
function try_load_single_config(project_dir::String)::Union{ReconstructSingleConfiguration, Nothing}
    single_path = joinpath(project_dir, "reconstruct-single.toml")
    if !isfile(single_path)
        println("ℹ️  reconstruct-single.toml not found - single-mast reconstruction will be skipped in analysis")
        return nothing
    end

    config_dict = load_dict(single_path)
    return from_dict(ReconstructSingleConfiguration, config_dict)
end

"""
    load_shading_config(project_dir::String)::TowerShadingConfiguration

Load and parse tower-shading.toml configuration.
"""
function load_shading_config(project_dir::String)::TowerShadingConfiguration
    shading_path = joinpath(project_dir, "tower-shading.toml")
    if !isfile(shading_path)
        error("tower-shading.toml not found in $project_dir")
    end
    
    config_dict = load_dict(shading_path)
    return from_dict(TowerShadingConfiguration, config_dict)
end

# Helper functions to find masts in different configurations
function find_mast_in_cross_config(config::Union{ReconstructCrossConfiguration, Nothing}, mast_name::String)
    isnothing(config) && return nothing
    idx = findfirst(m -> m.name == mast_name, config.masts)
    return isnothing(idx) ? nothing : config.masts[idx]
end

function find_mast_in_single_config(config::Union{ReconstructSingleConfiguration, Nothing}, mast_name::String)
    isnothing(config) && return nothing
    idx = findfirst(m -> m.name == mast_name, config.masts)
    return isnothing(idx) ? nothing : config.masts[idx]
end

function find_mast_in_shading_config(config::TowerShadingConfiguration, mast_name::String)
    idx = findfirst(m -> m.name == mast_name, config.masts)
    return isnothing(idx) ? nothing : config.masts[idx]
end

end # module
