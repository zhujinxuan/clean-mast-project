module TurbulenceIntensity

using ...Types.CleanMastConfig: ProjectConfig
using ...Types.MastTimeSeries: TimeSeriesData
using ...TurbulenceIntensity: process_turbulence_intensity

"""
Calculate turbulence intensity and save results to files

# Arguments
- `config::ProjectConfig`: Project configuration
- `ts::TimeSeriesData`: Time series data
- `wind_speed_bins::Union{Nothing, Vector{Float64}}=nothing`: Optional wind speed bins. If nothing, uses default bins
"""
function calculate(
    config::ProjectConfig, 
    ts::TimeSeriesData,
    wind_speed_bins::Union{Nothing, Vector{Float64}}=nothing
)::Nothing
    # Process turbulence intensity with optional wind speed bins
    if isnothing(wind_speed_bins)
        process_turbulence_intensity(config, ts)
    else
        process_turbulence_intensity(config, ts, wind_speed_bins)
    end
    
    return nothing
end

export calculate

end 