module TurbulenceIntensity

using CSV
using DataFrames
using ...Types.CleanMastConfig: ProjectConfig
using ...Types.MastTimeSeries: TimeSeriesData
using ...TurbulenceIntensity: calculate_ti_matrix

"""
Calculate turbulence intensity matrix and save to CSV file

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
    # Calculate TI matrix
    ti_matrix = if isnothing(wind_speed_bins)
        calculate_ti_matrix(config, ts)
    else
        calculate_ti_matrix(config, ts, wind_speed_bins)
    end
    
    # Save to CSV
    output_dir = joinpath(dirname(config.mast.data_path), "analysis")
    mkpath(output_dir)
    output_file = joinpath(output_dir, "turbulence_intensity_matrix.csv")
    CSV.write(output_file, ti_matrix)
    
    return nothing
end

export calculate

end 