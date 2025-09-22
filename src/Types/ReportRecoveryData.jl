module ReportRecoveryData

using Parameters
using Dates
using ..SensorColumns: SensorColumn

export SensorRecoveryInfo, MastRecoveryData, RecoveryReportData

"""
    SensorRecoveryInfo

Recovery statistics for a single sensor during the analysis time range.

# Fields
- `sensor::SensorColumn`: Sensor information
- `sensor_name::String`: Clean sensor name (e.g., "WS_120m_N", "WD_80m", "Temp_10m")
- `initial_missing::Int`: Missing data count after tower shading (starting point)
- `single_filled::Int`: Data points filled by single-mast reconstruction
- `cross_filled::Int`: Data points filled by cross-mast reconstruction  
- `meso_filled::Int`: Data points filled by mesoscale reconstruction
- `final_missing::Int`: Remaining missing data count after all reconstructions
- `total_points::Int`: Total data points in the analysis time range
"""
@with_kw struct SensorRecoveryInfo
    sensor::SensorColumn
    sensor_name::String
    initial_missing::Int
    single_filled::Int
    cross_filled::Int
    meso_filled::Int
    final_missing::Int
    total_points::Int
end

"""
    MastRecoveryData

Complete recovery data for a single mast.

# Fields
- `name::String`: Mast name
- `sensor_recovery::Vector{SensorRecoveryInfo}`: Recovery info for each sensor
- `analysis_start::DateTime`: Start of analysis time range
- `analysis_end::DateTime`: End of analysis time range
- `total_analysis_points::Int`: Total timestamps in analysis period
"""
@with_kw struct MastRecoveryData
    name::String
    sensor_recovery::Vector{SensorRecoveryInfo}
    analysis_start::DateTime
    analysis_end::DateTime
    total_analysis_points::Int
end

"""
    RecoveryReportData

Complete data for generating recovery status report.

# Fields
- `masts::Vector{MastRecoveryData}`: Recovery data for all masts
- `generation_time::DateTime`: When the report was generated
"""
@with_kw struct RecoveryReportData
    masts::Vector{MastRecoveryData}
    generation_time::DateTime
end

# Helper functions for calculating recovery statistics

"""
    calculate_recovery_percentage(filled::Int, initial_missing::Int)::Float64

Calculate the percentage of missing data that was recovered.
"""
function calculate_recovery_percentage(filled::Int, initial_missing::Int)::Float64
    return initial_missing > 0 ? (filled / initial_missing) * 100.0 : 0.0
end

"""
    calculate_final_coverage(final_missing::Int, total_points::Int)::Float64

Calculate the final data coverage percentage.
"""
function calculate_final_coverage(final_missing::Int, total_points::Int)::Float64
    return total_points > 0 ? ((total_points - final_missing) / total_points) * 100.0 : 0.0
end

"""
    get_sensor_display_name(sensor::SensorColumn)::String

Generate clean sensor name for display in reports.
Follows the same naming convention as SensorInventoryReport.
"""
function get_sensor_display_name(sensor::SensorColumn)::String
    if sensor.sensorType == "WindSpeed"
        return "WS_$(Int(sensor.height))m_$(sensor.sensorDirection)"
    elseif sensor.sensorType == "WindDirection"
        return "WD_$(Int(sensor.height))m"
    elseif sensor.sensorType == "Temperature"
        return "Temp_$(Int(sensor.height))m"
    elseif sensor.sensorType == "Analog"
        # Check if it's pressure or humidity based on column name
        col_name = string(sensor.columnName)
        if occursin("Pres", col_name) || occursin("kPa", col_name)
            return "Pres_$(Int(sensor.height))m"
        elseif occursin("RH", col_name) || occursin("%RH", col_name)
            return "RH_$(Int(sensor.height))m"
        else
            return "Analog_$(Int(sensor.height))m"
        end
    else
        return "$(sensor.sensorType)_$(Int(sensor.height))m"
    end
end

end # module
