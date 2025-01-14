module TurbulenceIntensity

using DataFrames
using Statistics
using CSV
using ..Types.MastTimeSeries: TimeSeriesData, SensorColumn, find_nearest_height_sensor
using ..Types.CleanMastConfig: ProjectConfig
using ..Types.Sector: DIRECTION_SECTORS, SECTOR_DEGREES, get_direction_sector, DirectionSector

const DEFAULT_WIND_SPEED_BINS = collect(0.0:1.0:28.0)

"""
Find wind speed and direction sensors at the target height
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

# Arguments
- `df::DataFrame`: Input DataFrame with wind speed and direction data
- `ws_col::Union{String, Symbol}`: Wind speed average column name
- `sd_col::Union{String, Symbol}`: Wind speed standard deviation column name
- `wd_col::Union{String, Symbol}`: Wind direction column name

# Returns
- `DataFrame`: DataFrame with turbulence intensity calculations
"""
function calculate_ti_series(
    df::DataFrame,
    ws_col::Union{String, Symbol},
    sd_col::Union{String, Symbol},
    wd_col::Union{String, Symbol}
)::DataFrame
    # Create result DataFrame with all necessary columns
    result = DataFrame(
        ws_avg = df[!, ws_col],
        ws_sd = df[!, sd_col],
        wd = df[!, wd_col]
    )
    
    # Calculate TI, ensuring minimum wind speed of 1.0 m/s
    result.ti = result.ws_sd ./ map(ws -> max(ws, 1.0), result.ws_avg)
    
    # Add sector for each direction
    result.sector = map(wd -> get_direction_sector(wd).name, result.wd)
    
    return result
end

"""
Calculate sector statistics for turbulence intensity

# Returns
- `sector_stats::DataFrame`: Statistics for each sector
- `mean_ti::Float64`: Overall mean turbulence intensity
- `std_ti::Float64`: Overall standard deviation of turbulence intensity
- `representative_ti::Float64`: Representative turbulence intensity (mean + std)
"""
function calculate_sector_stats(ti_df::DataFrame)::Tuple{DataFrame, Float64, Float64, Float64}
    # Calculate sector statistics
    sector_stats = combine(
        groupby(ti_df, :sector),
        :ws_avg => mean => :mean_speed,
        :ti => mean => :ti,
        :ti => std => :std,
        nrow => :occurrence
    )
    
    # Calculate overall statistics
    mean_ti = mean(skipmissing(ti_df.ti))
    std_ti = std(skipmissing(ti_df.ti))
    representative_ti = mean_ti + std_ti
    
    return sector_stats, mean_ti, std_ti, representative_ti
end

"""
Calculate turbulence intensity matrix for Meteodyn WT

# Arguments
- `ti_df::DataFrame`: DataFrame with turbulence intensity time series
- `wind_speed_bins::Vector{Float64}`: Wind speed bins for matrix
- `mean_ti::Float64`: Mean TI to use for missing values

# Returns
- `DataFrame`: Matrix with columns for v_min, v_max, and each direction sector
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
    for sector in DIRECTION_SECTORS
        result[!, sector.name] = fill(mean_ti, length(wind_speed_bins)-1)
    end
    
    # Calculate TI for each bin and sector
    for (i, (min_speed, max_speed)) in enumerate(zip(wind_speed_bins[1:end-1], wind_speed_bins[2:end]))
        # Get data for this speed bin
        speed_bin_data = filter(row -> min_speed ≤ row.ws_avg < max_speed, ti_df)
        
        # Calculate TI for each sector with enough data
        for sector in DIRECTION_SECTORS
            sector_data = filter(row -> row.sector == sector.name, speed_bin_data)
            
            if nrow(sector_data) ≥ 5  # Minimum sample size for reliable statistics
                result[i, sector.name] = mean(sector_data.ti)
            end
        end
    end
    
    return result
end

"""
Save turbulence intensity results to files

# Arguments
- `config::ProjectConfig`: Project configuration
- `ti_df::DataFrame`: DataFrame with turbulence intensity time series
- `sector_stats::DataFrame`: DataFrame with sector statistics
- `mean_ti::Float64`: Overall mean TI
- `std_ti::Float64`: Overall TI standard deviation
- `representative_ti::Float64`: Representative TI (mean + std)
- `ti_matrix::DataFrame`: TI matrix for Meteodyn WT
"""
function save_results(
    config::ProjectConfig,
    ti_df::DataFrame,
    sector_stats::DataFrame,
    mean_ti::Float64,
    std_ti::Float64,
    representative_ti::Float64,
    ti_matrix::DataFrame
)::Nothing
    # Create output directory
    output_dir = joinpath(dirname(config.mast.data_path), "analysis")
    mkpath(output_dir)
    
    # Save main TI results
    CSV.write(
        joinpath(output_dir, "turbulence_intensity.csv"),
        sector_stats
    )
    
    # Save report summary
    mast_name = basename(dirname(config.mast.data_path))
    report_df = DataFrame(
        mast = [mast_name],
        mean_ti = [mean_ti],
        representative_ti = [representative_ti],
        ti_std = [std_ti]
    )
    CSV.write(
        joinpath(output_dir, "turbulence_intensity_report.csv"),
        report_df
    )
    
    # Save Meteodyn WT input file
    open(joinpath(output_dir, "meteodyn_ti.txt"), "w") do io
        println(io, length(ti_matrix.v_max))
        for row in eachrow(ti_matrix)
            values = [row.v_max]
            append!(values, [row[sector.name] for sector in DIRECTION_SECTORS])
            println(io, join(values, "\t"))
        end
    end
    
    return nothing
end

"""
Process turbulence intensity analysis

# Arguments
- `config::ProjectConfig`: Project configuration
- `ts::TimeSeriesData`: Time series data
- `wind_speed_bins::Vector{Float64}=DEFAULT_WIND_SPEED_BINS`: Optional wind speed bins
"""
function process_turbulence_intensity(
    config::ProjectConfig,
    ts::TimeSeriesData,
    wind_speed_bins::Vector{Float64}=DEFAULT_WIND_SPEED_BINS
)::Nothing
    # Determine target height
    target_height = something(
        config.analysis.ti_target_height,
        config.analysis.target_height,
        120.0
    )
    
    # Find required sensors
    ws_avg, ws_sd, wd = find_ti_sensors(ts, target_height)
    
    isnothing(ws_avg) && error("No wind speed sensor found near height $(target_height)m")
    isnothing(ws_sd) && error("No wind speed standard deviation sensor found at height $(ws_avg.height)m")
    isnothing(wd) && error("No wind direction sensor found near height $(target_height)m")
    
    # Calculate TI time series
    ti_df = calculate_ti_series(ts.df, ws_avg.columnName, ws_sd.columnName, wd.columnName)
    
    # Calculate sector statistics
    sector_stats, mean_ti, std_ti, representative_ti = calculate_sector_stats(ti_df)
    
    # Calculate TI matrix for Meteodyn WT
    ti_matrix = calculate_ti_matrix(ti_df, wind_speed_bins, mean_ti)
    
    # Save all results
    save_results(
        config,
        ti_df,
        sector_stats,
        mean_ti,
        std_ti,
        representative_ti,
        ti_matrix
    )
    
    return nothing
end

# Export all public functions
export find_ti_sensors, calculate_ti_series, calculate_sector_stats, calculate_ti_matrix, 
       process_turbulence_intensity, DEFAULT_WIND_SPEED_BINS

end