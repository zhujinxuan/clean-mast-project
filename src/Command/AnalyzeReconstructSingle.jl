module AnalyzeReconstructSingle

using ...Types.AnalyzeReconstructSingleConfiguration: load_analyze_reconstruct_single_config
using ...ReportReconstructSingle: analyze_reconstruction_comparison

"""
    execute(config_path::String)

Execute reconstruction analysis using the provided configuration file.

# Arguments
- `config_path::String`: Path to the analyze-reconstruct-single.yaml configuration file

# Example
```
julia bin/CleanMast.jl analyze reconstruct-single path/to/analyze-reconstruct-single.yaml
```

The YAML configuration file should specify:
- Multiple masts with before/after reconstruction data files and sensor configurations
- Output directory for results (default: ./analyze-reconstruct-single)

For each mast, the analysis includes:
- Missing data points count before/after reconstruction
- Reconstruction rate and data coverage ratio
- R² matrix of wind speed correlations between heights
- Mean and standard deviation of wind direction differences between heights
"""
function execute(config_path::String)
    @info "Loading analyze reconstruct-single configuration from: $config_path"
    
    # Load and process the configuration
    config = load_analyze_reconstruct_single_config(config_path)
    
    @info "Starting reconstruction analysis for $(length(config.masts)) mast(s)"
    
    # Run the analysis
    results = analyze_reconstruction_comparison(config)
    
    @info "Analysis complete. Results saved to: $(config.outputDir)"
    
    return 0
end

end # module 