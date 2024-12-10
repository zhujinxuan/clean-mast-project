module ProcessData

using YAML
using DataFrames
using Dates

using CleanMastProject.Types.ReconstructSingleMast: ReconstructedSuccess, ReconstructedFailure
using CleanMastProject.Types.MastTimeSeries: TimeSeriesData
using CleanMastProject.Types.CleanMastConfig: ProjectConfig

using ..WindSpeedTraining
using ..DirectionTraining

"""
Reconstruct missing wind measurements in mast data
"""
function reconstruct_measurements(
    config::ProjectConfig,
    data::TimeSeriesData
)::Tuple{Vector{ReconstructedSuccess}, Vector{ReconstructedFailure}}
    speed_successes, speed_failures = reconstruct_wind_speeds(data)
    direction_successes, direction_failures = reconstruct_wind_directions(data)
    
    return vcat(speed_successes, direction_successes),
           vcat(speed_failures, direction_failures)
end

"""
Apply reconstruction to data.df and write results to single-reconstruction.yaml
"""
function process_data!(
    config::ProjectConfig,
    data::TimeSeriesData
)
    # Apply reconstruction
    successes, failures = reconstruct_measurements(config, data)

    # Group reconstructed values by column
    by_column = Dict{Symbol, Vector{Tuple{DateTime, Float64}}}()
    for success in successes
        push!(get!(by_column, success.columnName, Tuple{DateTime, Float64}[]), 
              (success.timestamp, success.value))
    end

    # Update data.df column by column
    for (col, time_values) in by_column
        times = first.(time_values)
        values = last.(time_values)
        data.df[in.(data.df.timestamp, Ref(times)), col] .= values
    end

    # Prepare data for YAML export
    result = Dict(
        "successes" => [Dict("timestamp" => s.timestamp, "columnName" => s.columnName, "value" => s.value) for s in successes],
        "failures" => [Dict("timestamp" => f.timestamp, "columnName" => f.columnName, "reason" => f.reason) for f in failures]
    )

    # Write results to single-reconstruction.yaml
    open("single-reconstruction.yaml", "w") do io
        YAML.write(io, result)
    end
end

export reconstruct_measurements, process_data!

end # module 