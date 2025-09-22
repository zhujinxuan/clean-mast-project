module ReportCleanData

using Parameters
using DataFrames
using Dates
using ..MastTimeSeries: TimeSeriesData
using ..ViolationData: ViolationAnalysisData

export MastReportData, SensorCoverageInfo, ViolationInfo, ReportGenerationData, DetectedInterval

"""
    DetectedInterval

Represents a detected time interval for data processing.
"""
@with_kw struct DetectedInterval
    interval::Minute                               # The detected interval (e.g., 10 minutes)
    confidence::Float64 = 1.0                     # Confidence in the detection (0-1)
    description::String = "Detected interval"     # Human-readable description
end

"""
    SensorCoverageInfo

Information about sensor data coverage for a single sensor.
"""
@with_kw struct SensorCoverageInfo
    name::String                    # Sensor name
    raw_coverage::Float64          # Raw data coverage percentage (0-100)
    clean_coverage::Float64        # Clean data coverage percentage (0-100)
    total_missing_days::Float64    # Total missing time in days
end

"""
    ViolationInfo

Information about a single violation rule for a sensor.
"""
@with_kw struct ViolationInfo
    rule_name::String              # Name of the violated rule
    count::Int                     # Number of violations
end

"""
    MastReportData

Complete report data for a single mast, including raw data, clean data,
coverage statistics, and violation information.
"""
@with_kw struct MastReportData
    name::String                                    # Mast name (e.g., "pn-002824")
    raw_data::TimeSeriesData                       # Raw time series data
    clean_data::TimeSeriesData                     # Clean time series data
    sensor_coverage::Vector{SensorCoverageInfo}    # Coverage info for each sensor
    violation_data::ViolationAnalysisData          # Properly typed violation data
    detected_interval::DetectedInterval           # Detected data interval
    expected_points::Int                           # Expected number of data points
end

"""
    ReportGenerationData

Container for all data needed to generate a complete report.
"""
@with_kw struct ReportGenerationData
    mast_data::Vector{MastReportData}              # Data for all masts
    report_title::String = "数据清洗报告"           # Report title
    generation_time::String = ""                   # Report generation timestamp
end

end # module
