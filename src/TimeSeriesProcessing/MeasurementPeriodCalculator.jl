module MeasurementPeriodCalculator

using ...Types.MastTimeSeries: TimeSeriesData, TimeRange
using ...TimeSeriesProcessing.IntervalDetection: get_interval_statistics
using Dates
using DataFrames

export calculate_optimal_measurement_period, DailyScore

"""
    DailyScore

Struct representing the data coverage quality score for a single day.

# Fields
- `date::Date`: The date being scored
- `single_score::Float64`: Reconstruct-single coverage score (0.0 to 1.0)
- `cross_score::Float64`: Reconstruct-cross coverage score (0.0 to 1.0)  
- `total_score::Float64`: Weighted total score (single_weight * single_score + cross_weight * cross_score)
"""
struct DailyScore
    date::Date
    single_score::Float64
    cross_score::Float64
    total_score::Float64
end

"""
    calculate_max_allowed_end_time(meso_ts::TimeSeriesData)::DateTime

Calculate the maximum allowed end time for measurement period selection.
This ensures we don't select periods that extend beyond available mesoscale data.

Formula: last_meso_time + representative_interval - 1 second

# Arguments
- `meso_ts::TimeSeriesData`: Mesoscale time series data

# Returns
- `DateTime`: Maximum allowed end time for any measurement period
"""
function calculate_max_allowed_end_time(meso_ts::TimeSeriesData)::DateTime
    # Get meso data bounds and interval
    valid_times = filter(!ismissing, meso_ts.df.timestamp)
    if isempty(valid_times)
        error("Mesoscale data has no valid timestamps")
    end
    
    meso_last_time = maximum(valid_times)
    stats = get_interval_statistics(meso_ts)
    representative_interval = stats.representative_interval
    
    # Add one interval period and subtract 1 second to get the boundary
    return meso_last_time + representative_interval - Second(1)
end

"""
    get_highest_windspeed_column(ts_data::TimeSeriesData)::String

Find the wind speed sensor column at the greatest height.

# Arguments  
- `ts_data::TimeSeriesData`: Time series data containing sensor information

# Returns
- `Symbol`: Column name of the highest wind speed sensor

# Throws
- `ErrorException`: If no wind speed sensors are found
"""
function get_highest_windspeed_column(ts_data::TimeSeriesData)::Symbol
    # Filter for wind speed sensors (statType = "avg", sensorType = "WindSpeed")
    windspeed_sensors = filter(ts_data.sensors) do sensor
        sensor.statType == "avg" && sensor.sensorType == "WindSpeed"
    end
    
    if isempty(windspeed_sensors)
        error("No wind speed sensors found in time series data")
    end
    
    # Find sensor with maximum height - argmax returns the element, not index
    highest_sensor = argmax(s -> s.height, windspeed_sensors)
    return highest_sensor.columnName
end

"""
    calculate_dataset_daily_scores(
        ts_data::TimeSeriesData, 
        ws_column::Symbol, 
        weight_factor::Float64,
        max_end_date::Date
    )::DataFrame

Calculate daily coverage scores for a single dataset using vectorized operations.
Much more efficient than iterating through each day individually.

# Arguments
- `ts_data::TimeSeriesData`: Time series data
- `ws_column::Symbol`: Wind speed column name to analyze
- `weight_factor::Float64`: Weight factor for this dataset (e.g., 1.0 for single, 0.5 for cross)
- `max_end_date::Date`: Maximum allowed end date

# Returns
- `DataFrame`: Two columns [:day, :daily_score] with daily coverage scores
"""
function calculate_dataset_daily_scores(
    ts_data::TimeSeriesData, 
    ws_column::Symbol, 
    weight_factor::Float64,
    max_end_date::Date
)::DataFrame
    df = copy(ts_data.df)
    
    # Check if wind speed column exists
    if !(ws_column in propertynames(df))
        return DataFrame(day=Date[], daily_score=Float64[])
    end
    
    # Add day column and filter valid timestamps
    valid_timestamps = .!ismissing.(df.timestamp)
    df = df[valid_timestamps, :]
    df[!, :day] = Date.(df[!, :timestamp])
    
    # Filter to allowed date range
    df = filter(row -> row.day <= max_end_date, df)
    
    if nrow(df) == 0
        return DataFrame(day=Date[], daily_score=Float64[])
    end
    
    # Get interval statistics for time conversion
    stats = get_interval_statistics(ts_data)
    interval_minutes = stats.representative_interval.value
    
    # Calculate contribution per row (hours contributed × weight factor)
    hours_per_point = interval_minutes / 60.0
    df[!, :contributed_score] = map(ws_val -> ismissing(ws_val) ? 0.0 : (hours_per_point * weight_factor), df[!, ws_column])
    
    # Group by day and sum contributions
    daily_df = combine(groupby(df, :day), :contributed_score => sum => :daily_score)
    
    # Cap daily scores at 24 hours worth of contribution (24 × weight_factor)
    max_daily_score = 24.0 * weight_factor
    daily_df[!, :daily_score] = min.(daily_df[!, :daily_score], max_daily_score)
    
    return daily_df
end

"""
    calculate_daily_coverage_scores(
        reconstruct_single_ts::TimeSeriesData,
        reconstruct_cross_ts::TimeSeriesData, 
        max_end_time::DateTime,
        single_weight::Float64 = 1.0,
        cross_weight::Float64 = 0.5
    )::Vector{DailyScore}

Calculate daily coverage scores using efficient vectorized operations.
Much faster than the previous day-by-day iteration approach.

# Arguments
- `reconstruct_single_ts::TimeSeriesData`: Single mast reconstruction data
- `reconstruct_cross_ts::TimeSeriesData`: Cross mast reconstruction data  
- `max_end_time::DateTime`: Maximum allowed end time
- `single_weight::Float64`: Weight for single reconstruction score (default: 1.0)
- `cross_weight::Float64`: Weight for cross reconstruction score (default: 0.5)

# Returns
- `Vector{DailyScore}`: Array of daily scores sorted by date
"""
function calculate_daily_coverage_scores(
    reconstruct_single_ts::TimeSeriesData,
    reconstruct_cross_ts::TimeSeriesData,
    max_end_time::DateTime,
    single_weight::Float64 = 1.0,
    cross_weight::Float64 = 0.5
)::Vector{DailyScore}
    
    # Get highest wind speed columns
    single_ws_col = get_highest_windspeed_column(reconstruct_single_ts)
    cross_ws_col = get_highest_windspeed_column(reconstruct_cross_ts)
    
    max_date = Date(max_end_time)
    
    # Calculate daily scores for each dataset using vectorized approach
    single_daily_df = calculate_dataset_daily_scores(reconstruct_single_ts, single_ws_col, single_weight, max_date)
    cross_daily_df = calculate_dataset_daily_scores(reconstruct_cross_ts, cross_ws_col, cross_weight, max_date)
    
    # Rename columns to be explicit before joining
    rename!(single_daily_df, :daily_score => :single_score)
    rename!(cross_daily_df, :daily_score => :cross_score)
    
    # Full outer join on day
    combined_df = outerjoin(single_daily_df, cross_daily_df, on=:day)
    
    # Calculate total scores (coalesce handles missing values)
    combined_df[!, :total_score] = coalesce.(combined_df[!, :single_score], 0.0) + 
                                   coalesce.(combined_df[!, :cross_score], 0.0)
    
    # Convert to normalized scores (0.0 to 1.0) and create DailyScore structs
    daily_scores = map(eachrow(combined_df)) do row
        single_normalized = coalesce(row.single_score, 0.0) / single_weight
        cross_normalized = coalesce(row.cross_score, 0.0) / cross_weight
        total_normalized = single_normalized + cross_normalized
        
        DailyScore(row.day, single_normalized, cross_normalized, total_normalized)
    end
    
    # Sort by date
    sort!(daily_scores, by = ds -> ds.date)
    
    return daily_scores
end

"""
    find_optimal_year_range(
        daily_scores::Vector{DailyScore},
        earliest_start_date::Date,
        latest_end_date::Date
    )::TimeRange

Find the optimal 1-year period within the specified date range using efficient vector operations.
Creates a complete vector of all days with zero scores for missing days, then uses array slicing
to find the best 365-day period.

# Arguments
- `daily_scores::Vector{DailyScore}`: Array of actual daily scores
- `earliest_start_date::Date`: Earliest possible start date for measurement period
- `latest_end_date::Date`: Latest possible end date (considering meso/cross data constraints)

# Returns
- `TimeRange`: Optimal time range aligned to month boundaries

# Throws  
- `ErrorException`: If date range is insufficient for yearly analysis
"""
function find_optimal_year_range(
    daily_scores::Vector{DailyScore},
    earliest_start_date::Date,
    latest_end_date::Date
)::TimeRange
    # Check if we have enough date range for a full year
    total_span_days = (latest_end_date - earliest_start_date).value + 1
    
    if total_span_days < 365
        error("Date range is too short for yearly analysis. Need at least 365 days, got $total_span_days days")
    end
    
    # Create vector with all dates and zero scores
    score_vector = map(d -> DailyScore(d, 0.0, 0.0, 0.0), collect(earliest_start_date:Day(1):latest_end_date))
    
    # Create HashMap for fast date-to-index lookup
    date_to_idx = Dict(score_vector[i].date => i for i in eachindex(score_vector))
    
    # Fill in actual scores where we have data
    for ds in daily_scores
        if haskey(date_to_idx, ds.date)
            idx = date_to_idx[ds.date]
            score_vector[idx] = ds
        end
    end
    
    # Find best 365-day slice using efficient array operations
    best_score = 0.0
    best_start_idx = 1
    
    for start_idx in 1:(length(score_vector) - 364)
        period_score = sum(score_vector[i].total_score for i in start_idx:start_idx+364)
        if period_score > best_score
            best_score = period_score
            best_start_idx = start_idx
        end
    end
    
    # Calculate optimal period dates
    start_date = score_vector[best_start_idx].date
    end_date = score_vector[best_start_idx + 364].date

    # Align start to month boundary for cleaner periods
    aligned_start = Date(year(start_date), month(start_date), 1)

    # Convert to DateTime and calculate exact 1-year period
    start_datetime = DateTime(aligned_start)
    end_datetime = start_datetime + Year(1) - Second(1)

    return TimeRange(start_datetime, end_datetime)
end

"""
    calculate_optimal_measurement_period(
        reconstruct_single_ts::TimeSeriesData,
        reconstruct_cross_ts::TimeSeriesData,
        meso_ts::TimeSeriesData
    )::TimeRange

Calculate the optimal measurement period based on data coverage quality across multiple datasets.

This function analyzes the completeness of reconstruct-single and reconstruct-cross data 
to find the 365-day period with the best overall data coverage, while respecting 
mesoscale data boundaries.

# Arguments
- `reconstruct_single_ts::TimeSeriesData`: Single mast reconstruction time series
- `reconstruct_cross_ts::TimeSeriesData`: Cross mast reconstruction time series  
- `meso_ts::TimeSeriesData`: Mesoscale time series data

# Returns
- `TimeRange`: Optimal measurement period aligned to month boundaries

# Algorithm
1. Calculate maximum allowed end time from mesoscale data
2. Score each day based on data completeness (single_weight=1.0, cross_weight=0.5)
3. Use sliding 365-day window to find period with maximum total score
4. Return month-aligned time range for clean period boundaries
"""
function calculate_optimal_measurement_period(
    reconstruct_single_ts::TimeSeriesData,
    reconstruct_cross_ts::TimeSeriesData,
    meso_ts::TimeSeriesData
)::TimeRange
    
    # Step 1: Calculate boundary constraints
    max_end_time = calculate_max_allowed_end_time(meso_ts)
    latest_end_date = Date(max_end_time)
    
    # Get cross data boundaries
    cross_timestamps = filter(!ismissing, reconstruct_cross_ts.df.timestamp)
    start_of_cross_data = Date(minimum(cross_timestamps))
    end_of_cross_data = Date(maximum(cross_timestamps))
    
    # Calculate earliest start date based on constraints
    earliest_start_date = min(
        latest_end_date - Year(1),           # Can't start later than 1 year before end
        start_of_cross_data,                 # Can't start before cross data begins
        end_of_cross_data - Day(364)         # Need at least 365 days of cross data
    )
    
    # Step 2: Calculate daily coverage scores
    daily_scores = calculate_daily_coverage_scores(
        reconstruct_single_ts,
        reconstruct_cross_ts,
        DateTime(year(latest_end_date), month(latest_end_date), day(latest_end_date), 23, 59, 59)  # Convert back to DateTime for compatibility
    )
    
    # Step 3: Find optimal year-long period within constraints
    optimal_range = find_optimal_year_range(daily_scores, earliest_start_date, latest_end_date)
    
    return optimal_range
end

end # module MeasurementPeriodCalculator