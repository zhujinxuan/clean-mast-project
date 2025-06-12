module AnalyzeEN

using ...AnalyzeEN.CalculateAnalyzeEN: calculate_analyze_en, ENMastAnalysisResult
using ...AnalyzeEN.WindSpeedMatrixSerialization: serialize_wind_speed_matrices
using ...Types.AnalyzeENConfiguration: load_en_config

"""
    execute(config_path::String, output_path::String="")

Execute EN wind analysis on masts specified in the configuration file.

# Arguments
- `config_path`: Path to the analyze-en.yaml configuration file
- `output_path`: Output directory. If empty, uses config directory with "en_analysis_output" subdirectory
"""
function execute(config_path::String, output_path::Union{String, Nothing}=nothing)
    # Set default output path if not provided
    if isnothing(output_path)
        config_dir = dirname(abspath(config_path))
        output_path = joinpath(config_dir, "en_analysis_output")
    end
    
    # Create output directory if it doesn't exist
    mkpath(output_path)
    
    @info "Starting EN analysis..."
    @info "Configuration: $config_path"
    @info "Output directory: $output_path"
    
    # Load configuration to get mast names
    config = load_en_config(config_path)
    
    # Run analysis
    results = calculate_analyze_en(config_path)
    
    # Serialize all matrices
    matrices = serialize_wind_speed_matrices(results.wind_speed)
    
    output_file = joinpath(output_path, "WindSpeedMatrix.txt")
    if isfile(output_file)
        rm(output_file)
    end
    # Save each mast result
    for (label, content) in matrices
        
        # Write to file
        open(output_file, "a") do io
            write(io, content)
            write(io, repeat("-", 201))
        end
        
        @info "Saved wind speed matrix for mast $(label) to: $output_file"
    end
    
    @info "EN analysis completed successfully!"
end

export execute

end # module 