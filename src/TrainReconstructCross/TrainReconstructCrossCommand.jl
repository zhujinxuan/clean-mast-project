"""
    TrainReconstructCrossCommand.jl

Main command implementation for training cross-mast relationships and reconstruction models.
Orchestrates the complete workflow: analysis → model training → results serialization.
"""
module TrainReconstructCrossCommand

using DataFrames
using Dates
using Statistics
using TOML
using JLD2

# Import analysis components
using ..DataCoverage: analyze_mast_pair_coverage
using ..CrossMastSpeedCorrelation: analyze_windspeed_correlations
using ..CrossMastDirectionAnalysis: analyze_winddirection_differences
using ..CrossMastSummary: summarize_correlations, summarize_direction_analysis

# Import types
import ...Types.MastTimeSeries: TimeSeriesData, load_timeseries
import ...Types.SensorColumns: SensorColumn
import ...Types.CrossMastAnalysisResults: MastPairAnalysisResult, MastPairCoverage, to_dict
import ...Types.CrossMastSpeedModels: CrossMastSpeedModel
import ...Types.CrossMastDirectionModels: CrossMastDirectionModel
import ...Types.CrossMastTrainParams: CrossMastSpeedTrainParams, CrossMastDirectionTrainParams
import ...Types.TrainReconstructCrossConfig: TrainReconstructCrossConfiguration, TrainCrossSettings, from_dict
import ...Types.MastReferenceModel: train
import ...Types.Utils: strip_nothing_values
using ...CleanMastUtils: load_dict

export execute

"""
    execute(config_path::String)

Execute the train reconstruct-cross command.

# Arguments
- `config_path::String`: Path to train-reconstruct-cross.toml configuration file

# Workflow
1. Load and validate configuration
2. Create output directory structure  
3. Load all mast time series data
4. Analyze all mast pairs (N² combinations)
5. Train and save models for qualified pairs
6. Save machine-readable results (TOML)
7. Generate summary statistics
"""
function execute(config_path::String)
    println("🚀 Starting cross-mast training...")
    
    # 1. Load and validate configuration
    config_dict = load_dict(config_path)
    config = from_dict(TrainReconstructCrossConfiguration, config_dict)
    project_dir = dirname(config_path)
    println("📋 Loaded configuration with $(length(config.masts)) masts")
    println("⚙️  Training parameters: min_overlap=$(config.train.min_overlap_days) days, min_data=$(config.train.min_data_points)")
    
    # 2. Create output directory structure
    full_output_dir = joinpath(project_dir, config.train.output_dir)
    mkpath(full_output_dir)
    mkpath(joinpath(full_output_dir, "cross-mast-models"))
    println("📁 Created output directory: $(full_output_dir)")
    
    # 3. Load all mast time series data
    mast_data = load_all_mast_data(config, project_dir)
    println("📊 Loaded time series data for $(length(mast_data)) masts")
    
    # 4. Analyze all mast pairs (N² combinations)
    analysis_results = Vector{MastPairAnalysisResult}(map( Iterators.product(config.masts, config.masts) ) do (target_mast, source_mast)
        if target_mast.name == source_mast.name
            return nothing
        end
        println("🔍 Training pair $(target_mast.name) ← $(source_mast.name)")
        return train_mast_pair(
                    mast_data[target_mast.name], 
                    mast_data[source_mast.name],
                    target_mast.name,
                    source_mast.name,
                    config.train,
                    full_output_dir
                )
    end |> filter(!isnothing))
    
    # 5. Save machine-readable results
    results_path = joinpath(full_output_dir, "train-results.toml")
    save_train_results_toml(analysis_results, results_path)
    println("💾 Saved training results to: $results_path")
    
    # 6. Generate summary statistics
    print_final_summary(analysis_results)
    println("✅ Cross-mast training completed successfully!")
end

"""
    train_mast_pair(target_ts, source_ts, target_name, source_name, settings, full_output_dir)

Train a single mast pair: coverage, correlations, directions, model training.

Returns MastPairAnalysisResult or nothing if training impossible.
"""
function train_mast_pair(target_ts::TimeSeriesData, source_ts::TimeSeriesData, 
                          target_name::String, source_name::String, 
                          settings::TrainCrossSettings, full_output_dir::String)::Union{MastPairAnalysisResult, Nothing}
    
    # 1. Data coverage analysis
    coverage = analyze_mast_pair_coverage(target_ts, source_ts)
    
    # Handle case where no coverage analysis is possible
    if isnothing(coverage)
        @warn "  Coverage: No training possible (no wind speed sensors or no overlap)"
        return nothing
    end

    if (coverage.overlap_days < settings.min_overlap_days)
        @warn "  ⚠️  Insufficient data for model training ($(round(coverage.overlap_days, digits=1)) < $(settings.min_overlap_days) days)"
        return nothing
    end
    
    println("  📈 Coverage: $(round(coverage.overlap_days, digits=1)) days")
    
    # 2. Wind speed correlation analysis
    speed_correlations = analyze_windspeed_correlations(target_ts, source_ts)
    speed_summary = summarize_correlations(speed_correlations)
    println("  🌪️  Best high-elevation speed correlation: $(round(speed_summary.best_high_elevation_correlation, digits=3))")
    
    # 3. Wind direction analysis
    direction_analysis = analyze_winddirection_differences(target_ts, source_ts)
    direction_summary = summarize_direction_analysis(direction_analysis)
    println("  🧭 Best high-elevation direction std: $(round(direction_summary.best_high_elevation_std, digits=1))°")
    
    # 4. Train and save models if sufficient data available
    speed_model_file = nothing
    direction_model_file = nothing
    
    # Train and save speed model (use permissive defaults)
    speed_params = CrossMastSpeedTrainParams(
        target_name=target_name,
        source_name=source_name,
        min_data_points=settings.min_data_points,
        exclude_nan_results=settings.exclude_nan_results
    )
    speed_model = train(CrossMastSpeedModel, speed_params, target_ts, source_ts)
    speed_model_file = save_speed_model(speed_model, full_output_dir, target_name, source_name)

    # Train and save direction model (use permissive defaults)
    direction_params = CrossMastDirectionTrainParams(
        target_name=target_name,
        source_name=source_name,
        min_data_points=settings.min_data_points,
        exclude_nan_results=settings.exclude_nan_results
    )
    direction_model = train(CrossMastDirectionModel, direction_params, target_ts, source_ts)
    direction_model_file = save_direction_model(direction_model, full_output_dir, target_name, source_name)
        
    println("  💾 Saved models: $(speed_model_file !== nothing ? "✅" : "❌") speed, $(direction_model_file !== nothing ? "✅" : "❌") direction")
    
    return MastPairAnalysisResult(
        target_mast=target_name,
        source_mast=source_name,
        coverage=coverage,
        windspeed_correlations=speed_correlations,
        winddirection_analysis=direction_analysis,
        windspeed_summary=speed_summary,
        winddirection_summary=direction_summary,
        windspeed_model_file=speed_model_file,
        winddirection_model_file=direction_model_file
    )
end

"""
    save_speed_model(model, output_dir, target_name, source_name)

Save a CrossMastSpeedModel to JLD2 file.
"""
function save_speed_model(model::CrossMastSpeedModel, output_dir::String, 
                         target_name::String, source_name::String)::Union{String, Nothing}
    if isempty(model.pairs)
        @debug "No speed pairs to save for $target_name ← $source_name"
        return nothing
    end
    
    # Create directory structure: output_dir/cross-mast-models/target/source/
    model_dir = joinpath(output_dir, "cross-mast-models", target_name, source_name)
    mkpath(model_dir)
    
    # Save using JLD2
    model_path = joinpath(model_dir, "windspeed.jld2")
    @save model_path model
    
    @info "Saved speed model: $model_path ($(length(model.pairs)) pairs)"
    return model_path
end

"""
    save_direction_model(model, output_dir, target_name, source_name)

Save a CrossMastDirectionModel to JLD2 file.
"""
function save_direction_model(model::CrossMastDirectionModel, output_dir::String,
                            target_name::String, source_name::String)::Union{String, Nothing}
    if isempty(model.pairs)
        @debug "No direction pairs to save for $target_name ← $source_name"
        return nothing
    end
    
    # Create directory structure: output_dir/cross-mast-models/target/source/
    model_dir = joinpath(output_dir, "cross-mast-models", target_name, source_name)
    mkpath(model_dir)
    
    # Save using JLD2
    model_path = joinpath(model_dir, "winddirection.jld2")
    @save model_path model
    
    @info "Saved direction model: $model_path ($(length(model.pairs)) pairs)"
    return model_path
end

"""
    save_train_results_toml(results, output_path)

Save training results as machine-readable TOML file.
Leverages existing to_dict infrastructure.
"""
function save_train_results_toml(results::Vector{MastPairAnalysisResult}, output_path::String)
    toml_dict = Dict{String, Any}(
        "metadata" => Dict{String, Any}(
            "generated_at" => string(now()),
            "total_mast_pairs" => length(results),
            "qualified_speed_pairs" => count(r -> is_qualified_for_speed(r), results),
            "qualified_direction_pairs" => count(r -> is_qualified_for_direction(r), results)
        ),
        "mast_pairs" => [to_dict(result) for result in results]  # Uses existing to_dict!
    )
    
    open(output_path, "w") do io
        TOML.print(io, strip_nothing_values(toml_dict))
    end
    
    @info "Saved training results TOML: $output_path"
end

"""
    load_all_mast_data(config, project_dir)

Load time series data for all masts.
"""
function load_all_mast_data(config :: TrainReconstructCrossConfiguration, project_dir::String)::Dict{String, TimeSeriesData}
    return Dict{String, TimeSeriesData}(
        map(config.masts) do m
            m.name => load_timeseries(m.input, project_dir)
        end
    )
end

"""
    is_qualified_for_speed(result)

Check if mast pair qualifies for wind speed reconstruction.
"""
function is_qualified_for_speed(result::MastPairAnalysisResult)::Bool
    return result.coverage.overlap_days >= 120.0 && 
           result.windspeed_summary.best_high_elevation_correlation >= 0.7
end

"""
    is_qualified_for_direction(result)

Check if mast pair qualifies for wind direction reconstruction.
"""
function is_qualified_for_direction(result::MastPairAnalysisResult)::Bool
    return result.coverage.overlap_days >= 120.0 && 
           result.winddirection_summary.best_high_elevation_std <= 45.0
end

"""
    print_final_summary(results)

Print final training summary statistics.
"""
function print_final_summary(results::Vector{MastPairAnalysisResult})
    qualified_speed = count(is_qualified_for_speed, results)
    qualified_direction = count(is_qualified_for_direction, results)
    
    println("\n📈 Training Summary:")
    println("  Total mast pairs trained: $(length(results))")
    println("  Qualified for wind speed reconstruction: $qualified_speed")
    println("  Qualified for wind direction reconstruction: $qualified_direction")
    
    # Best correlations across all pairs
    if !isempty(results)
        best_speed_corr = maximum(r -> r.windspeed_summary.best_high_elevation_correlation, results)
        best_direction_std = minimum(r -> r.winddirection_summary.best_high_elevation_std, results)
        
        println("  Best high-elevation speed correlation: $(round(best_speed_corr, digits=3))")
        println("  Best high-elevation direction std: $(round(best_direction_std, digits=1))°")
    end
end

end # module 