module TurbulenceIntensity

using DataFrames
using Statistics
using ..Types.MastTimeSeries: TimeSeriesData, SensorColumn, find_nearest_height_sensor
using ..Types.CleanMastConfig: ProjectConfig
using ..Types.Sector: DIRECTION_SECTORS, SECTOR_DEGREES, get_direction_sector, DirectionSector
using ..Types.TurbulenceIntensity: TurbulenceSectorStats, TurbulenceResults

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
- `ws_col::Symbol`: Wind speed average column name
- `sd_col::Symbol`: Wind speed standard deviation column name
- `wd_col::Symbol`: Wind direction column name

# Returns
- `DataFrame`: DataFrame with turbulence intensity calculations
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
        ismissing(wd) ? missing : get_direction_sector(wd).name
    end
    
    return result
end

"""
Calculate sector statistics for turbulence intensity

# Returns
- `TurbulenceSectorStats`: Statistics for each sector and overall statistics
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
        # Get data for this speed bin, skipping missing values
        speed_bin_data = filter(row -> !ismissing(row.ws_avg) && min_speed ≤ row.ws_avg < max_speed, ti_df)
        
        # Calculate TI for each sector with enough data
        for sector in DIRECTION_SECTORS
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
Process turbulence intensity analysis

# Arguments
- `config::ProjectConfig`: Project configuration
- `ts::TimeSeriesData`: Time series data
- `wind_speed_bins::Vector{Float64}=DEFAULT_WIND_SPEED_BINS`: Optional wind speed bins

# Returns
- `TurbulenceResults`: Complete turbulence intensity analysis results
"""
function process_turbulence_intensity(
    config::ProjectConfig,
    ts::TimeSeriesData,
    wind_speed_bins::Vector{Float64}=DEFAULT_WIND_SPEED_BINS
)::TurbulenceResults
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
    sector_stats = calculate_sector_stats(ti_df)
    
    # Calculate TI matrix for Meteodyn WT
    ti_matrix = calculate_ti_matrix(ti_df, wind_speed_bins, sector_stats.mean_ti)
    
    return TurbulenceResults(ti_df, sector_stats, ti_matrix)
end

# Export all public functions
export find_ti_sensors, calculate_ti_series, calculate_sector_stats, calculate_ti_matrix, 
       process_turbulence_intensity, DEFAULT_WIND_SPEED_BINS

end