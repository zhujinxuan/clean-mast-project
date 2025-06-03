module Turbulence

using DataFrames
using CSV
using Gadfly
using Statistics
using Dates

import ...Types.MastTimeSeries: TimeSeriesData, SensorColumn, find_nearest_height_sensor
import ...Types.AnalyzeConfiguration: AnalyzeConfig, MastAnalyzeConfig, get_output_path
import ...Types.Sector: DIRECTION_16_SECTORS, get_direction_sector
import ...Types.TurbulenceIntensity: TurbulenceSectorStats, TurbulenceResults

const DEFAULT_WIND_SPEED_BINS = collect(0.0:1.0:28.0)

"""
Find wind speed (avg, std) and direction sensors at the target height
"""
function find_ti_sensors(ts::TimeSeriesData, target_height::Float64)::Tuple{Union{SensorColumn,Nothing}, Union{SensorColumn,Nothing}, Union{SensorColumn,Nothing}}
    # Find average wind speed sensor
    ws_avg = find_nearest_height_sensor(target_height, ts.sensors, "WindSpeed", "avg")
    # Find standard deviation wind speed sensor at the same height as avg
    ws_sd = ws_avg === nothing ? nothing : 
        find_nearest_height_sensor(ws_avg.height, ts.sensors, "WindSpeed", "sd")
    # Find wind direction sensor
    wd = find_nearest_height_sensor(target_height, ts.sensors, "WindDirection", "avg")
    
    return ws_avg, ws_sd, wd
end

"""
Calculate turbulence intensity for each time step
"""
function calculate_ti_series(
    df::DataFrame,
    ws_col::Symbol,
    sd_col::Symbol,
    wd_col::Symbol
)::DataFrame
    # Create result DataFrame with all necessary columns
    result = DataFrame(
        ws_avg = df[!, ws_col],
        ws_sd = df[!, sd_col],
        wd = df[!, wd_col]
    )
    
    # Calculate TI, ensuring minimum wind speed of 1.0 m/s
    result.ti = result.ws_sd ./ map(ws -> max(ws, 1.0), result.ws_avg)
    
    # Add sector for each direction, propagating missing values
    result.sector = map(result.wd) do wd
        ismissing(wd) ? missing : get_direction_sector(wd, DIRECTION_16_SECTORS).name
    end
    
    return result
end

"""
Calculate sector statistics for turbulence intensity
"""
function calculate_sector_stats(ti_df::DataFrame)::TurbulenceSectorStats
    # Filter out rows with missing sectors or missing TI
    valid_data = filter(row -> !ismissing(row.sector) && !ismissing(row.ti), ti_df)
    # Calculate sector statistics
    sector_stats = combine(
        groupby(valid_data, :sector),
        :ws_avg => mean => :mean_speed,
        :ti => mean => :ti,
        :ti => std => :std,
        nrow => :occurrence
    )
    
    # Calculate overall statistics
    mean_ti = mean(skipmissing(ti_df.ti))
    std_ti = std(skipmissing(ti_df.ti))
    representative_ti = mean_ti + std_ti
    
    return TurbulenceSectorStats(sector_stats, mean_ti, std_ti, representative_ti)
end

"""
Calculate turbulence intensity matrix for Meteodyn WT
"""
function calculate_ti_matrix(
    ti_df::DataFrame,
    wind_speed_bins::Vector{Float64},
    mean_ti::Float64
)::DataFrame
    # Create base DataFrame with speed bins
    result = DataFrame(
        v_min = wind_speed_bins[1:end-1],
        v_max = wind_speed_bins[2:end]
    )
    
    # Initialize sector columns with mean TI
    for sector in DIRECTION_16_SECTORS
        result[!, sector.name] = fill(mean_ti, length(wind_speed_bins)-1)
    end
    
    # Calculate TI for each bin and sector
    for (i, (min_speed, max_speed)) in enumerate(zip(wind_speed_bins[1:end-1], wind_speed_bins[2:end]))
        # Get data for this speed bin, skipping missing values
        speed_bin_data = filter(row -> !ismissing(row.ws_avg) && min_speed ≤ row.ws_avg < max_speed, ti_df)
        
        # Calculate TI for each sector with enough data
        for sector in DIRECTION_16_SECTORS
            # Filter for this sector, skipping missing sectors
            sector_data = filter(row -> !ismissing(row.sector) && row.sector == sector.name, speed_bin_data)
            
            if nrow(sector_data) ≥ 5  # Minimum sample size for reliable statistics
                result[i, sector.name] = mean(skipmissing(sector_data.ti))
            end
        end
    end
    
    return result
end

"""
Calculate turbulence intensity statistics by wind speed bin
"""
function calculate_ti_by_wind_speed(
    ti_df::DataFrame,
    wind_speed_bins::Vector{Float64}
)::DataFrame
    # Create empty result DataFrame
    result = DataFrame(
        wind_speed_min = Float64[],
        wind_speed_max = Float64[],
        mean_ti = Float64[],
        std_ti = Float64[],
        occurrence = Int[],
        representative_ti = Float64[]
    )
    
    # Calculate stats for each wind speed bin
    for (i, (min_speed, max_speed)) in enumerate(zip(wind_speed_bins[1:end-1], wind_speed_bins[2:end]))
        # Filter data for this wind speed bin
        bin_data = filter(row -> !ismissing(row.ws_avg) && min_speed ≤ row.ws_avg < max_speed, ti_df)
        
        # Skip bins with no data
        if nrow(bin_data) == 0
            continue
        end
        
        # Calculate statistics
        bin_mean_ti = mean(skipmissing(bin_data.ti))
        bin_std_ti = nrow(bin_data) > 1 ? std(skipmissing(bin_data.ti)) : 0.0
        bin_representative_ti = bin_mean_ti + bin_std_ti
        
        # Add row to results
        push!(result, (
            min_speed,
            max_speed,
            bin_mean_ti,
            bin_std_ti,
            nrow(bin_data),
            bin_representative_ti
        ))
    end
    
    return result
end

"""
Calculate sector statistics for turbulence intensity with optional wind speed filtering
"""
function calculate_filtered_sector_stats(
    ti_df::DataFrame;
    min_ws::Union{Nothing, Float64} = nothing,
    max_ws::Union{Nothing, Float64} = nothing
)::TurbulenceSectorStats
    # Apply wind speed filtering if requested
    filtered_df = ti_df
    if !isnothing(min_ws) || !isnothing(max_ws)
        filtered_df = filter(row -> begin
            # Skip missing wind speeds
            ismissing(row.ws_avg) && return false
            
            # Apply min filter if specified
            if !isnothing(min_ws) && row.ws_avg < min_ws
                return false
            end
            
            # Apply max filter if specified
            if !isnothing(max_ws) && row.ws_avg > max_ws
                return false
            end
            
            return true
        end, ti_df)
    end
    
    # Now use the standard sector stats calculation on filtered data
    return calculate_sector_stats(filtered_df)
end

"""
Process turbulence intensity for a single height
"""
function process_turbulence_intensity(
    ts::TimeSeriesData,
    target_height::Float64,
    wind_speed_bins::Vector{Float64}
)::TurbulenceResults
    # Find required sensors
    ws_avg, ws_sd, wd = find_ti_sensors(ts, target_height)
    
    isnothing(ws_avg) && error("No wind speed sensor found near height $(target_height)m")
    isnothing(ws_sd) && error("No wind speed standard deviation sensor found at height $(ws_avg.height)m")
    isnothing(wd) && error("No wind direction sensor found near height $(target_height)m")
    
    # Calculate TI time series
    ti_df = calculate_ti_series(ts.df, ws_avg.columnName, ws_sd.columnName, wd.columnName)
    
    # Calculate sector statistics
    sector_stats = calculate_sector_stats(ti_df)
    
    # Calculate TI matrix for Meteodyn WT
    ti_matrix = calculate_ti_matrix(ti_df, wind_speed_bins, sector_stats.mean_ti)
    
    return TurbulenceResults(ti_df, sector_stats, ti_matrix)
end

"""
Save Meteodyn WT turbulence intensity file
"""
function save_meteodyn_ti(output_dir::String, ti_matrix::DataFrame, height::Float64)
    meteodyn_path = joinpath(output_dir, "meteodyn_ti_$(height)m.txt")
    
    open(meteodyn_path, "w") do io
        println(io, nrow(ti_matrix))
        for row in eachrow(ti_matrix)
            values = [row.v_max]
            append!(values, [row[sector.name] for sector in DIRECTION_16_SECTORS])
            println(io, join(values, "\t"))
        end
    end
    
    @info "Saved Meteodyn WT file: $meteodyn_path"
end

"""
    analyze_turbulence_intensity(config::AnalyzeConfig)

Analyze turbulence intensity for all masts and heights in the configuration.
"""
function analyze_turbulence_intensity(config::AnalyzeConfig)
    results = Dict{String, Any}()
    
    for mast in config.masts
        output_dir = get_output_path(config, mast.name, "turbulence")
        
        # Find all unique heights with both wind speed avg and sd sensors
        ws_avg_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "avg", 
                               mast.timeSeriesData.sensors)
        ws_sd_sensors = filter(s -> s.sensorType == "WindSpeed" && s.statType == "sd", 
                              mast.timeSeriesData.sensors)
        
        # Get heights that have both avg and sd sensors
        avg_heights = Set([s.height for s in ws_avg_sensors])
        sd_heights = Set([s.height for s in ws_sd_sensors])
        valid_heights = sort(collect(intersect(avg_heights, sd_heights)))
        
        if isempty(valid_heights)
            @warn "No heights with both wind speed avg and sd sensors for mast $(mast.name)"
            continue
        end
        
        mast_results = Dict{String, Any}()
        
        for height in valid_heights
            @info "Processing turbulence intensity for mast $(mast.name) at $(height)m"

            # Process turbulence intensity
            ti_results = process_turbulence_intensity(
                mast.timeSeriesData,
                height,
                DEFAULT_WIND_SPEED_BINS
            )

            # Save sector statistics
            ti_stats_df = select(
                ti_results.sector_stats.sector_stats,
                :sector,
                :mean_speed => :mean_speed,
                :ti => :mean_ti,
                :std => :ti_std,
                :occurrence
            )
            CSV.write(joinpath(output_dir, "turbulence_intensity_$(height)m.csv"), ti_stats_df)

            # Save TI by wind speed
            ti_by_ws = calculate_ti_by_wind_speed(ti_results.time_series, DEFAULT_WIND_SPEED_BINS)
            CSV.write(joinpath(output_dir, "ti_by_wind_speed_$(height)m.csv"), ti_by_ws)

            # Calculate TI for different wind speed ranges
            all_speeds_ti = ti_results.sector_stats.mean_ti
            all_speeds_rep_ti = ti_results.sector_stats.representative_ti
            all_speeds_std_ti = ti_results.sector_stats.std_ti

            # Wind speeds > 3 m/s
            above_3_stats = calculate_filtered_sector_stats(ti_results.time_series, min_ws=3.0)

            # Wind speeds between 14.5 and 16.5 m/s
            ws_14_5_16_5_stats = calculate_filtered_sector_stats(ti_results.time_series, min_ws=14.5, max_ws=16.5)

            # Wind speeds between 9.5 and 10.5 m/s
            ws_9_5_10_5_stats = calculate_filtered_sector_stats(ti_results.time_series, min_ws=9.5, max_ws=10.5)

            # Create report
            report_df = DataFrame(
                mast=[mast.name, mast.name, mast.name, mast.name],
                height=[height, height, height, height],
                wind_speed_range=["all", ">3 m/s", "14.5-16.5 m/s", "9.5-10.5 m/s"],
                mean_ti=[
                    all_speeds_ti,
                    above_3_stats.mean_ti,
                    ws_14_5_16_5_stats.mean_ti,
                    ws_9_5_10_5_stats.mean_ti
                ],
                representative_ti=[
                    all_speeds_rep_ti,
                    above_3_stats.representative_ti,
                    ws_14_5_16_5_stats.representative_ti,
                    ws_9_5_10_5_stats.representative_ti
                ],
                ti_std=[
                    all_speeds_std_ti,
                    above_3_stats.std_ti,
                    ws_14_5_16_5_stats.std_ti,
                    ws_9_5_10_5_stats.std_ti
                ]
            )

            CSV.write(joinpath(output_dir, "turbulence_intensity_report_$(height)m.csv"), report_df)

            # Save Meteodyn WT file
            save_meteodyn_ti(output_dir, ti_results.matrix, height)

            mast_results["$(height)m"] = ti_results

        end

        results[mast.name] = mast_results
    end

    return results
end

"""
    analyze_all_turbulence(config::AnalyzeConfig)

Run all turbulence intensity analyses for all masts in the configuration.
"""
function analyze_all_turbulence(config::AnalyzeConfig)
    return analyze_turbulence_intensity(config)
end

export analyze_turbulence_intensity, analyze_all_turbulence

end # module 