module CalculateAirDensity

using CSV
using DataFrames
using Statistics
using ...Types.SensorColumns: SensorColumn
using ...Types.ReportTimeSeriesConfiguration: AirDensityConfig
using ...CleanMastUtils: load_dict
using ...Types.Utils: from_dict

export calculate_air_density_from_data

const GAS_CONSTANT_DRY_AIR = 287.05  # J/(kg·K) - specific gas constant for dry air

"""
    find_lowest_sensor(sensors::Vector{SensorColumn}, sensor_type::String,
                      stat_type::String="avg")::Union{SensorColumn, Nothing}

Find the sensor with the lowest height of specified type and statType.

# Arguments
- `sensors::Vector{SensorColumn}`: Vector of sensor configurations
- `sensor_type::String`: Sensor type (e.g., "Temperature", "Pressure")
- `stat_type::String`: Statistical type (default: "avg")

# Returns
- `Union{SensorColumn, Nothing}`: Sensor with lowest height, or nothing if not found
"""
function find_lowest_sensor(sensors::Vector{SensorColumn}, sensor_type::String,
                           stat_type::String="avg")::Union{SensorColumn, Nothing}
    matching_sensors = filter(s -> s.sensorType == sensor_type && s.statType == stat_type,
                             sensors)
    isempty(matching_sensors) && return nothing

    return reduce((s1, s2) -> s1.height < s2.height ? s1 : s2, matching_sensors)
end

"""
    celsius_to_kelvin(celsius::Float64)::Float64

Convert temperature from Celsius to Kelvin.
"""
function celsius_to_kelvin(celsius::Float64)::Float64
    return celsius + 273.15
end

"""
    calculate_air_density(temperature_k::Float64, pressure_pa::Float64)::Float64

Calculate air density using the ideal gas law for dry air.

# Arguments
- `temperature_k::Float64`: Temperature in Kelvin
- `pressure_pa::Float64`: Pressure in Pascals

# Returns
- `Float64`: Air density in kg/m³

# Formula
ρ = P / (R_specific × T)
where:
- ρ = air density (kg/m³)
- P = pressure (Pa)
- R_specific = specific gas constant for dry air (287.05 J/(kg·K))
- T = temperature (K)
"""
function calculate_air_density(temperature_k::Float64, pressure_pa::Float64)::Float64
    return pressure_pa / (GAS_CONSTANT_DRY_AIR * temperature_k)
end

"""
    calculate_air_density_from_data(data_path::String, sensors_path::String)
        ::Union{AirDensityConfig, Nothing}

Calculate air density configuration from time series data.

# Arguments
- `data_path::String`: Path to CSV file containing time series data
- `sensors_path::String`: Path to sensor configuration file (YAML/TOML)

# Returns
- `Union{AirDensityConfig, Nothing}`: Air density configuration, or nothing if
  temperature or pressure sensors are not available

# Algorithm
1. Load sensor configuration and find lowest Temperature and Pressure sensors
2. If both sensors exist, load data and calculate median temperature and pressure
3. Convert temperature to Kelvin and calculate air density using ideal gas law
4. Return AirDensityConfig with density and reference height (minimum of sensor heights)
"""
function calculate_air_density_from_data(data_path::String, sensors_path::String)::Union{AirDensityConfig, Nothing}

    # Load sensor configuration
    sensor_dict = load_dict(sensors_path)
    sensors = [from_dict(SensorColumn, Dict{String, Any}(s))
              for s in sensor_dict["sensors"]]

    # Find lowest Temperature and Pressure sensors
    temp_sensor = find_lowest_sensor(sensors, "Temperature", "avg")
    pressure_sensor = find_lowest_sensor(sensors, "Pressure", "avg")

    # If either sensor is missing, return nothing
    if isnothing(temp_sensor) || isnothing(pressure_sensor)
        return nothing
    end

    @info "Found Temperature sensor: $(temp_sensor.columnName) at $(temp_sensor.height)m"
    @info "Found Pressure sensor: $(pressure_sensor.columnName) at $(pressure_sensor.height)m"

    # Load data
    df = CSV.read(data_path, DataFrame)

    # Extract temperature and pressure data
    temp_data = df[!, temp_sensor.columnName]
    pressure_data = df[!, pressure_sensor.columnName]

    # Remove missing values
    temp_clean = filter(!ismissing, temp_data)
    pressure_clean = filter(!ismissing, pressure_data)

    if isempty(temp_clean) || isempty(pressure_clean)
        @warn "No valid temperature or pressure data found"
        return nothing
    end

    # Calculate median values
    median_temp_c = median(temp_clean)
    median_pressure_pa = median(pressure_clean)

    @info "Median temperature: $(round(median_temp_c, digits=2))°C"
    @info "Median pressure: $(round(median_pressure_pa, digits=1)) Pa"

    # Convert temperature to Kelvin
    median_temp_k = celsius_to_kelvin(median_temp_c)

    # Calculate air density
    air_density = calculate_air_density(median_temp_k, median_pressure_pa)

    # Reference height is the minimum of temperature and pressure sensor heights
    reference_height = min(temp_sensor.height, pressure_sensor.height)

    @info "Calculated air density: $(round(air_density, digits=4)) kg/m³ at $(reference_height)m"

    return AirDensityConfig(air_density, reference_height)
end

end # module
