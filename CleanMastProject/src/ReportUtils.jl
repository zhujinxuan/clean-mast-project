"""
    ReportUtils.jl

Shared utilities for report generation commands.
Provides common functions for path adjustment, configuration handling, etc.
"""
module ReportUtils

using ..Types.MastTimeSeries: TimeSeriesSource

export adjust_path_for_report_masts, adjust_timeseries_source_for_report_masts

"""
    adjust_path_for_report_masts(path::Union{String, Nothing})::Union{String, Nothing}

Adjust a project-relative path to be relative to report-masts/ directory.
Converts "./some/path" to "../some/path" for use in configs saved in report-masts/.
Returns nothing if input is nothing (for Parquet files with embedded metadata).

# Examples
```julia
adjust_path_for_report_masts("./clean/data.parquet")  # Returns "../clean/data.parquet"
adjust_path_for_report_masts(nothing)                  # Returns nothing
```
"""
function adjust_path_for_report_masts(path::Union{String, Nothing})::Union{String, Nothing}
    isnothing(path) && return nothing
    if startswith(path, "./")
        return "../" * path[3:end]
    else
        return "../" * path
    end
end

"""
    adjust_timeseries_source_for_report_masts(source::TimeSeriesSource)::TimeSeriesSource

Adjust paths in a TimeSeriesSource to be relative to report-masts/ directory.

# Arguments
- `source::TimeSeriesSource`: The source with paths to adjust

# Returns
- `TimeSeriesSource`: New source with adjusted paths
"""
function adjust_timeseries_source_for_report_masts(source::TimeSeriesSource)::TimeSeriesSource
    return TimeSeriesSource(
        adjust_path_for_report_masts(source.data),
        adjust_path_for_report_masts(source.sensors)
    )
end

end # module
