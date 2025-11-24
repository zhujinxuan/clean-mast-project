module MastPeriodAlignment

using Dates
using DataFrames
using Clustering
using ...Types.MastTimeSeries: TimeSeriesData, TimeRange
using ...TimeSeriesProcessing.MeasurementPeriodCalculator:
    calculate_max_allowed_end_time,
    get_highest_windspeed_column,
    calculate_dataset_daily_scores
using ...TimeSeriesProcessing.IntervalDetection: get_interval_statistics

export calculate_pairwise_overlap,
    calculate_pairwise_intersection_days,
    calculate_relative_overlap_matrix,
    calculate_absolute_overlap_matrix,
    cluster_masts_by_overlap,
    determine_target_period_years,
    calculate_union_time_range,
    calculate_cluster_optimal_period

"""
    extract_valid_timestamps(ts::TimeSeriesData)::Set{DateTime}

Extract valid timestamps from timeseries data.

Uses the highest wind speed sensor and filters out missing values.

# Arguments
- `ts::TimeSeriesData`: Timeseries data

# Returns
- `Set{DateTime}`: Set of valid timestamps (non-missing for highest wind speed sensor)
"""
function extract_valid_timestamps(ts::TimeSeriesData)::Set{DateTime}
    # Get highest wind speed column
    ws_col = get_highest_windspeed_column(ts)

    # Filter to non-missing timestamps for this sensor
    valid_mask = .!ismissing.(ts.df[:, ws_col])
    valid_timestamps = ts.df[valid_mask, :timestamp]

    # Filter out missing timestamps themselves
    valid_timestamps = filter(!ismissing, valid_timestamps)

    return Set(valid_timestamps)
end

"""
    calculate_pairwise_intersection_days(
        valid_timestamps::Dict{String, Set{DateTime}},
        intervals::Dict{String, Float64},
        mast_names::Vector{String}
    )::Tuple{Matrix{Float64}, Vector{Float64}}

Calculate pairwise intersection matrix in days and individual period lengths.

# Arguments
- `valid_timestamps::Dict{String, Set{DateTime}}`: Valid timestamps for each mast
- `intervals::Dict{String, Float64}`: Representative interval in hours for each mast
- `mast_names::Vector{String}`: Sorted list of mast names (determines matrix indices)

# Returns
- `Tuple{Matrix{Float64}, Vector{Float64}}`:
  - Symmetric intersection matrix in days [i,j] = intersection between mast i and j
  - Vector of period lengths in days [i] = total period for mast i
"""
function calculate_pairwise_intersection_days(
    valid_timestamps::Dict{String, Set{DateTime}},
    intervals::Dict{String, Float64},
    mast_names::Vector{String}
)::Tuple{Matrix{Float64}, Vector{Float64}}
    n = length(mast_names)
    intersection_matrix = zeros(n, n)
    period_days = zeros(n)

    # Calculate individual period lengths
    for i in 1:n
        mast_i = mast_names[i]
        period_i_count = length(valid_timestamps[mast_i])
        period_days[i] = (period_i_count * intervals[mast_i]) / 24.0

        # Self-intersection equals full period
        intersection_matrix[i, i] = period_days[i]
    end

    # Calculate pairwise intersections
    for i in 1:n
        for j in (i+1):n
            mast_i = mast_names[i]
            mast_j = mast_names[j]

            # Calculate Set intersection of timestamps
            intersection_timestamps = intersect(valid_timestamps[mast_i], valid_timestamps[mast_j])
            intersection_count = length(intersection_timestamps)

            # Use average interval to convert count to days
            avg_interval_hours = (intervals[mast_i] + intervals[mast_j]) / 2.0
            intersection_days = (intersection_count * avg_interval_hours) / 24.0

            # Symmetric matrix
            intersection_matrix[i, j] = intersection_days
            intersection_matrix[j, i] = intersection_days
        end
    end

    return (intersection_matrix, period_days)
end

"""
    calculate_relative_overlap_matrix(
        intersection_days::Matrix{Float64},
        period_days::Vector{Float64}
    )::Matrix{Float64}

Calculate relative overlap matrix: intersection / min(period_i, period_j)

# Arguments
- `intersection_days::Matrix{Float64}`: Pairwise intersection in days [i,j]
- `period_days::Vector{Float64}`: Individual period lengths in days [i]

# Returns
- `Matrix{Float64}`: Symmetric matrix where [i,j] = intersection_days[i,j] / min(period_days[i], period_days[j])
"""
function calculate_relative_overlap_matrix(
    intersection_days::Matrix{Float64},
    period_days::Vector{Float64}
)::Matrix{Float64}
    n = length(period_days)
    relative_matrix = zeros(n, n)

    for i in 1:n
        relative_matrix[i, i] = 1.0  # Self-overlap is always 100%

        for j in (i+1):n
            min_period = min(period_days[i], period_days[j])

            if min_period > 0
                relative_overlap = intersection_days[i, j] / min_period
                relative_matrix[i, j] = relative_overlap
                relative_matrix[j, i] = relative_overlap  # Symmetric
            end
        end
    end

    return relative_matrix
end

"""
    calculate_absolute_overlap_matrix(
        intersection_days::Matrix{Float64},
        threshold_period::Int
    )::Matrix{Float64}

Calculate absolute overlap matrix: intersection / threshold_period

# Arguments
- `intersection_days::Matrix{Float64}`: Pairwise intersection in days [i,j]
- `threshold_period::Int`: Threshold period in days (default: 120)

# Returns
- `Matrix{Float64}`: Symmetric matrix where [i,j] = intersection_days[i,j] / threshold_period
"""
function calculate_absolute_overlap_matrix(
    intersection_days::Matrix{Float64},
    threshold_period::Int
)::Matrix{Float64}
    # Element-wise division
    return intersection_days ./ threshold_period
end

"""
    calculate_pairwise_overlap(
        mast_timeseries::Dict{String, TimeSeriesData},
        threshold_period::Int
    )::Matrix{Float64}

Calculate pairwise overlap matrix using dual-criterion formula.

Uses Set intersection on valid timestamps (non-missing for highest wind speed sensor),
then converts to days using representative interval.

# Arguments
- `mast_timeseries::Dict{String, TimeSeriesData}`: Timeseries data for each mast
- `threshold_period::Int`: Minimum intersection days for absolute criterion (default: 120)

# Returns
- `Matrix{Float64}`: Symmetric overlap matrix where overlap[i,j] = max(relative, absolute)

# Algorithm
1. Extract valid timestamps for each mast (highest wind speed sensor, skip missing)
2. Calculate pairwise intersection matrix in days (once!)
3. Calculate relative overlap matrix: intersection / min(period_i, period_j)
4. Calculate absolute overlap matrix: intersection / threshold_period
5. Combine with element-wise max: overlap = max.(relative, absolute)
"""
function calculate_pairwise_overlap(
    mast_timeseries::Dict{String, TimeSeriesData},
    threshold_period::Int
)::Matrix{Float64}
    mast_names = sort(collect(keys(mast_timeseries)))

    # Step 1: Extract valid timestamps for each mast
    valid_timestamps = Dict{String, Set{DateTime}}()
    intervals = Dict{String, Float64}()

    for mast_name in mast_names
        ts = mast_timeseries[mast_name]
        valid_timestamps[mast_name] = extract_valid_timestamps(ts)

        # Get representative interval in hours
        stats = get_interval_statistics(ts)
        interval_ms = Dates.value(Millisecond(stats.representative_interval))  # Convert to milliseconds
        intervals[mast_name] = interval_ms / (1000.0 * 3600.0)  # ms to hours
    end

    # Step 2: Calculate pairwise intersection matrix (once!)
    intersection_days, period_days = calculate_pairwise_intersection_days(valid_timestamps, intervals, mast_names)

    # Step 3: Calculate relative overlap matrix
    relative_matrix = calculate_relative_overlap_matrix(intersection_days, period_days)

    # Step 4: Calculate absolute overlap matrix
    absolute_matrix = calculate_absolute_overlap_matrix(intersection_days, threshold_period)

    # Step 5: Combine with element-wise max
    overlap_matrix = max.(relative_matrix, absolute_matrix)

    return overlap_matrix
end

"""
    cluster_masts_by_overlap(
        mast_names::Vector{String},
        overlap_matrix::Matrix{Float64},
        cluster_threshold::Float64
    )::Dict{Int, Vector{String}}

Perform hierarchical clustering with complete linkage on overlap matrix.

# Arguments
- `mast_names::Vector{String}`: Sorted list of mast names
- `overlap_matrix::Matrix{Float64}`: Pairwise overlap matrix
- `cluster_threshold::Float64`: Minimum overlap threshold (default: 0.8)

# Returns
- `Dict{Int, Vector{String}}`: Mapping from cluster ID to list of mast names
"""
function cluster_masts_by_overlap(
    mast_names::Vector{String},
    overlap_matrix::Matrix{Float64},
    cluster_threshold::Float64
)::Dict{Int, Vector{String}}
    # Convert overlap to distance
    distance_matrix = 1 .- overlap_matrix

    # Hierarchical clustering with complete linkage
    hc = hclust(distance_matrix, linkage=:complete)

    # Cut dendrogram at threshold height
    cluster_assignments = cutree(hc; h=1.0 - cluster_threshold)

    # Group masts by cluster ID
    clusters = Dict{Int, Vector{String}}()
    for (idx, cluster_id) in enumerate(cluster_assignments)
        if !haskey(clusters, cluster_id)
            clusters[cluster_id] = String[]
        end
        push!(clusters[cluster_id], mast_names[idx])
    end

    return clusters
end

"""
    determine_target_period_years(union_days::Int)::Int

Determine target period in years based on union period length.

Uses floor with 0.8 threshold:
- union_years = union_days / 365.0
- If fractional part < 0.8: floor (round down)
- If fractional part >= 0.8: ceil (round up)
- Minimum 1 year

Target period can exceed union period because mesoscale data can extend
beyond the mast measurement period.

# Examples
- 400 days (1.1 years) → 1 year (0.1 < 0.8)
- 550 days (1.5 years) → 1 year (0.5 < 0.8)
- 600 days (1.6 years) → 1 year (0.6 < 0.8)
- 657 days (1.8 years) → 2 years (0.8 >= 0.8)
- 850 days (2.3 years) → 2 years (0.3 < 0.8)
- 950 days (2.6 years) → 2 years (0.6 < 0.8)
- 1021 days (2.8 years) → 3 years (0.8 >= 0.8)
- 1303 days (3.57 years) → 3 years (0.57 < 0.8)
"""
function determine_target_period_years(union_days::Int)::Int
    union_years = union_days / 365.0
    fractional_part = union_years - floor(union_years)

    if fractional_part < 0.8
        target_years = floor(Int, union_years)
    else
        target_years = ceil(Int, union_years)
    end

    return max(1, target_years)
end

"""
    calculate_union_time_range(
        mast_timeseries::Dict{String, TimeSeriesData}
    )::Tuple{Date, Date}

Calculate union time range (earliest start to latest end) across all masts.

# Arguments
- `mast_timeseries::Dict{String, TimeSeriesData}`: Loaded timeseries for each mast

# Returns
- `Tuple{Date, Date}`: (union_start, union_end)
"""
function calculate_union_time_range(
    mast_timeseries::Dict{String, TimeSeriesData}
)::Tuple{Date, Date}
    start_dates = Date[]
    end_dates = Date[]

    for (_, ts_data) in mast_timeseries
        valid_times = filter(!ismissing, ts_data.df.timestamp)
        if !isempty(valid_times)
            push!(start_dates, Date(minimum(valid_times)))
            push!(end_dates, Date(maximum(valid_times)))
        end
    end

    if isempty(start_dates)
        error("No valid timestamps found in cluster timeseries data")
    end

    union_start = minimum(start_dates)
    union_end = maximum(end_dates)

    return (union_start, union_end)
end

"""
    score_cluster_window(
        mast_timeseries::Dict{String, TimeSeriesData},
        window_start::Date,
        window_end::Date
    )::Float64

Calculate average coverage score for a time window across all masts in cluster.

# Arguments
- `mast_timeseries::Dict{String, TimeSeriesData}`: Loaded timeseries for each mast
- `window_start::Date`: Window start date
- `window_end::Date`: Window end date

# Returns
- `Float64`: Average coverage score across all masts
"""
function score_cluster_window(
    mast_timeseries::Dict{String, TimeSeriesData},
    window_start::Date,
    window_end::Date
)::Float64
    coverages = Float64[]

    for (_, ts_data) in mast_timeseries
        # Get highest wind speed column
        ws_column = get_highest_windspeed_column(ts_data)

        # Calculate daily scores for this mast
        daily_scores = calculate_dataset_daily_scores(ts_data, ws_column, 1.0, window_end)

        # Filter to window range
        window_scores = filter(row -> window_start <= row.day <= window_end, daily_scores)

        # Calculate coverage (sum of daily scores / expected hours)
        if nrow(window_scores) > 0
            expected_hours = (window_end - window_start).value * 24.0
            actual_coverage = sum(window_scores.daily_score) / expected_hours
            push!(coverages, actual_coverage)
        else
            push!(coverages, 0.0)
        end
    end

    return isempty(coverages) ? 0.0 : sum(coverages) / length(coverages)
end

"""
    calculate_cluster_optimal_period(
        cluster_mast_names::Vector{String},
        mast_timeseries::Dict{String, TimeSeriesData},
        meso_ts::TimeSeriesData
    )::TimeRange

Calculate optimal period for a cluster of masts.

# Algorithm
1. Calculate union time range across all cluster masts
2. Determine target period length (1, 2, 3+ years) based on union length
3. Find optimal N-year window with highest average coverage across all masts
4. Return month-aligned period

# Arguments
- `cluster_mast_names::Vector{String}`: Names of masts in this cluster
- `mast_timeseries::Dict{String, TimeSeriesData}`: Loaded timeseries for all masts
- `meso_ts::TimeSeriesData`: Mesoscale data for boundary constraints

# Returns
- `TimeRange`: Optimal period for the cluster
"""
function calculate_cluster_optimal_period(
    cluster_mast_names::Vector{String},
    mast_timeseries::Dict{String, TimeSeriesData},
    meso_ts::TimeSeriesData
)::TimeRange
    # Get timeseries for this cluster
    cluster_ts = Dict(name => mast_timeseries[name] for name in cluster_mast_names)

    # Step 1: Calculate union time range (for determining target period)
    union_start, union_end = calculate_union_time_range(cluster_ts)
    union_days = Dates.value(union_end - union_start) + 1

    # Step 2: Determine target period in years
    target_years = determine_target_period_years(union_days)

    # Step 3: Calculate meso boundary constraints
    # Search within meso boundaries (can extend beyond mast union)
    valid_meso_times = filter(!ismissing, meso_ts.df.timestamp)
    if isempty(valid_meso_times)
        error("Mesoscale data has no valid timestamps")
    end
    meso_start_time = minimum(valid_meso_times)
    meso_end_time = calculate_max_allowed_end_time(meso_ts)

    search_start = Date(meso_start_time)
    search_end = Date(meso_end_time)

    # Verify we have enough meso data for target period
    meso_span_days = Dates.value(search_end - search_start) + 1
    if meso_span_days < target_years * 365
        error("Meso data span ($meso_span_days days) is shorter than target period ($(target_years * 365) days)")
    end

    # Step 4: Find optimal window (month-aligned starts only)
    best_start = search_start
    best_score = -Inf

    current_date = Date(year(search_start), month(search_start), 1)
    while true
        # Calculate window end using Year for proper leap year handling
        window_start_datetime = DateTime(current_date)
        window_end_datetime = window_start_datetime + Year(target_years) - Second(1)
        window_end = Date(window_end_datetime)

        # Stop if window extends beyond meso boundaries
        if window_end > search_end
            break
        end

        # Score this window
        score = score_cluster_window(cluster_ts, current_date, window_end)

        if score > best_score
            best_score = score
            best_start = current_date
        end

        # Move to next month
        if month(current_date) == 12
            current_date = Date(year(current_date) + 1, 1, 1)
        else
            current_date = Date(year(current_date), month(current_date) + 1, 1)
        end
    end

    # Step 5: Return month-aligned period using Year() for proper leap year handling
    start_datetime = DateTime(best_start)
    end_datetime = start_datetime + Year(target_years) - Second(1)

    return TimeRange(start_datetime, end_datetime)
end

end # module MastPeriodAlignment
