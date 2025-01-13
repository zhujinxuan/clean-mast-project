module TurbulenceIntensity

using DataFrames
using Statistics
using ..Types.MastTimeSeries: TimeSeriesData, SensorColumn, find_nearest_height_sensor
using ..Types.CleanMastConfig: ProjectConfig
using ..Types.Sector: DIRECTION_SECTORS, SECTOR_DEGREES, get_direction_sector

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
export find_ti_sensors

"""
Calculate turbulence intensity matrix for given time series data

# Arguments
- `config::ProjectConfig`: Project configuration
- `ts::TimeSeriesData`: Time series data
- `wind_speed_bins::Vector{Float64}=DEFAULT_WIND_SPEED_BINS`: Optional wind speed bins, defaults to 0:1:25

# Returns
- `DataFrame`: Turbulence intensity matrix with columns for min_speed, max_speed, and each direction sector
"""
function calculate_ti_matrix(
    config::ProjectConfig, 
    ts::TimeSeriesData,
    wind_speed_bins::Vector{Float64}=DEFAULT_WIND_SPEED_BINS
)::DataFrame
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
    
    # Create result DataFrame
    result = DataFrame(
        min_speed = wind_speed_bins[1:end-1],
        max_speed = wind_speed_bins[2:end]
    )
    
    # Add columns for each direction sector
    for sector in DIRECTION_SECTORS
        result[!, sector.name] = Vector{Union{Float64, Missing}}(missing, length(wind_speed_bins)-1)
    end
    
    # Get data from time series
    df = ts.df
    ws_col = ws_avg.columnName
    sd_col = ws_sd.columnName
    wd_col = wd.columnName
    
    # Calculate TI for each bin and sector
    for (i, (min_speed, max_speed)) in enumerate(zip(wind_speed_bins[1:end-1], wind_speed_bins[2:end]))
        # Filter for wind speed range
        speed_mask = (min_speed .<= df[!, ws_col] .< max_speed)
        
        # Skip if no data in this speed range
        sum(speed_mask) == 0 && continue
        
        # Calculate TI for each direction sector
        for sector in DIRECTION_SECTORS
            # Get sector bounds
            sector_idx = findfirst(==(sector), DIRECTION_SECTORS)
            sector_center = SECTOR_DEGREES[sector_idx]
            sector_min = mod(sector_center - 11.25, 360)
            sector_max = mod(sector_center + 11.25, 360)
            
            # Handle sector crossing 360°
            dir_mask = if sector_min > sector_max
                (sector_min .<= df[!, wd_col] .<= 360.0) .| (0.0 .<= df[!, wd_col] .< sector_max)
            else
                sector_min .<= df[!, wd_col] .< sector_max
            end
            
            # Combine masks and filter out missing values
            mask = speed_mask .& dir_mask .& 
                   .!ismissing.(df[!, ws_col]) .& 
                   .!ismissing.(df[!, sd_col]) .& 
                   .!ismissing.(df[!, wd_col])
            
            # Calculate TI if we have at least 5 data points
            if sum(mask) > 5
                ws_values = map(w -> maximum([w, 0.5]), df[mask, ws_col])
                ti_values = df[mask, sd_col] ./ ws_values
                result[i, sector] = mean(ti_values)
            end
        end
    end
    
    return result
end

export calculate_ti_matrix

end 