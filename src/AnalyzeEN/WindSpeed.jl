module WindSpeed

using DataFrames
using Statistics
using ...Types.AnalyzeENConfiguration: ENMastWindSpeedResult, ENMastConfig
using ...Types.MastTimeSeries: TimeSeriesData, SensorColumn
using ...Types.AnalyzeConfiguration: load_timeseries_data, resolve_path

export analyze_single_mast, create_direction_sectors

"""
    create_direction_sectors() -> Vector{Float64}

Create wind direction sectors centered at 0, 15, 30, ..., 345 degrees.
"""
function create_direction_sectors()::Vector{Float64}
    return collect(0.0:15.0:345.0)
end

"""
    get_sector_center(direction::Float64) -> Float64

Find the center of the 15-degree sector that contains the given direction.
"""
function get_sector_center(direction::Float64)::Float64
    # Normalize direction to [0, 360)
    dir = mod(direction, 360.0)
    # Find the nearest sector center (0, 15, 30, ..., 345)
    sector_idx = round(Int, dir / 15.0)
    return mod(sector_idx * 15.0, 360.0)
end

"""
    analyze_wind_speed_by_direction(df::DataFrame, ws_col::Symbol, wd_col::Symbol) -> DataFrame

Analyze wind speed by direction sectors.
Returns DataFrame with columns: Direction, Vmean, Frequency
"""
function analyze_wind_speed_by_direction(df::DataFrame, ws_col::Symbol, wd_col::Symbol)::DataFrame
    # Filter out missing values
    clean_df = dropmissing(df, [ws_col, wd_col])
    
    if nrow(clean_df) == 0
        # Return empty DataFrame with correct structure
        return DataFrame(
            Direction = Float64[],
            Vmean = Float64[],
            Frequency = Float64[]
        )
    end
    
    # Create sectors
    sectors = create_direction_sectors()
    
    # Add sector column
    clean_df[!, :Sector] = get_sector_center.(clean_df[!, wd_col])
    
    # Group by sector and calculate statistics
    grouped = combine(groupby(clean_df, :Sector)) do sdf
        (Vmean = mean(sdf[!, ws_col]),
         Count = nrow(sdf))
    end
    
    # Calculate total count for frequency
    total_count = sum(grouped.Count)
    grouped[!, :Frequency] = grouped.Count ./ total_count
    
    # Create complete result with all sectors
    result = DataFrame(Direction = sectors)
    result = leftjoin(result, grouped[!, [:Sector, :Vmean, :Frequency]], 
                     on = :Direction => :Sector)
    
    # Fill missing sectors with zero
    result.Vmean = coalesce.(result.Vmean, 0.0)
    result.Frequency = coalesce.(result.Frequency, 0.0)
    
    select!(result, :Direction, :Vmean, :Frequency)
    
    return result
end

"""
    analyze_frequency_by_direction_and_speed(df::DataFrame, ws_col::Symbol, wd_col::Symbol; 
                                           max_speed::Int=40) -> DataFrame

Analyze frequency distribution by direction and wind speed bins.
Returns DataFrame with:
- "SpeedBin" column: speed bins (1, 2, 3, ..., 40) where bin n represents speeds (n-1, n] m/s
- Direction columns: "0.0", "15.0", "30.0", ..., "345.0" for each 15-degree sector
- "All Sectors" column: frequency across all direction sectors for each speed bin
- Values: frequency of occurrence for each speed bin in each direction sector
  (e.g., row 5, column "30.0" contains frequency for speeds 4 < v ≤ 5 m/s in 30° sector)
Return DataFrame example:
SpeedBin  │ 0.0   15.0  30.0  ... 345.0  All Sectors
──────────┼─────────────────────────────────────────
1         │ 0.023 0.018 0.025 ... 0.020  0.071
2         │ 0.045 0.040 0.050 ... 0.038  0.101
3         │ 0.032 0.028 0.035 ... 0.025  0.135
...       │ ...   ...   ...   ... ...    ...
40        │ 0.001 0.000 0.002 ... 0.001  0.000
"""
function analyze_frequency_by_direction_and_speed(df::DataFrame, ws_col::Symbol, wd_col::Symbol; 
                                                max_speed::Int=40)::DataFrame
    # Filter out missing values
    clean_df = dropmissing(df, [ws_col, wd_col])
    
    if nrow(clean_df) == 0
        # Return empty DataFrame with correct structure
        # Rows: SpeedBin (1 to max_speed), Columns: Direction sectors + "All Sectors"
        result = DataFrame(SpeedBin = 1:max_speed)
        for sector in create_direction_sectors()
            result[!, string(sector)] .= 0.0
        end
        result[!, "All Sectors"] .= 0.0
        return result
    end
    
    # Add sector and speed bin columns, keep only what we need
    select!(clean_df, ws_col, wd_col)
    clean_df[!, :Sector] = get_sector_center.(clean_df[!, wd_col])
    # Create speed bins where bin number = vmax for that bin
    # Bin 1: 0 < speed ≤ 1, Bin 2: 1 < speed ≤ 2, ..., Bin 40: 39 < speed ≤ 40
    clean_df[!, :SpeedBin] = clamp.(ceil.(Int, clean_df[!, ws_col]), 1, max_speed)
    
    # Calculate frequencies by sector and speed bin
    sector_freq = combine(groupby(clean_df, [:Sector, :SpeedBin])) do sdf
        (Frequency = nrow(sdf) / count(==(sdf.Sector[1]), clean_df.Sector),)
    end
    
    # Pivot sector frequencies into matrix format using unstack
    # Rows: SpeedBin (1, 2, 3, ..., 40), Columns: Sector (0.0, 15.0, ..., 345.0)
    freq_matrix = unstack(sector_freq, :SpeedBin, :Sector, :Frequency, fill=0.0)
    
    # Ensure all direction sectors are present as columns
    default_sectors = create_direction_sectors()
    for sector in default_sectors
        col_name = string(sector)
        if !(col_name in names(freq_matrix))
            freq_matrix[!, col_name] .= 0.0
        end
    end
    
    missing_bins = filter(bin -> !(bin in freq_matrix.SpeedBin), 1:max_speed)
    new_rows = DataFrame(["SpeedBin" => missing_bins, map(r -> r => repeat([0.0], length(missing_bins)), names(freq_matrix)[2:end])...])
    freq_matrix = vcat(freq_matrix, new_rows)
    # Sort by SpeedBin to ensure proper order
    sort!(freq_matrix, :SpeedBin)
    
    # Calculate "All Sectors" frequencies
    all_sectors_freq = combine(groupby(clean_df, :SpeedBin)) do sdf
        (Frequency = nrow(sdf) / nrow(clean_df),)
    end
    sort!(all_sectors_freq, :SpeedBin)
    select!(all_sectors_freq, :SpeedBin, :Frequency)
    rename!(all_sectors_freq, :Frequency => Symbol("All Sectors"))

    freq_matrix = outerjoin(freq_matrix, all_sectors_freq, on = :SpeedBin)
    # Ensure all speed bins are present as rows
    freq_matrix .= coalesce.(freq_matrix, 0.0)
    select!(freq_matrix, ["SpeedBin", map(string, default_sectors)..., "All Sectors"])
    return freq_matrix
end

"""
    find_wind_columns(timeseries::TimeSeriesData, height::Int64) -> (ws_col::Symbol, wd_col::Symbol)

Find wind speed and wind direction columns at the specified height.
"""
function find_wind_columns(timeseries::TimeSeriesData, height::Int64)::Tuple{Symbol, Symbol}
    # Convert Int64 height to Float64 for comparison
    target_height = Float64(height)
    
    # Find wind speed sensor
    ws_sensors = filter(sensor -> sensor.sensorType == "WindSpeed" && 
                                 sensor.height == target_height && 
                                 sensor.statType == "avg", timeseries.sensors)
    if isempty(ws_sensors)
        error("Cannot find wind speed sensor at height $height")
    end
    ws_col = first(ws_sensors)
    
    # Find wind direction sensor
    wd_sensors = filter(sensor -> sensor.sensorType == "WindDirection" && 
                                 sensor.height == target_height && 
                                 sensor.statType == "avg", timeseries.sensors)
    if isempty(wd_sensors)
        error("Cannot find wind direction sensor at height $height")
    end
    wd_col = first(wd_sensors)
    
    return (ws_col.columnName, wd_col.columnName)
end

"""
    analyze_single_mast(mast_config::ENMastConfig, config_dir::String) -> ENMastWindSpeedResult

Analyze wind data for a single mast.
"""
function analyze_single_mast(mast_config::ENMastConfig, config_dir::String)::ENMastWindSpeedResult
    # Resolve paths
    data_path = resolve_path(mast_config.input.data_path, config_dir)
    sensor_path = resolve_path(mast_config.input.sensor_path, config_dir)
    
    # Load time series data
    timeseries = load_timeseries_data(data_path, sensor_path)
    
    # Find wind columns at specified height
    ws_col, wd_col = find_wind_columns(timeseries, mast_config.H)
    
    # Calculate overall mean wind speed
    vmean = mean(skipmissing(timeseries.df[!, ws_col]))
    
    # Analyze by direction
    vmean_by_direction = analyze_wind_speed_by_direction(timeseries.df, ws_col, wd_col)
    
    # Analyze frequency by direction and speed
    freq_by_dir_speed = analyze_frequency_by_direction_and_speed(timeseries.df, ws_col, wd_col)
    
    return ENMastWindSpeedResult(
        mast_config.name,      # Label
        mast_config.x,         # X
        mast_config.y,         # Y
        mast_config.H,         # H
        mast_config.GeoHash,   # GeoHash
        vmean,
        vmean_by_direction,
        freq_by_dir_speed
    )
end

end # module 