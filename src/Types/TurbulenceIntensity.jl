module TurbulenceIntensity

using DataFrames

"""
Struct containing turbulence intensity sector statistics
"""
struct TurbulenceSectorStats
    sector_stats::DataFrame  # Statistics for each sector
    mean_ti::Float64        # Overall mean turbulence intensity
    std_ti::Float64         # Overall standard deviation of turbulence intensity
    representative_ti::Float64  # Representative turbulence intensity (mean + std)
end

"""
Struct containing all turbulence intensity analysis results
"""
struct TurbulenceResults
    time_series::DataFrame           # Time series of turbulence intensity
    sector_stats::TurbulenceSectorStats  # Sector statistics
    matrix::DataFrame               # Matrix with TI by sector and wind speed bin
end

export TurbulenceSectorStats, TurbulenceResults

end 