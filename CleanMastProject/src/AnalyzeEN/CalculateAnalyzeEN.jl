module CalculateAnalyzeEN

# Import types
using ...Types.AnalyzeENConfiguration: ENMastWindSpeedResult, ENMastConfig, ENAnalyzeConfig, load_en_config

# Import wind speed analysis module
using ..WindSpeed: analyze_single_mast

export calculate_analyze_en, ENMastAnalysisResult

struct ENMastAnalysisResult
    wind_speed :: Vector{ENMastWindSpeedResult}
    turbulence:: Nothing
end

"""
    calculate_analyze_en(config_path::String) -> ENMastAnalysisResult

Analyze wind data for all masts in the EN configuration.
"""
function calculate_analyze_en(config_path::String)::ENMastAnalysisResult
    # Load configuration
    config = load_en_config(config_path)
    config_dir = dirname(abspath(config_path))
    
    # Analyze each mast
    wind_speed_results = map(config.masts) do mast
        @info "Analyzing wind speed matrix for mast: $(mast.name)"
        analyze_single_mast(mast, config_dir)
    end
    
    return ENMastAnalysisResult(wind_speed_results, nothing)
end

end # module 