module CalculateAirDensityCommand

using CSV
using DataFrames
using Statistics

export execute

# Constants for air density calculation
const GAS_CONSTANT_DRY_AIR = 287.05  # J/(kg·K) - specific gas constant for dry air
const STANDARD_PRESSURE = 101325.0   # Pa - standard atmospheric pressure at sea level

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
    celsius_to_kelvin(celsius::Float64)::Float64

Convert temperature from Celsius to Kelvin.
"""
function celsius_to_kelvin(celsius::Float64)::Float64
    return celsius + 273.15
end

"""
    execute(csv_path::String, temp_col::String, pressure_col::String)

Calculate air density from CSV data using median temperature and pressure values.

# Arguments
- `csv_path::String`: Path to CSV file containing temperature and pressure data
- `temp_col::String`: Name of temperature column (assumed to be in Celsius)
- `pressure_col::String`: Name of pressure column (assumed to be in Pascals)

# Example
```bash
julia bin/CleanMast.jl calculate ad data.csv --temp-col Temperature_80m_avg --pressure-col Pressure_80m_avg
```

The command will:
1. Load the CSV file
2. Extract temperature and pressure columns
3. Calculate median values (excluding missing data)
4. Convert temperature from Celsius to Kelvin
5. Calculate air density using ideal gas law
6. Display the result
"""
function execute(csv_path::String, temp_col::String, pressure_col::String)
    @info "Calculating air density from: $csv_path"
    @info "Temperature column: $temp_col"
    @info "Pressure column: $pressure_col"
    
    # Check if file exists
    if !isfile(csv_path)
        error("CSV file not found: $csv_path")
    end
    
    # Load CSV data
    @info "Loading CSV data..."
    df = CSV.read(csv_path, DataFrame)
    
    # Check if columns exist
    if !hasproperty(df, Symbol(temp_col))
        error("Temperature column '$temp_col' not found in CSV file")
    end
    
    if !hasproperty(df, Symbol(pressure_col))
        error("Pressure column '$pressure_col' not found in CSV file")
    end
    
    # Extract temperature and pressure data
    temp_data = df[!, Symbol(temp_col)]
    pressure_data = df[!, Symbol(pressure_col)]
    
    # Remove missing values
    temp_clean = filter(!ismissing, temp_data)
    pressure_clean = filter(!ismissing, pressure_data)
    
    if isempty(temp_clean)
        error("No valid temperature data found in column '$temp_col'")
    end
    
    if isempty(pressure_clean)
        error("No valid pressure data found in column '$pressure_col'")
    end
    
    # Calculate median values
    median_temp_c = median(temp_clean)
    median_pressure_raw = median(pressure_clean)

    # Convert pressure to Pa if it appears to be in kPa (typical range 90-110 kPa)
    median_pressure_pa = if median_pressure_raw < 200  # Likely in kPa
        @info "Pressure appears to be in kPa, converting to Pa"
        median_pressure_raw * 1000.0
    else
        median_pressure_raw
    end
    
    @info "Data statistics:"
    @info "  Temperature: $(length(temp_clean)) valid values, median = $(round(median_temp_c, digits=2))°C"
    @info "  Pressure: $(length(pressure_clean)) valid values, median = $(round(median_pressure_pa, digits=1)) Pa"
    
    # Convert temperature to Kelvin
    median_temp_k = celsius_to_kelvin(median_temp_c)
    
    # Calculate air density
    air_density = calculate_air_density(median_temp_k, median_pressure_pa)
    
    # Display results
    println()
    println("=" ^ 50)
    println("AIR DENSITY CALCULATION RESULTS")
    println("=" ^ 50)
    println("Input Data:")
    println("  CSV file: $csv_path")
    println("  Temperature column: $temp_col")
    println("  Pressure column: $pressure_col")
    println()
    println("Median Values:")
    println("  Temperature: $(round(median_temp_c, digits=2))°C ($(round(median_temp_k, digits=2))K)")
    println("  Pressure: $(round(median_pressure_pa, digits=1)) Pa")
    println()
    println("Calculated Air Density:")
    println("  ρ = $(round(air_density, digits=4)) kg/m³")
    println()
    println("For comparison:")
    println("  Standard air density (15°C, 1013.25 hPa): 1.225 kg/m³")
    println("  Difference from standard: $(round((air_density - 1.225) / 1.225 * 100, digits=2))%")
    println("=" ^ 50)
    
    return air_density
end

end # module
