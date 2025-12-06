module FrozenDetection

using DataFrames
using Dates
using Statistics: mean
using ...Types.ReportFrozenPeriodConfig: FrozenDetectionSettings, FrozenThresholdSet
using ...Types.ReportFrozenPeriodData: FrozenPeriod, SensorFrozenInfo
using ...Types.SensorColumns: SensorColumn, find_nearest_height_sensor, create_sensor_short_name
using ...Types.MastTimeSeries: TimeSeriesData, TimeRange
using ...TimeSeriesProcessing.IntervalDetection: detect_representative_interval
using ...TimeSeriesProcessing.Regularization: ensure_regular_intervals
using ..PeriodOperations:
    TimePeriod, periods_overlap, compute_intersection, merge_consecutive_periods, calculate_duration_points

export detect_frozen_periods_for_mast

"""
    find_temperature_periods(timestamps::Vector{DateTime}, temp_values::Vector, threshold::Float64, min_duration::Period, rep_interval::Period)::Vector{TimePeriod}

Find continuous periods where temperature < threshold for at least min_duration.

# Arguments
- `timestamps::Vector{DateTime}`: Timestamp vector
- `temp_values::Vector`: Temperature values (may contain missing)
- `threshold::Float64`: Temperature threshold (e.g., 2.0°C)
- `min_duration::Period`: Minimum duration (e.g., Hour(6))
- `rep_interval::Period`: Representative interval (e.g., Minute(10))

# Returns
- `Vector{TimePeriod}`: Periods meeting temperature condition
"""
function find_temperature_periods(
    timestamps::Vector{DateTime},
    temp_values::Vector,
    threshold::Float64,
    min_duration::Period,
    rep_interval::Period
)::Vector{TimePeriod}

    periods = TimePeriod[]
    period_start_idx = nothing

    for i in 1:length(timestamps)
        if ismissing(temp_values[i])
            # Missing value - skip but don't break the period
            # Continue to next point
            continue
        elseif temp_values[i] < threshold
            # Condition met - start or continue period
            if isnothing(period_start_idx)
                period_start_idx = i
            end
        else
            # Condition not met - end period if active
            if !isnothing(period_start_idx)
                period_end_idx = i - 1
                duration = timestamps[period_end_idx] - timestamps[period_start_idx]
                if duration >= min_duration
                    push!(periods, TimePeriod(
                        timestamps[period_start_idx],
                        timestamps[period_end_idx],
                        period_end_idx - period_start_idx + 1
                    ))
                end
                period_start_idx = nothing
            end
        end
    end

    # Handle final period if still active
    if !isnothing(period_start_idx)
        period_end_idx = length(timestamps)
        duration = timestamps[period_end_idx] - timestamps[period_start_idx]
        if duration >= min_duration
            push!(periods, TimePeriod(
                timestamps[period_start_idx],
                timestamps[period_end_idx],
                period_end_idx - period_start_idx + 1
            ))
        end
    end

    return periods
end

"""
    find_windspeed_stable_periods(timestamps::Vector{DateTime}, ws_values::Vector, threshold::Float64, min_duration::Period, rep_interval::Period)::Vector{TimePeriod}

Find continuous periods where wind speed change < threshold for at least min_duration.

# Arguments
- `timestamps::Vector{DateTime}`: Timestamp vector
- `ws_values::Vector`: Wind speed values (may contain missing)
- `threshold::Float64`: Max wind speed change threshold (e.g., 0.1 m/s)
- `min_duration::Period`: Minimum duration (e.g., Hour(6))
- `rep_interval::Period`: Representative interval (e.g., Minute(10))

# Returns
- `Vector{TimePeriod}`: Periods meeting wind speed stability condition
"""
function find_windspeed_stable_periods(
    timestamps::Vector{DateTime},
    ws_values::Vector,
    threshold::Float64,
    min_duration::Period,
    rep_interval::Period
)::Vector{TimePeriod}

    periods = TimePeriod[]
    period_start_idx = nothing
    ws_start = nothing

    for i in 1:length(timestamps)
        if ismissing(ws_values[i])
            # Missing value - skip but don't break the period
            continue
        else
            if isnothing(period_start_idx)
                # Start new period
                period_start_idx = i
                ws_start = ws_values[i]
            else
                # Check if stable (change < threshold)
                if abs(ws_values[i] - ws_start) <= threshold
                    # Continue period
                else
                    # Stability broken - end period
                    period_end_idx = i - 1
                    duration = timestamps[period_end_idx] - timestamps[period_start_idx]
                    if duration >= min_duration
                        push!(periods, TimePeriod(
                            timestamps[period_start_idx],
                            timestamps[period_end_idx],
                            period_end_idx - period_start_idx + 1
                        ))
                    end
                    # Start new period
                    period_start_idx = i
                    ws_start = ws_values[i]
                end
            end
        end
    end

    # Handle final period if still active
    if !isnothing(period_start_idx)
        period_end_idx = length(timestamps)
        duration = timestamps[period_end_idx] - timestamps[period_start_idx]
        if duration >= min_duration
            push!(periods, TimePeriod(
                timestamps[period_start_idx],
                timestamps[period_end_idx],
                period_end_idx - period_start_idx + 1
            ))
        end
    end

    return periods
end

"""
    find_winddirection_stable_periods(timestamps::Vector{DateTime}, wd_values::Vector, threshold::Float64, min_duration::Period, rep_interval::Period)::Vector{TimePeriod}

Find continuous periods where wind direction change < threshold for at least min_duration.
Handles wraparound (355° to 5° is 10°, not 350°).

# Arguments
- `timestamps::Vector{DateTime}`: Timestamp vector
- `wd_values::Vector`: Wind direction values (may contain missing)
- `threshold::Float64`: Max wind direction change threshold (e.g., 5.0°)
- `min_duration::Period`: Minimum duration (e.g., Hour(6))
- `rep_interval::Period`: Representative interval (e.g., Minute(10))

# Returns
- `Vector{TimePeriod}`: Periods meeting wind direction stability condition
"""
function find_winddirection_stable_periods(
    timestamps::Vector{DateTime},
    wd_values::Vector,
    threshold::Float64,
    min_duration::Period,
    rep_interval::Period
)::Vector{TimePeriod}

    periods = TimePeriod[]
    period_start_idx = nothing
    wd_start = nothing

    for i in 1:length(timestamps)
        if ismissing(wd_values[i])
            # Missing value - skip but don't break the period
            continue
        else
            if isnothing(period_start_idx)
                # Start new period
                period_start_idx = i
                wd_start = wd_values[i]
            else
                # Check if stable (change < threshold with wraparound handling)
                wd_diff = abs(wd_values[i] - wd_start)
                wd_diff = min(wd_diff, 360.0 - wd_diff)  # Handle wraparound

                if wd_diff <= threshold
                    # Continue period
                else
                    # Stability broken - end period
                    period_end_idx = i - 1
                    duration = timestamps[period_end_idx] - timestamps[period_start_idx]
                    if duration >= min_duration
                        push!(periods, TimePeriod(
                            timestamps[period_start_idx],
                            timestamps[period_end_idx],
                            period_end_idx - period_start_idx + 1
                        ))
                    end
                    # Start new period
                    period_start_idx = i
                    wd_start = wd_values[i]
                end
            end
        end
    end

    # Handle final period if still active
    if !isnothing(period_start_idx)
        period_end_idx = length(timestamps)
        duration = timestamps[period_end_idx] - timestamps[period_start_idx]
        if duration >= min_duration
            push!(periods, TimePeriod(
                timestamps[period_start_idx],
                timestamps[period_end_idx],
                period_end_idx - period_start_idx + 1
            ))
        end
    end

    return periods
end

"""
    detect_nonheated_frozen_periods(df::DataFrame, ws_sensor::SensorColumn, wd_sensor::Union{SensorColumn, Nothing}, temp_sensor::SensorColumn, threshold_set::FrozenThresholdSet, rep_interval::Period)::Vector{FrozenPeriod}

Detect frozen periods for non-heated sensors using component-based intersection approach.

Steps:
1. Find periods meeting each condition independently (T, WS stability, WD stability)
2. Compute intersection of all three period sets
3. Merge consecutive periods
4. Filter out periods with >50% missing data
5. Return final frozen periods

# Arguments
- `df::DataFrame`: Time series data (regularized)
- `ws_sensor::SensorColumn`: Wind speed sensor
- `wd_sensor::Union{SensorColumn, Nothing}`: Wind direction sensor (optional)
- `temp_sensor::SensorColumn`: Temperature sensor
- `threshold_set::FrozenThresholdSet`: Threshold configuration for non-heated sensors
- `rep_interval::Period`: Representative interval (e.g., Minute(10))

# Returns
- `Vector{FrozenPeriod}`: Detected frozen periods
"""
function detect_nonheated_frozen_periods(
    df::DataFrame,
    ws_sensor::SensorColumn,
    wd_sensor::Union{SensorColumn, Nothing},
    temp_sensor::SensorColumn,
    threshold_set::FrozenThresholdSet,
    rep_interval::Period
)::Vector{FrozenPeriod}

    timestamps = df[!, :timestamp]
    ws_values = df[!, ws_sensor.columnName]
    wd_values = isnothing(wd_sensor) ? fill(missing, length(timestamps)) :
                df[!, wd_sensor.columnName]
    temp_values = df[!, temp_sensor.columnName]

    # Minimum duration (from threshold_set or default 6 hours)
    min_duration = if isnothing(threshold_set.min_duration_seconds)
        Hour(6)
    else
        Second(threshold_set.min_duration_seconds)
    end

    # Step 1: Find wind stability periods (WS and optionally WD)
    ws_periods = find_windspeed_stable_periods(
        timestamps,
        ws_values,
        threshold_set.windspeed_change_threshold,
        min_duration,
        rep_interval
    )

    # Step 2: Intersect WS with WD (if available) to get wind stable periods
    wind_stable_periods = if isnothing(wd_sensor)
        # No wind direction sensor - use WS periods directly
        ws_periods
    else
        # Have wind direction sensor - intersect WS and WD
        wd_periods = find_winddirection_stable_periods(
            timestamps,
            wd_values,
            threshold_set.winddirection_change_threshold,
            min_duration,
            rep_interval
        )

        intersected = TimePeriod[]
        for ws_period in ws_periods
            for wd_period in wd_periods
                if periods_overlap(ws_period, wd_period)
                    # Compute intersection window
                    start_time = max(ws_period.start_time, wd_period.start_time)
                    end_time = min(ws_period.end_time, wd_period.end_time)
                    duration = end_time - start_time

                    if duration >= min_duration
                        duration_points = calculate_duration_points(start_time, end_time, rep_interval)
                        push!(intersected, TimePeriod(start_time, end_time, duration_points))
                    end
                end
            end
        end
        intersected
    end

    # Step 3: Filter wind stable periods by average temperature during each period
    temp_filtered_periods = TimePeriod[]
    for period in wind_stable_periods
        # Extract temperature values during this period
        period_mask = (timestamps .>= period.start_time) .& (timestamps .<= period.end_time)
        period_temps = temp_values[period_mask]

        # Calculate average temperature (skipping missing values)
        valid_temps = filter(!ismissing, period_temps)
        if isempty(valid_temps)
            # All temperatures missing in this period - skip
            continue
        end

        avg_temp = mean(valid_temps)

        # Keep period if average temperature < threshold
        if avg_temp < threshold_set.temperature_threshold
            push!(temp_filtered_periods, period)
        end
    end

    # Use temp_filtered_periods as the intersected_periods for remaining logic
    intersected_periods = temp_filtered_periods

    # Step 4: Merge consecutive periods
    merged_periods = merge_consecutive_periods(intersected_periods, rep_interval)

    # Step 5: Filter out periods with >50% missing data
    filtered_periods = filter(merged_periods) do period
        # Count missing points in this period
        period_df = df[
            (df.timestamp .>= period.start_time) .&
            (df.timestamp .<= period.end_time), :]

        missing_ws = count(ismissing, period_df[!, ws_sensor.columnName])
        missing_temp = count(ismissing, period_df[!, temp_sensor.columnName])

        if !isnothing(wd_sensor)
            missing_wd = count(ismissing, period_df[!, wd_sensor.columnName])
            max_missing = max(missing_ws, missing_temp, missing_wd)
        else
            max_missing = max(missing_ws, missing_temp)
        end

        total_points = nrow(period_df)
        missing_ratio = total_points > 0 ? max_missing / total_points : 1.0

        return missing_ratio <= 0.5  # Keep if <=50% missing
    end

    # Step 6: Convert to FrozenPeriod
    frozen_periods = map(filtered_periods) do period
        FrozenPeriod(
            start_time = period.start_time,
            end_time = period.end_time,
            duration_points = period.duration_points,
            threshold_name = threshold_set.name
        )
    end

    return frozen_periods
end

"""
    detect_heated_frozen_periods(df::DataFrame, ws_sensor::SensorColumn, temp_sensor::SensorColumn, rh_sensor::Union{SensorColumn, Nothing}, threshold_set::FrozenThresholdSet, rep_interval::Period)::Vector{FrozenPeriod}

Detect frozen periods for heated sensors using simple point-by-point check.

Criteria: T < 2°C AND RH < 80% (if RH available)
No sliding window, no wind stability check.
Duration = number of consecutive points * rep_interval

# Arguments
- `df::DataFrame`: Time series data (regularized)
- `ws_sensor::SensorColumn`: Wind speed sensor (used to check for missing data)
- `temp_sensor::SensorColumn`: Temperature sensor
- `rh_sensor::Union{SensorColumn, Nothing}`: RH sensor (optional)
- `threshold_set::FrozenThresholdSet`: Threshold configuration for heated sensors
- `rep_interval::Period`: Representative interval (e.g., Minute(10))

# Returns
- `Vector{FrozenPeriod}`: Detected frozen periods
"""
function detect_heated_frozen_periods(
    df::DataFrame,
    ws_sensor::SensorColumn,
    temp_sensor::SensorColumn,
    rh_sensor::Union{SensorColumn, Nothing},
    threshold_set::FrozenThresholdSet,
    rep_interval::Period
)::Vector{FrozenPeriod}

    timestamps = df[!, :timestamp]
    ws_values = df[!, ws_sensor.columnName]
    temp_values = df[!, temp_sensor.columnName]
    rh_values = isnothing(rh_sensor) ? fill(missing, length(timestamps)) :
                df[!, rh_sensor.columnName]

    frozen_periods = FrozenPeriod[]
    period_start_idx = nothing

    for i in 1:length(timestamps)
        # Check if point meets criteria: T < threshold AND (RH < threshold OR no RH)
        temp_ok = !ismissing(temp_values[i]) && temp_values[i] < threshold_set.temperature_threshold

        rh_ok = if isnothing(threshold_set.rh_threshold)
            true  # No RH threshold requirement
        elseif isnothing(rh_sensor)
            true  # No RH sensor available
        else
            !ismissing(rh_values[i]) && rh_values[i] < threshold_set.rh_threshold
        end

        # Also check that WS is not missing (for consistency)
        ws_ok = !ismissing(ws_values[i])

        if temp_ok && rh_ok && ws_ok
            # Condition met - start or continue period
            if isnothing(period_start_idx)
                period_start_idx = i
            end
        else
            # Condition not met - end period if active
            if !isnothing(period_start_idx)
                period_end_idx = i - 1
                push!(frozen_periods, FrozenPeriod(
                    start_time = timestamps[period_start_idx],
                    end_time = timestamps[period_end_idx],
                    duration_points = period_end_idx - period_start_idx + 1,
                    threshold_name = threshold_set.name
                ))
                period_start_idx = nothing
            end
        end
    end

    # Handle final period if still active
    if !isnothing(period_start_idx)
        period_end_idx = length(timestamps)
        push!(frozen_periods, FrozenPeriod(
            start_time = timestamps[period_start_idx],
            end_time = timestamps[period_end_idx],
            duration_points = period_end_idx - period_start_idx + 1,
            threshold_name = threshold_set.name
        ))
    end

    return frozen_periods
end

"""
    detect_frozen_periods_for_mast(data::TimeSeriesData, settings::FrozenDetectionSettings)::Vector{SensorFrozenInfo}

Core detection function for one mast.
For each wind sensor, detects frozen periods using ALL threshold configurations.
Returns Vector{SensorFrozenInfo} for all wind speed sensors.

# Arguments
- `data::TimeSeriesData`: Raw mast data
- `settings::FrozenDetectionSettings`: Detection criteria (multiple threshold sets)

# Returns
- `Vector{SensorFrozenInfo}`: Frozen period info for each wind speed sensor
"""
function detect_frozen_periods_for_mast(
    data::TimeSeriesData,
    settings::FrozenDetectionSettings
)::Vector{SensorFrozenInfo}

    # Detect representative interval and ensure regular intervals
    representative_interval = detect_representative_interval(data)
    time_range = TimeRange(
        minimum(data.df.timestamp),
        maximum(data.df.timestamp)
    )
    regularized_data = ensure_regular_intervals(data, time_range, representative_interval)

    @info "Ensured regular $(representative_interval) intervals for frozen period detection"

    # Find temperature sensor (lowest height with avg statType)
    temp_sensor = find_temperature_sensor(regularized_data.sensors)
    if isnothing(temp_sensor)
        @warn "No temperature sensor found - frozen detection cannot proceed"
        return SensorFrozenInfo[]
    end

    # Check for RH sensor (optional - just log if missing)
    rh_sensor = find_rh_sensor(regularized_data.sensors)
    rh_sensor_available = !isnothing(rh_sensor)
    if !rh_sensor_available
        @info "RH sensor not found - frozen detection will proceed without it"
    end

    # Get all wind speed sensors (avg statType)
    wind_speed_sensors = filter(
        s -> s.sensorType == "WindSpeed" && s.statType == "avg",
        regularized_data.sensors
    )

    if isempty(wind_speed_sensors)
        @warn "No wind speed sensors found"
        return SensorFrozenInfo[]
    end

    println("  📊 Analyzing $(length(wind_speed_sensors)) wind speed sensors with $(length(settings.thresholds)) threshold sets")

    # Detect frozen periods for each wind speed sensor
    sensor_frozen_info = map(wind_speed_sensors) do ws_sensor
        # Find corresponding wind direction sensor
        wd_sensor = find_nearest_height_sensor(
            ws_sensor.height,
            regularized_data.sensors,
            "WindDirection",
            "avg"
        )

        if isnothing(wd_sensor)
            @warn "No wind direction sensor found for $(create_sensor_short_name(ws_sensor))"
        end

        # Detect frozen periods for EACH threshold set
        frozen_by_threshold = Dict{String, Vector{FrozenPeriod}}()

        for threshold_set in settings.thresholds
            frozen_periods = detect_frozen_periods_for_sensor(
                regularized_data.df,
                ws_sensor,
                wd_sensor,
                temp_sensor,
                rh_sensor,
                threshold_set,
                representative_interval
            )
            frozen_by_threshold[threshold_set.name] = frozen_periods

            total_points = sum(fp.duration_points for fp in frozen_periods; init=0)
            println("    - $(create_sensor_short_name(ws_sensor)) [$(threshold_set.name)]: $(length(frozen_periods)) frozen periods, $(total_points) points")
        end

        # Calculate statistics
        total_missing_points = count(ismissing, regularized_data.df[!, ws_sensor.columnName])
        total_points = nrow(regularized_data.df)

        sensor_info = SensorFrozenInfo(
            sensor = ws_sensor,
            sensor_name = create_sensor_short_name(ws_sensor),
            temperature_sensor = temp_sensor,
            direction_sensor = wd_sensor,
            rh_sensor_available = rh_sensor_available,
            frozen_periods_by_threshold = frozen_by_threshold,
            total_missing_points = total_missing_points,
            total_points = total_points
        )

        return sensor_info
    end

    return sensor_frozen_info
end

"""
    detect_frozen_periods_for_sensor(df, ws_sensor, wd_sensor, temp_sensor, rh_sensor, threshold_set, rep_interval)::Vector{FrozenPeriod}

Dispatch frozen period detection based on threshold characteristics.

- If `windspeed_change_threshold >= 100.0`: Heated sensor → use point-by-point check
- Otherwise: Non-heated sensor → use component-based intersection

# Arguments
- `df::DataFrame`: Time series data (regularized)
- `ws_sensor::SensorColumn`: Wind speed sensor
- `wd_sensor::Union{SensorColumn, Nothing}`: Wind direction sensor (optional)
- `temp_sensor::SensorColumn`: Temperature sensor
- `rh_sensor::Union{SensorColumn, Nothing}`: RH sensor (optional)
- `threshold_set::FrozenThresholdSet`: One set of detection thresholds
- `rep_interval::Period`: Representative interval (e.g., Minute(10))

# Returns
- `Vector{FrozenPeriod}`: All detected frozen periods for this threshold set
"""
function detect_frozen_periods_for_sensor(
    df::DataFrame,
    ws_sensor::SensorColumn,
    wd_sensor::Union{SensorColumn, Nothing},
    temp_sensor::SensorColumn,
    rh_sensor::Union{SensorColumn, Nothing},
    threshold_set::FrozenThresholdSet,
    rep_interval::Period
)::Vector{FrozenPeriod}

    # Determine sensor type based on wind speed threshold
    # If WS threshold >= 100.0, it's effectively disabled → heated sensor
    is_heated = threshold_set.windspeed_change_threshold >= 100.0

    if is_heated
        return detect_heated_frozen_periods(
            df,
            ws_sensor,
            temp_sensor,
            rh_sensor,
            threshold_set,
            rep_interval
        )
    else
        return detect_nonheated_frozen_periods(
            df,
            ws_sensor,
            wd_sensor,
            temp_sensor,
            threshold_set,
            rep_interval
        )
    end
end

"""
    find_temperature_sensor(sensors::Vector{SensorColumn})::Union{SensorColumn, Nothing}

Find temperature sensor - lowest height with avg statType.

# Arguments
- `sensors::Vector{SensorColumn}`: All sensors

# Returns
- `Union{SensorColumn, Nothing}`: Temperature sensor or nothing
"""
function find_temperature_sensor(sensors::Vector{SensorColumn})::Union{SensorColumn, Nothing}
    temp_sensors = filter(
        s -> s.sensorType == "Temperature" && s.statType == "avg",
        sensors
    )
    isempty(temp_sensors) && return nothing
    return reduce((s1, s2) -> s1.height < s2.height ? s1 : s2, temp_sensors)
end

"""
    find_rh_sensor(sensors::Vector{SensorColumn})::Union{SensorColumn, Nothing}

Find RH sensor - sensorType="Analog" with column name containing "RH".

# Arguments
- `sensors::Vector{SensorColumn}`: All sensors

# Returns
- `Union{SensorColumn, Nothing}`: RH sensor or nothing
"""
function find_rh_sensor(sensors::Vector{SensorColumn})::Union{SensorColumn, Nothing}
    rh_sensors = filter(sensors) do s
        s.sensorType == "Analog" && occursin("RH", String(s.columnName))
    end
    return isempty(rh_sensors) ? nothing : first(rh_sensors)
end

end # module
