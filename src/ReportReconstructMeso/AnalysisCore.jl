"""
    AnalysisCore.jl

Core analysis functions for meso-mast reconstruction quality analysis.
Calculates RMSE and correlation between mesoscale and mast data.
"""
module AnalysisCore

using DataFrames
using Statistics
using Dates
using Logging

using ...Types.MastTimeSeries: TimeSeriesData, load_timeseries, SensorColumn
using ...TimeSeriesProcessing.Interpolation: interpolate_timeseries

export AnalyzeMesoMastResult, SensorPairMetrics, analyze_meso_mast_pair, load_all_data, get_top_wind_speed_sensors

"""
    SensorPairMetrics

Metrics for a single sensor pair (mast sensor vs meso sensor).

# Fields
- `mast_sensor::SensorColumn`: Mast sensor
- `meso_sensor::SensorColumn`: Meso sensor
- `correlation::Float64`: Pearson correlation coefficient
- `rmse::Float64`: Root mean square error
- `sample_count::Int`: Number of valid samples used
"""
struct SensorPairMetrics
    mast_sensor::SensorColumn
    meso_sensor::SensorColumn
    correlation::Float64
    rmse::Float64
    sample_count::Int
end

"""
    AnalyzeMesoMastResult

Result struct for a single meso-mast pair analysis.

# Fields
- `mast_name::String`: Name of mast
- `meso_name::String`: Name of meso source
- `sensor_metrics::Vector{SensorPairMetrics}`: Metrics for each sensor pair
- `overlap_days::Float64`: Number of overlapping days
"""
struct AnalyzeMesoMastResult
    mast_name::String
    meso_name::String
    sensor_metrics::Vector{SensorPairMetrics}
    overlap_days::Float64
end

"""
    compute_rmse(predicted::Vector, actual::Vector)::Float64

Compute root mean square error between predicted and actual values.
"""
function compute_rmse(predicted::Vector, actual::Vector)::Float64
    return sqrt(mean((predicted .- actual).^2))
end

"""
    get_sensors_by_heights(ts::TimeSeriesData, target_heights::Vector{Float64})::Vector{SensorColumn}

Get wind speed sensors (statType = avg) matching exact target heights.

# Arguments
- `ts::TimeSeriesData`: Time series data
- `target_heights::Vector{Float64}`: Heights to match

# Returns
- `Vector{SensorColumn}`: Wind speed sensors at specified heights

# Throws
- Error if any target height has no matching sensor
"""
function get_sensors_by_heights(ts::TimeSeriesData, target_heights::Vector{Float64})::Vector{SensorColumn}
    ws_sensors = filter(
        s -> s.sensorType == "WindSpeed" && s.statType == "avg",
        ts.sensors
    )

    matched_sensors = SensorColumn[]
    for target_height in target_heights
        matching = filter(s -> s.height == target_height, ws_sensors)
        if isempty(matching)
            error("No wind speed sensor found at height $(target_height)m with statType=avg")
        end
        push!(matched_sensors, first(matching))
    end

    return matched_sensors
end

"""
    analyze_sensor_pair(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData,
                       mast_sensor::SensorColumn, meso_sensor::SensorColumn)::Union{SensorPairMetrics, Nothing}

Analyze a single sensor pair and compute correlation and RMSE.
"""
function analyze_sensor_pair(
    mast_ts::TimeSeriesData,
    meso_ts::TimeSeriesData,
    mast_sensor::SensorColumn,
    meso_sensor::SensorColumn
)::Union{SensorPairMetrics, Nothing}

    mast_col = mast_sensor.columnName
    meso_col = meso_sensor.columnName

    if !hasproperty(mast_ts.df, mast_col) || !hasproperty(meso_ts.df, meso_col)
        return nothing
    end

    mast_vec = mast_ts.df[!, mast_col]
    meso_vec = meso_ts.df[!, meso_col]

    valid_mask = .!(ismissing.(mast_vec) .| ismissing.(meso_vec))
    valid_count = count(valid_mask)

    if valid_count < 10
        return nothing
    end

    mast_valid = collect(skipmissing(mast_vec[valid_mask]))
    meso_valid = collect(skipmissing(meso_vec[valid_mask]))

    correlation = cor(mast_valid, meso_valid)
    rmse = compute_rmse(meso_valid, mast_valid)

    return SensorPairMetrics(
        mast_sensor,
        meso_sensor,
        correlation,
        rmse,
        length(mast_valid)
    )
end

"""
    analyze_meso_mast_pair(mast_ts::TimeSeriesData, meso_ts::TimeSeriesData,
                          mast_name::String, meso_name::String,
                          mast_heights::Vector{Float64}, meso_heights::Vector{Float64})::AnalyzeMesoMastResult

Perform complete analysis for a single meso-mast pair.

# Arguments
- `mast_ts::TimeSeriesData`: Mast time series
- `meso_ts::TimeSeriesData`: Meso time series
- `mast_name::String`: Mast name
- `meso_name::String`: Meso name
- `mast_heights::Vector{Float64}`: Wind speed sensor heights to analyze for mast
- `meso_heights::Vector{Float64}`: Wind speed sensor heights to analyze for meso

# Returns
- `AnalyzeMesoMastResult`: Analysis result (never returns nothing, errors instead)

# Throws
- Error if insufficient overlap (<1 day)
- Error if no sensors at configured heights
- Error if all sensor pairs have insufficient data
"""
function analyze_meso_mast_pair(
    mast_ts::TimeSeriesData,
    meso_ts::TimeSeriesData,
    mast_name::String,
    meso_name::String,
    mast_heights::Vector{Float64},
    meso_heights::Vector{Float64}
)::AnalyzeMesoMastResult

    meso_ts_aligned = interpolate_timeseries(meso_ts, mast_ts.df.timestamp)

    overlap_start = max(first(mast_ts.df.timestamp), first(meso_ts_aligned.df.timestamp))
    overlap_end = min(last(mast_ts.df.timestamp), last(meso_ts_aligned.df.timestamp))
    overlap_days = (overlap_end - overlap_start).value / (1000 * 60 * 60 * 24)

    if overlap_days < 1.0
        error("Insufficient overlap for $(mast_name) ← $(meso_name): $(round(overlap_days, digits=1)) days. Need at least 1 day.")
    end

    mast_sensors = get_sensors_by_heights(mast_ts, mast_heights)
    meso_sensors = get_sensors_by_heights(meso_ts_aligned, meso_heights)

    sensor_metrics = SensorPairMetrics[]

    for mast_sensor in mast_sensors
        for meso_sensor in meso_sensors
            metrics = analyze_sensor_pair(mast_ts, meso_ts_aligned, mast_sensor, meso_sensor)
            if !isnothing(metrics)
                push!(sensor_metrics, metrics)
            end
        end
    end

    if isempty(sensor_metrics)
        error("No valid sensor pairs for $(mast_name) ← $(meso_name). All configured sensor pairs have insufficient data (<10 overlapping samples).")
    end

    best_idx = argmax([m.correlation for m in sensor_metrics])
    best_metrics = sensor_metrics[best_idx]
    @info "Analysis metrics" overlap_days=round(overlap_days, digits=1) sensor_pairs=length(sensor_metrics) best_corr=round(best_metrics.correlation, digits=3) best_rmse=round(best_metrics.rmse, digits=2)

    return AnalyzeMesoMastResult(
        mast_name,
        meso_name,
        sensor_metrics,
        overlap_days
    )
end

"""
    load_all_data(config, config_dir::String)::Tuple{Dict{String, TimeSeriesData}, Dict{String, TimeSeriesData}}

Load time series data for all masts and mesos in configuration.

# Arguments
- `config`: ReportReconstructMesoConfiguration
- `config_dir::String`: Config directory path for resolving relative paths

# Returns
- `Tuple{Dict{String, TimeSeriesData}, Dict{String, TimeSeriesData}}`: (mast_data, meso_data) dictionaries
"""
function load_all_data(config, config_dir::String)::Tuple{Dict{String, TimeSeriesData}, Dict{String, TimeSeriesData}}
    mast_data = Dict{String, TimeSeriesData}()
    meso_data = Dict{String, TimeSeriesData}()

    @info "Loading mast data" count=length(config.masts)
    for mast_config in config.masts
        @info "Loading mast" name=mast_config.name
        mast_data[mast_config.name] = load_timeseries(mast_config.input, config_dir)

        ts = mast_data[mast_config.name]
        @info "Mast loaded" name=mast_config.name records=nrow(ts.df) first_timestamp=first(ts.df.timestamp) last_timestamp=last(ts.df.timestamp)
    end

    @info "Loading meso data" count=length(config.mesos)
    for meso_config in config.mesos
        @info "Loading meso" name=meso_config.name
        meso_data[meso_config.name] = load_timeseries(meso_config.input, config_dir)

        ts = meso_data[meso_config.name]
        @info "Meso loaded" name=meso_config.name records=nrow(ts.df) first_timestamp=first(ts.df.timestamp) last_timestamp=last(ts.df.timestamp)
    end

    return mast_data, meso_data
end

end # module
