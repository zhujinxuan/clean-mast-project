module ReportFrozenPeriodData

using Parameters
using Dates
using ..SensorColumns: SensorColumn
using ..ReportFrozenPeriodConfig: FrozenDetectionSettings

export FrozenPeriod, SensorFrozenInfo, MastFrozenData, FrozenReportData,
       calculate_frozen_duration_days, calculate_missing_duration_days

"""
    FrozenPeriod

Represents one detected frozen period for a sensor.

# Fields
- `start_time::DateTime`: Start time of frozen period
- `end_time::DateTime`: End time of frozen period
- `duration_points::Int`: Number of data points in this period
- `threshold_name::String`: Which threshold set detected this period
"""
@with_kw struct FrozenPeriod
    start_time::DateTime
    end_time::DateTime
    duration_points::Int
    threshold_name::String
end

"""
    SensorFrozenInfo

Frozen period statistics for one wind speed sensor.
Stores frozen periods grouped by threshold set name.

# Fields
- `sensor::SensorColumn`: Wind speed sensor
- `sensor_name::String`: Display name (e.g., "WS:80m:SE")
- `temperature_sensor::Union{SensorColumn, Nothing}`: Associated temperature sensor
- `direction_sensor::Union{SensorColumn, Nothing}`: Associated wind direction sensor
- `rh_sensor_available::Bool`: Whether RH sensor was found
- `frozen_periods_by_threshold::Dict{String, Vector{FrozenPeriod}}`: Frozen periods grouped by threshold name (key = "加热型", "非加热型")
- `total_missing_points::Int`: Missing data points in raw data
- `total_points::Int`: Total data points in analysis period
"""
@with_kw struct SensorFrozenInfo
    sensor::SensorColumn
    sensor_name::String
    temperature_sensor::Union{SensorColumn, Nothing}
    direction_sensor::Union{SensorColumn, Nothing}
    rh_sensor_available::Bool
    frozen_periods_by_threshold::Dict{String, Vector{FrozenPeriod}}
    total_missing_points::Int
    total_points::Int
end

"""
    MastFrozenData

Complete frozen period data for one mast.

# Fields
- `name::String`: Mast name
- `sensor_frozen_info::Vector{SensorFrozenInfo}`: Frozen info for all wind sensors
- `analysis_start::DateTime`: Analysis period start
- `analysis_end::DateTime`: Analysis period end
- `interval_minutes::Int`: Data interval (e.g., 10 minutes)
"""
@with_kw struct MastFrozenData
    name::String
    sensor_frozen_info::Vector{SensorFrozenInfo}
    analysis_start::DateTime
    analysis_end::DateTime
    interval_minutes::Int
end

"""
    FrozenReportData

Complete data for frozen period report generation.

# Fields
- `masts::Vector{MastFrozenData}`: Masts analyzed
- `detection_settings::FrozenDetectionSettings`: Detection criteria used (multiple thresholds)
- `generation_time::DateTime`: Report generation timestamp
"""
@with_kw struct FrozenReportData
    masts::Vector{MastFrozenData}
    detection_settings::FrozenDetectionSettings
    generation_time::DateTime
end

"""
    calculate_frozen_duration_days(points::Int, interval_minutes::Int)::Float64

Convert frozen period points to days.

# Arguments
- `points::Int`: Number of data points
- `interval_minutes::Int`: Data interval in minutes

# Returns
- `Float64`: Duration in days
"""
function calculate_frozen_duration_days(points::Int, interval_minutes::Int)::Float64
    return (points * interval_minutes) / (60.0 * 24.0)
end

"""
    calculate_missing_duration_days(points::Int, interval_minutes::Int)::Float64

Convert missing data points to days.

# Arguments
- `points::Int`: Number of missing data points
- `interval_minutes::Int`: Data interval in minutes

# Returns
- `Float64`: Duration in days
"""
function calculate_missing_duration_days(points::Int, interval_minutes::Int)::Float64
    return (points * interval_minutes) / (60.0 * 24.0)
end

end # module
