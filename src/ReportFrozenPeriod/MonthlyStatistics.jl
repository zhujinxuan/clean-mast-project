module MonthlyStatistics

using DataFrames
using Dates
using ...Types.ReportFrozenPeriodData: MastFrozenData, SensorFrozenInfo, FrozenPeriod,
                                        calculate_frozen_duration_days

export generate_monthly_frozen_table, generate_monthly_missing_table, MonthlyData

"""
    MonthlyData

Helper struct for monthly aggregated data.

# Fields
- `year_month::Tuple{Int, Int}`: (year, month)
- `sensor_name::String`: Sensor name (e.g., "WS:80m:SE")
- `threshold_name::String`: Threshold set name (e.g., "加热型", "非加热型")
- `duration_days::Float64`: Duration in days
"""
struct MonthlyData
    year_month::Tuple{Int, Int}
    sensor_name::String
    threshold_name::String
    duration_days::Float64
end

"""
    generate_monthly_frozen_table(mast::MastFrozenData, threshold_name::String)::Vector{MonthlyData}

Generate monthly frozen duration table (in days) for one threshold set.

# Arguments
- `mast::MastFrozenData`: Mast frozen period data
- `threshold_name::String`: Threshold set name to filter (e.g., "加热型")

# Returns
- `Vector{MonthlyData}`: Monthly frozen duration for each sensor under this threshold
"""
function generate_monthly_frozen_table(mast::MastFrozenData, threshold_name::String)::Vector{MonthlyData}
    monthly_data = MonthlyData[]

    for sensor_info in mast.sensor_frozen_info
        # Get frozen periods for this threshold set
        frozen_periods = get(sensor_info.frozen_periods_by_threshold, threshold_name, FrozenPeriod[])

        if isempty(frozen_periods)
            continue
        end

        # Group frozen periods by month for this sensor
        monthly_frozen = group_frozen_periods_by_month(
            frozen_periods,
            mast.interval_minutes
        )

        # Convert to MonthlyData structs
        for ((year, month), duration_days) in monthly_frozen
            push!(monthly_data, MonthlyData(
                (year, month),
                sensor_info.sensor_name,
                threshold_name,
                duration_days
            ))
        end
    end

    return monthly_data
end

"""
    generate_monthly_missing_table(mast::MastFrozenData)::Vector{MonthlyData}

Generate monthly missing data duration table (in days).
This is independent of threshold sets.

# Arguments
- `mast::MastFrozenData`: Mast frozen period data

# Returns
- `Vector{MonthlyData}`: Monthly missing duration for each sensor
"""
function generate_monthly_missing_table(mast::MastFrozenData)::Vector{MonthlyData}
    monthly_data = MonthlyData[]

    # Iterate through months in analysis period
    current_month = Date(year(mast.analysis_start), month(mast.analysis_start), 1)
    end_month = Date(year(mast.analysis_end), month(mast.analysis_end), 1)

    while current_month <= end_month
        month_start = DateTime(current_month)
        next_month = current_month + Month(1)
        month_end = DateTime(next_month) - Millisecond(1)

        # Ensure month_end doesn't exceed analysis end
        if month_end > mast.analysis_end
            month_end = mast.analysis_end
        end

        # Calculate expected points in this month
        days_in_period = (month_end - month_start).value / (1000.0 * 60 * 60 * 24)
        expected_points_month = Int(ceil((days_in_period * 24 * 60) / mast.interval_minutes))

        # For each sensor, calculate missing data in this month
        for sensor_info in mast.sensor_frozen_info
            # Simple approach: distribute total missing proportionally
            # This is approximate - better would be to track actual timestamps
            if sensor_info.total_points > 0
                missing_ratio = sensor_info.total_missing_points / sensor_info.total_points
                missing_points_month = Int(round(expected_points_month * missing_ratio))
                missing_days = calculate_frozen_duration_days(missing_points_month, mast.interval_minutes)

                if missing_days > 0.0
                    push!(monthly_data, MonthlyData(
                        (year(current_month), month(current_month)),
                        sensor_info.sensor_name,
                        "missing",  # Special marker for missing data
                        missing_days
                    ))
                end
            end
        end

        current_month = next_month
    end

    return monthly_data
end

"""
    group_frozen_periods_by_month(frozen_periods, interval_minutes)::Dict{Tuple{Int, Int}, Float64}

Group frozen periods by month for one sensor.

# Arguments
- `frozen_periods::Vector{FrozenPeriod}`: All frozen periods
- `interval_minutes::Int`: Data interval

# Returns
- `Dict{Tuple{Int, Int}, Float64}`: Map of (year, month) => frozen_days
"""
function group_frozen_periods_by_month(
    frozen_periods::Vector{FrozenPeriod},
    interval_minutes::Int
)::Dict{Tuple{Int, Int}, Float64}

    monthly_frozen = Dict{Tuple{Int, Int}, Float64}()

    for period in frozen_periods
        # Distribute period across months it spans
        current_time = period.start_time

        while current_time <= period.end_time
            month_key = (year(current_time), month(current_time))

            # Add one interval's worth of frozen time to this month
            monthly_frozen[month_key] = get(monthly_frozen, month_key, 0.0) +
                                       (interval_minutes / (60.0 * 24.0))

            current_time += Minute(interval_minutes)
        end
    end

    return monthly_frozen
end

end # module
