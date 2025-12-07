"""
    RecommendReportReconstructMesoCommand.jl

Command to generate report-reconstruct-meso.toml configuration file
based on reconstruct-meso.toml configuration.
"""
module RecommendReportReconstructMesoCommand

using TOML

using ...Types.ReconstructMesoConfig: ReconstructMesoConfiguration, from_dict
using ...Types.ReportReconstructMesoConfig: ReportReconstructMesoConfiguration, ReportReconstructMesoMast, ReportReconstructMesoMeso, ReportReconstructMesoAnalysisSettings, to_dict
using ...Types.MastTimeSeries: load_timeseries, TimeSeriesSource
using ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict

export execute

"""
    adjust_path_for_report_masts(path::String)::String

Adjust a project-relative path to be relative to report-masts/ directory.
Converts "./some/path" to "../some/path" for use in configs saved in report-masts/.
"""
function adjust_path_for_report_masts(path::String)::String
    if startswith(path, "./")
        return "../" * path[3:end]
    else
        return "../" * path
    end
end

"""
    adjust_timeseries_source(source::TimeSeriesSource)::TimeSeriesSource

Adjust paths in a TimeSeriesSource to be relative to report-masts/ directory.
"""
function adjust_timeseries_source(source::TimeSeriesSource)::TimeSeriesSource
    return TimeSeriesSource(
        adjust_path_for_report_masts(source.data),
        adjust_path_for_report_masts(source.sensors)
    )
end

"""
    execute(project_dir::String)

Generate report-reconstruct-meso.toml configuration file.

# Arguments
- `project_dir::String`: Project directory containing reconstruct-meso.toml

# Description
This command reads reconstruct-meso.toml and generates a configuration for
meso-mast reconstruction quality reporting. The configuration will be saved as:
`report-masts/report-reconstruct-meso.toml`

# Example
```bash
julia bin/CleanMast.jl recommend report-reconstruct-meso ./projects/my-project
```
"""
function execute(project_dir::String)
    println("🔍 Generating Report Reconstruct Meso Configuration")
    println("=" ^ 50)

    if !isdir(project_dir)
        error("Project directory not found: $project_dir")
    end

    reconstruct_meso_path = joinpath(project_dir, "reconstruct-meso.toml")
    if !isfile(reconstruct_meso_path)
        error("reconstruct-meso.toml not found at: $reconstruct_meso_path")
    end

    println("📋 Loading reconstruct-meso.toml...")
    config_dict = load_dict(reconstruct_meso_path)
    reconstruct_config = from_dict(ReconstructMesoConfiguration, config_dict)

    println("  ✓ Found $(length(reconstruct_config.masts)) masts")
    println("  ✓ Found $(length(reconstruct_config.mesos)) mesos")

    println("\n🔍 Detecting wind speed sensor heights...")

    report_masts = ReportReconstructMesoMast[]
    for mast in reconstruct_config.masts
        println("  📊 Analyzing mast: $(mast.name)")
        mast_ts = load_timeseries(mast.input, project_dir)

        ws_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", mast_ts.sensors)
        if isempty(ws_sensors)
            error("No wind speed sensors (statType=avg) found for mast $(mast.name)")
        end

        sorted = sort(ws_sensors, by = s -> s.height, rev = true)
        top_3_heights = [s.height for s in sorted[1:min(3, length(sorted))]]
        println("    ✓ Selected heights: $(top_3_heights)")

        push!(report_masts, ReportReconstructMesoMast(
            mast.name,
            adjust_timeseries_source(mast.input),
            top_3_heights
        ))
    end

    report_mesos = ReportReconstructMesoMeso[]
    for meso in reconstruct_config.mesos
        println("  🌍 Analyzing meso: $(meso.name)")
        meso_ts = load_timeseries(meso.input, project_dir)

        ws_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", meso_ts.sensors)
        if isempty(ws_sensors)
            error("No wind speed sensors (statType=avg) found for meso $(meso.name)")
        end

        highest_height = maximum(s.height for s in ws_sensors)
        println("    ✓ Selected height: $(highest_height)")

        push!(report_mesos, ReportReconstructMesoMeso(
            meso.name,
            adjust_timeseries_source(meso.input),
            [highest_height]
        ))
    end

    analyze_settings = ReportReconstructMesoAnalysisSettings("./reconstruct-meso")

    report_config = ReportReconstructMesoConfiguration(
        report_masts,
        report_mesos,
        analyze_settings
    )

    report_masts_dir = joinpath(project_dir, "report-masts")
    if !isdir(report_masts_dir)
        mkpath(report_masts_dir)
        println("📁 Created report-masts directory")
    end

    output_path = joinpath(report_masts_dir, "report-reconstruct-meso.toml")
    open(output_path, "w") do io
        println(io, "# Meso-Mast Reconstruction Quality Analysis Configuration")
        println(io, "# Analyzes RMSE and correlation between mesoscale and mast data")
        println(io)
        TOML.print(io, to_dict(report_config))
    end

    println("\n✅ Configuration generated successfully!")
    println("  📄 Output: $(output_path)")
    println("\n💡 Next steps:")
    println("  1. Review the generated configuration file")
    println("  2. Run: julia bin/CleanMast.jl report reconstruct-meso $(output_path)")
end

end # module
