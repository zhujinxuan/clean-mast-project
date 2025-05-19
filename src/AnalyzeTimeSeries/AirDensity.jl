"""
# Air Density Module
Functions to calculate air density at different heights.
"""
module AirDensity

using ...Types.CleanMastConfig: AirDensityConfig

# Constants
const STANDARD_AIR_DENSITY = 1.225  # kg/m³, at sea level, 15°C
const GRAVITATIONAL_ACCELERATION = 9.81  # m/s²
const GAS_CONSTANT_DRY_AIR = 287.05  # J/(kg·K)
const TEMPERATURE_LAPSE_RATE = 0.0065  # K/m, standard atmosphere

"""
    calculate_air_density(height::Float64, config::AirDensityConfig)::Float64

Calculate air density at a specific height using the barometric formula.

# Arguments
- `height::Float64`: Height in meters above sea level
- `config::AirDensityConfig`: Configuration with reference density and height

# Returns
- `Float64`: Air density at the specified height in kg/m³
"""
function calculate_air_density(height::Float64, config::AirDensityConfig)::Float64
    # If height matches reference height, return reference density
    if height ≈ config.reference_height
        return config.density
    end
    
    # Standard altitude formula based on barometric equation
    # ρ = ρ₀ * exp(-g * (h - h₀) / (R * T))
    # where:
    # ρ₀ is reference density
    # g is gravitational acceleration
    # h is height
    # h₀ is reference height
    # R is gas constant for dry air
    # T is temperature (approximated as 288.15K at sea level)
    
    # Approximate temperature at reference height (K)
    reference_temperature = 288.15 - TEMPERATURE_LAPSE_RATE * config.reference_height
    
    # Calculate height difference
    height_diff = height - config.reference_height
    
    # Calculate air density using barometric formula
    density = config.density * exp(
        -GRAVITATIONAL_ACCELERATION * height_diff / 
        (GAS_CONSTANT_DRY_AIR * reference_temperature)
    )
    
    return density
end

"""
    calculate_wind_power_density(wind_speed::Float64, air_density::Float64)::Float64

Calculate wind power density based on wind speed and air density.

# Arguments
- `wind_speed::Union{Missing, Float64}`: Wind speed in m/s
- `air_density::Float64`: Air density in kg/m³

# Returns
- `Union{Missing, Float64}`: Wind power density in W/m²
"""
function calculate_wind_power_density(wind_speed::Union{Missing, Float64}, air_density::Float64)::Union{Missing, Float64}
    if ismissing(wind_speed)
        return missing
    end
    # Wind power density formula: P = 0.5 * ρ * v³
    0.5 * air_density * wind_speed^3
end

export calculate_air_density, calculate_wind_power_density

end # module 