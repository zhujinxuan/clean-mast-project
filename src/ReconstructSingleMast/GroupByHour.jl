module GroupByHour

using DataFrames
using Dates
using ...Types.MastTimeSeries: TimeSeriesData

"""
    process_by_hour(data::TimeSeriesData, process_hour::Function)

Process time series data in hourly groups and collect results.

Groups the time series by hour, applies a processing function to each hour's data,
and collects all results into a single vector.

# Arguments
- `data::TimeSeriesData`: Input time series data
- `process_hour::Function`: Function with signature `TimeSeriesData -> Vector{T}`

# Returns
- `Vector{T}`: Concatenated results from all hourly groups (type inferred from process_hour)

# Example
```julia
results = process_by_hour(data, reconstruct_hourly_speeds)
```
"""
function process_by_hour(
    data::TimeSeriesData,
    process_hour::Function
)
    # Add hour column for grouping
    df_with_hour = transform(data.df, :timestamp => ByRow(ts -> floor(ts, Hour)) => :hour)

    # Group by hour
    grouped = groupby(df_with_hour, :hour)

    # Process first hour to infer result type
    if isempty(grouped)
        return []
    end

    # Process all hour groups and collect results
    all_results = []
    for hour_group in grouped
        hour_data = TimeSeriesData(
            select(hour_group, Not(:hour)),
            data.sensors
        )
        results = process_hour(hour_data)
        append!(all_results, results)
    end

    return all_results
end

export process_by_hour

end # module
