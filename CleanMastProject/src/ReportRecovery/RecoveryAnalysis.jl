module RecoveryAnalysis

using DataFrames
using Dates
using ...Types.ReportRecoveryConfig: ReportRecoveryMast
using ...Types.ReportRecoveryData: SensorRecoveryInfo, MastRecoveryData, get_sensor_display_name
using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries
using ...Types.SensorColumns: SensorColumn
using ...TimeSeriesProcessing.IntervalDetection: detect_representative_interval
using ...TimeSeriesProcessing.Regularization: ensure_regular_intervals

export analyze_mast_recovery

"""
    analyze_mast_recovery(mast_config::ReportRecoveryMast, config_dir::String)::MastRecoveryData

Analyze data recovery for a single mast by comparing data at each reconstruction stage.

# Arguments
- `mast_config::ReportRecoveryMast`: Configuration with data sources for all stages
- `config_dir::String`: Config directory for resolving relative paths

# Returns
- `MastRecoveryData`: Complete recovery statistics for the mast
"""
function analyze_mast_recovery(mast_config::ReportRecoveryMast, config_dir::String)::MastRecoveryData
    println("📊 Analyzing recovery for mast: $(mast_config.name)")

    # Load time series data from all stages
    tower_shading_data = load_timeseries(mast_config.tower_shading, config_dir)
    single_data = load_timeseries(mast_config.reconstruct_single, config_dir)
    cross_data = isnothing(mast_config.reconstruct_cross) ? nothing : load_timeseries(mast_config.reconstruct_cross, config_dir)
    meso_data = load_timeseries(mast_config.reconstruct_meso, config_dir)

    # Detect representative interval from the final meso data
    representative_interval = detect_representative_interval(meso_data)
    println("  📊 Using $(representative_interval.value)-minute intervals for recovery analysis")

    # Check if stages are actually different (some may be the same if stages were skipped)
    single_is_same = (mast_config.reconstruct_single == mast_config.tower_shading)
    cross_is_same = isnothing(mast_config.reconstruct_cross) || (mast_config.reconstruct_cross == mast_config.reconstruct_single)

    # Filter data to analysis time range and regularize to consistent intervals
    time_range = mast_config.time_range
    tower_filtered = filter_time_range(tower_shading_data, time_range.min, time_range.max)
    tower_filtered = ensure_regular_intervals(tower_filtered, time_range, representative_interval)

    single_filtered = filter_time_range(single_data, time_range.min, time_range.max)
    single_filtered = ensure_regular_intervals(single_filtered, time_range, representative_interval)

    cross_filtered = if isnothing(cross_data)
        nothing
    else
        filtered = filter_time_range(cross_data, time_range.min, time_range.max)
        ensure_regular_intervals(filtered, time_range, representative_interval)
    end

    meso_filtered = filter_time_range(meso_data, time_range.min, time_range.max)
    meso_filtered = ensure_regular_intervals(meso_filtered, time_range, representative_interval)
    
    # Get total analysis points
    total_points = nrow(meso_filtered.df)

    # Filter sensors to only analyze 'avg' statType sensors
    avg_sensors = filter(sensor -> sensor.statType == "avg", meso_filtered.sensors)
    println("  📊 Analyzing $(length(avg_sensors)) 'avg' sensors (filtered from $(length(meso_filtered.sensors)) total sensors)")

    # Analyze each 'avg' sensor
    sensor_recovery = map(avg_sensors) do sensor
        analyze_sensor_recovery(
            sensor,
            tower_filtered,
            single_filtered,
            cross_filtered,
            meso_filtered,
            total_points,
            single_is_same,
            cross_is_same
        )
    end

    # Sort sensor recovery data by sensor type priority and height
    sorted_sensor_recovery = sort_sensor_recovery(sensor_recovery)

    return MastRecoveryData(
        name = mast_config.name,
        sensor_recovery = sorted_sensor_recovery,
        analysis_start = time_range.min,
        analysis_end = time_range.max,
        total_analysis_points = total_points
    )
end

"""
    analyze_sensor_recovery(sensor::SensorColumn, tower_data, single_data, cross_data, meso_data, total_points, single_is_same, cross_is_same)::SensorRecoveryInfo

Analyze recovery statistics for a single sensor across all reconstruction stages.
"""
function analyze_sensor_recovery(
    sensor::SensorColumn,
    tower_data::TimeSeriesData,
    single_data::TimeSeriesData,
    cross_data::Union{TimeSeriesData, Nothing},
    meso_data::TimeSeriesData,
    total_points::Int,
    single_is_same::Bool,
    cross_is_same::Bool
)::SensorRecoveryInfo
    
    col_name = sensor.columnName
    
    # Count missing data at each stage
    initial_missing = count_missing_values(tower_data.df, col_name)
    after_single_missing = count_missing_values(single_data.df, col_name)
    after_cross_missing = isnothing(cross_data) ? after_single_missing : count_missing_values(cross_data.df, col_name)
    final_missing = count_missing_values(meso_data.df, col_name)

    # Calculate filled counts (reduction in missing data)
    # If stages are the same, no reconstruction happened at that stage
    single_filled = single_is_same ? 0 : max(0, initial_missing - after_single_missing)
    cross_filled = (cross_is_same || isnothing(cross_data)) ? 0 : max(0, after_single_missing - after_cross_missing)
    meso_filled = max(0, after_cross_missing - final_missing)
    
    return SensorRecoveryInfo(
        sensor = sensor,
        sensor_name = get_sensor_display_name(sensor),
        initial_missing = initial_missing,
        single_filled = single_filled,
        cross_filled = cross_filled,
        meso_filled = meso_filled,
        final_missing = final_missing,
        total_points = total_points
    )
end

"""
    filter_time_range(data::TimeSeriesData, start_time::DateTime, end_time::DateTime)::TimeSeriesData

Filter time series data to specified time range.
"""
function filter_time_range(data::TimeSeriesData, start_time::DateTime, end_time::DateTime)::TimeSeriesData
    filtered_df = filter(row -> start_time <= row.timestamp <= end_time, data.df)
    return TimeSeriesData(filtered_df, data.sensors)
end

"""
    count_missing_values(df::DataFrame, col_name::Symbol)::Int

Count missing values in a specific column of a DataFrame.
"""
function count_missing_values(df::DataFrame, col_name::Symbol)::Int
    if !hasproperty(df, col_name)
        return 0  # Column doesn't exist, treat as no missing data
    end
    return count(ismissing, df[!, col_name])
end

"""
    validate_data_consistency(tower_data, single_data, cross_data, meso_data)::Bool

Validate that all datasets have consistent timestamps and sensor configurations.
"""
function validate_data_consistency(
    tower_data::TimeSeriesData,
    single_data::TimeSeriesData,
    cross_data::TimeSeriesData,
    meso_data::TimeSeriesData
)::Bool
    
    # Check that all datasets have the same number of rows
    nrows = [nrow(data.df) for data in [tower_data, single_data, cross_data, meso_data]]
    if !all(n == nrows[1] for n in nrows)
        @warn "Inconsistent number of rows across datasets: $nrows"
        return false
    end
    
    # Check that timestamps are consistent
    timestamps = [data.df.timestamp for data in [tower_data, single_data, cross_data, meso_data]]
    if !all(ts == timestamps[1] for ts in timestamps)
        @warn "Inconsistent timestamps across datasets"
        return false
    end
    
    return true
end

"""
    get_recovery_summary(recovery_info::SensorRecoveryInfo)::Dict{String, Any}

Get summary statistics for a sensor's recovery performance.
"""
function get_recovery_summary(recovery_info::SensorRecoveryInfo)::Dict{String, Any}
    total_filled = recovery_info.single_filled + recovery_info.cross_filled + recovery_info.meso_filled
    recovery_rate = recovery_info.initial_missing > 0 ? 
                   (total_filled / recovery_info.initial_missing) * 100.0 : 0.0
    final_coverage = recovery_info.total_points > 0 ?
                    ((recovery_info.total_points - recovery_info.final_missing) / recovery_info.total_points) * 100.0 : 0.0
    
    return Dict{String, Any}(
        "sensor_name" => recovery_info.sensor_name,
        "initial_missing" => recovery_info.initial_missing,
        "total_filled" => total_filled,
        "recovery_rate_percent" => round(recovery_rate, digits=1),
        "final_coverage_percent" => round(final_coverage, digits=1),
        "single_contribution" => recovery_info.single_filled,
        "cross_contribution" => recovery_info.cross_filled,
        "meso_contribution" => recovery_info.meso_filled
    )
end

"""
    sort_sensor_recovery(sensor_recovery::Vector{SensorRecoveryInfo})::Vector{SensorRecoveryInfo}

Sort sensor recovery data by sensor type priority (WS → WD → Temp → Pres → others) and then by height (descending).
"""
function sort_sensor_recovery(sensor_recovery::Vector{SensorRecoveryInfo})::Vector{SensorRecoveryInfo}
    # Define sensor type priority order
    function get_sensor_type_priority(sensor_type::String)::Int
        priority_map = Dict(
            "WindSpeed" => 1,
            "WindDirection" => 2,
            "Temperature" => 3,
            "Pressure" => 4,
            "Analog" => 5  # For RH, etc.
        )
        return get(priority_map, sensor_type, 6)  # Default priority for unknown types
    end

    # Sort by: 1) sensor type priority, 2) height (descending), 3) sensor direction
    return sort(sensor_recovery, by = info -> (
        get_sensor_type_priority(info.sensor.sensorType),
        -info.sensor.height,  # Negative for descending order
        info.sensor.sensorDirection
    ))
end

end # module
