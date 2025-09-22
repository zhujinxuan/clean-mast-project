"""
    RecommendReconstructCrossCommand.jl

Generate reconstruct-cross.toml configuration from train-results.toml.
This command analyzes training results and creates intelligent reconstruction recommendations.
"""
module RecommendReconstructCrossCommand

using TOML
using Dates
using ...Types.CrossMastAnalysisResults: MastPairAnalysisResult, from_dict
using ...Types.ReconstructCrossConfig: ReconstructCrossConfiguration, ReconstructCrossSettings, 
                                       ReconstructionJob, ReconstructionPriority, ReconstructCrossMast, to_dict
using ...Types.MastTimeSeries: TimeSeriesSource
using ...Types.Utils: from_dict, to_dict
using ...CleanMastUtils: load_dict

export execute

"""
    execute(train_results_path::String, output_dir::String = "./")

Generate reconstruct-cross.toml configuration from train-results.toml.

# Arguments
- `train_results_path::String`: Path to train-results.toml from train command
- `output_dir::String`: Directory to write reconstruct-cross.toml (default: current directory)

# Algorithm
1. Load and parse train-results.toml
2. Filter qualified mast pairs (correlation ≥0.3, direction std ≤25°, ≥120 days data)
3. For each target mast, find best source mast(s) by correlation
4. Create priority levels: excellent (≥0.7), good (≥0.5), acceptable (≥0.3)
5. Generate reconstruction job queue with fallback options
6. Create complete reconstruct-cross.toml configuration

# Returns
- Path to generated reconstruct-cross.toml file
"""
function execute(train_results_path::String, output_dir::String = "./")::String
    println("🔍 Analyzing training results for reconstruction recommendations...")
    
    # 1. Load and parse train-results.toml
    if !isfile(train_results_path)
        error("Training results file not found: $train_results_path")
    end
    
    train_results_dict = load_dict(train_results_path)
    train_results = parse_train_results(train_results_dict)
    
    println("📊 Loaded training results for $(length(train_results)) mast pairs")
    
    # 2. Analyze reconstruction opportunities
    reconstruction_candidates = analyze_reconstruction_opportunities(train_results)
    
    if isempty(reconstruction_candidates)
        @warn "No qualified reconstruction opportunities found. Check training results and selection criteria."
        return ""
    end
    
    println("🎯 Found reconstruction opportunities for $(length(reconstruction_candidates)) target masts")
    
    # 3. Create priority levels and reconstruction jobs
    priority_levels = create_priority_levels(reconstruction_candidates, train_results_path, output_dir)
    
    # 4. Create mast configurations from training results
    masts = create_mast_configurations(train_results)
    
    # 5. Create complete configuration
    config = ReconstructCrossConfiguration(
        masts = masts,
        reconstruction_priorities = priority_levels,
        settings = ReconstructCrossSettings(),
        training_metadata = create_training_metadata(train_results_dict, train_results_path)
    )
    
    # 6. Save configuration file
    output_path = joinpath(output_dir, "reconstruct-cross.toml")
    config_dict = to_dict(config)
    
    open(output_path, "w") do io
        println(io, "# Cross-Mast Reconstruction Configuration")
        println(io, "# Generated from training results: $train_results_path")
        println(io, "# Generated on: $(now())")
        println(io)
        TOML.print(io, config_dict)
    end
    
    # 7. Print summary
    print_recommendation_summary(priority_levels, output_path)
    
    return output_path
end

"""
    parse_train_results(train_results_dict::Dict{String, Any})::Vector{MastPairAnalysisResult}

Parse train-results.toml dictionary into MastPairAnalysisResult objects.
"""
function parse_train_results(train_results_dict::Dict{String, Any})::Vector{MastPairAnalysisResult}
    if !haskey(train_results_dict, "mast_pairs")
        error("Invalid training results format: missing 'mast_pairs' section")
    end
    
    return [from_dict(MastPairAnalysisResult, pair_dict) for pair_dict in train_results_dict["mast_pairs"]]
end

"""
    ReconstructionCandidate

Internal struct for recommendation analysis.
"""
struct ReconstructionCandidate
    target_mast::String
    source_mast::String
    speed_correlation::Float64
    direction_std::Float64
    data_coverage_days::Float64
    model_paths::Dict{String, String}
    qualification_score::Float64
end

"""
    meets_basic_qualification_criteria(result::MastPairAnalysisResult)::Bool

Check if a training result meets basic qualification criteria for reconstruction.
"""
function meets_basic_qualification_criteria(result::MastPairAnalysisResult)::Bool
    # Loose threshold criteria for reconstruct cross-masts
    MIN_CORRELATION = 0.3
    MAX_DIRECTION_STD = 25.0
    MIN_COVERAGE_DAYS = 120.0

    speed_qualified = result.windspeed_summary.best_high_elevation_correlation >= MIN_CORRELATION
    direction_qualified = result.winddirection_summary.best_high_elevation_std <= MAX_DIRECTION_STD
    coverage_qualified = result.coverage.overlap_days >= MIN_COVERAGE_DAYS

    return (speed_qualified || direction_qualified) && coverage_qualified
end

"""
    create_reconstruction_candidate(result::MastPairAnalysisResult)::Union{ReconstructionCandidate, Nothing}

Create a reconstruction candidate from a qualified training result.
"""
function create_reconstruction_candidate(result::MastPairAnalysisResult)::Union{ReconstructionCandidate, Nothing}
    # Loose threshold criteria for reconstruct cross-masts
    MIN_CORRELATION = 0.3
    MAX_DIRECTION_STD = 25.0

    # Determine which variables are available
    variables = String[]
    model_paths = Dict{String, String}()

    speed_qualified = result.windspeed_summary.best_high_elevation_correlation >= MIN_CORRELATION
    direction_qualified = result.winddirection_summary.best_high_elevation_std <= MAX_DIRECTION_STD

    if speed_qualified && result.windspeed_model_file !== nothing
        push!(variables, "windspeed")
        model_paths["windspeed"] = result.windspeed_model_file
    end

    if direction_qualified && result.winddirection_model_file !== nothing
        push!(variables, "winddirection")
        model_paths["winddirection"] = result.winddirection_model_file
    end

    if isempty(variables)
        return nothing
    end

    # Calculate qualification score (higher is better)
    score = calculate_qualification_score(
        result.windspeed_summary.best_high_elevation_correlation,
        result.winddirection_summary.best_high_elevation_std,
        result.coverage.overlap_days
    )

    return ReconstructionCandidate(
        result.target_mast,
        result.source_mast,
        result.windspeed_summary.best_high_elevation_correlation,
        result.winddirection_summary.best_high_elevation_std,
        result.coverage.overlap_days,
        model_paths,
        score
    )
end

"""
    group_candidates_by_target(candidates::Vector{ReconstructionCandidate})::Dict{String, Vector{ReconstructionCandidate}}

Group reconstruction candidates by their target mast.
"""
function group_candidates_by_target(candidates::Vector{ReconstructionCandidate})::Dict{String, Vector{ReconstructionCandidate}}
    opportunities = Dict{String, Vector{ReconstructionCandidate}}()

    for candidate in candidates
        target_mast = candidate.target_mast  # This needs to be added to ReconstructionCandidate
        if !haskey(opportunities, target_mast)
            opportunities[target_mast] = ReconstructionCandidate[]
        end
        push!(opportunities[target_mast], candidate)
    end

    return opportunities
end

"""
    analyze_reconstruction_opportunities(train_results::Vector{MastPairAnalysisResult})::Dict{String, Vector{ReconstructionCandidate}}

Analyze train results to identify reconstruction opportunities for each mast.
"""
function analyze_reconstruction_opportunities(train_results::Vector{MastPairAnalysisResult})::Dict{String, Vector{ReconstructionCandidate}}
    
    # Process all training results into reconstruction candidates
    candidates = train_results |>
        results -> filter(meets_basic_qualification_criteria, results) |>
        results -> map(create_reconstruction_candidate, results) |>
        results -> filter(!isnothing, results) |>
        Vector{ReconstructionCandidate}

    # Group candidates by target mast
    opportunities = group_candidates_by_target(candidates)
    
    # Sort candidates by qualification score (best first)
    for (target_mast, candidates) in opportunities
        sort!(candidates, by = c -> c.qualification_score, rev = true)
    end
    
    return opportunities
end

"""
    calculate_qualification_score(correlation::Float64, direction_std::Float64, coverage_days::Float64)::Float64

Calculate a qualification score for ranking reconstruction candidates.
Higher scores indicate better reconstruction opportunities.
"""
function calculate_qualification_score(correlation::Float64, direction_std::Float64, coverage_days::Float64)::Float64
    # Normalize components to 0-1 scale
    correlation_score = min(correlation, 1.0)  # Already 0-1
    direction_score = max(0.0, 1.0 - direction_std / 25.0)  # 0° = 1.0, 25°+ = 0.0
    coverage_score = min(coverage_days / 365.0, 1.0)  # 365 days = 1.0
    
    # Weighted combination (correlation is most important)
    return 0.6 * correlation_score + 0.2 * direction_score + 0.2 * coverage_score
end

"""
    create_priority_levels(candidates::Dict{String, Vector{ReconstructionCandidate}}, train_results_path::String, output_dir::String)::Vector{ReconstructionPriority}

Group reconstruction jobs into priority levels based on correlation quality.
"""
function create_priority_levels(candidates::Dict{String, Vector{ReconstructionCandidate}}, train_results_path::String, output_dir::String)::Vector{ReconstructionPriority}
    # Priority thresholds adjusted for loose criteria
    EXCELLENT_THRESHOLD = 0.7
    GOOD_THRESHOLD = 0.5
    ACCEPTABLE_THRESHOLD = 0.3
    
    excellent_jobs = ReconstructionJob[]
    good_jobs = ReconstructionJob[]
    acceptable_jobs = ReconstructionJob[]
    
    # Extract model directory from train results path (make relative to project directory)
    train_dir = dirname(train_results_path)
    # Make train_dir relative to output_dir (project directory)
    relative_train_dir = relpath(train_dir, output_dir)

    priority_counter = 1

    for (target_mast, target_candidates) in candidates
        for (idx, candidate) in enumerate(target_candidates)
            # Determine variables to reconstruct
            variables = collect(keys(candidate.model_paths))

            # Create model directory path (relative to project directory)
            model_dir = joinpath(relative_train_dir, "cross-mast-models", target_mast, candidate.source_mast)
            
            job = ReconstructionJob(
                target_mast = target_mast,
                source_mast = candidate.source_mast,
                model_dir = model_dir,
                priority = priority_counter,
                speed_correlation = candidate.speed_correlation,
                direction_std = candidate.direction_std,
                data_coverage_days = candidate.data_coverage_days,
                variables = variables
            )
            
            # Assign to priority level based on correlation
            if candidate.speed_correlation >= EXCELLENT_THRESHOLD
                push!(excellent_jobs, job)
            elseif candidate.speed_correlation >= GOOD_THRESHOLD
                push!(good_jobs, job)
            else
                push!(acceptable_jobs, job)
            end
            
            priority_counter += 1
        end
    end
    
    priority_levels = ReconstructionPriority[]
    
    if !isempty(excellent_jobs)
        push!(priority_levels, ReconstructionPriority(
            priority_level = 1,
            min_correlation = EXCELLENT_THRESHOLD,
            max_direction_std = 15.0,
            jobs = excellent_jobs
        ))
    end

    if !isempty(good_jobs)
        push!(priority_levels, ReconstructionPriority(
            priority_level = 2,
            min_correlation = GOOD_THRESHOLD,
            max_direction_std = 20.0,
            jobs = good_jobs
        ))
    end

    if !isempty(acceptable_jobs)
        push!(priority_levels, ReconstructionPriority(
            priority_level = 3,
            min_correlation = ACCEPTABLE_THRESHOLD,
            max_direction_std = 25.0,
            jobs = acceptable_jobs
        ))
    end
    
    return priority_levels
end

"""
    create_mast_configurations(train_results::Vector{MastPairAnalysisResult})::Vector{ReconstructCrossMast}

Create mast configurations from training results.
"""
function create_mast_configurations(train_results::Vector{MastPairAnalysisResult})::Vector{ReconstructCrossMast}
    # Extract unique mast names and their input sources
    mast_inputs = Dict{String, TimeSeriesSource}()

    for result in train_results
        # We need to infer the input paths from the training results
        # Since training results don't store the original input paths directly,
        # we'll create reasonable defaults based on the mast names

        if !haskey(mast_inputs, result.target_mast)
            mast_inputs[result.target_mast] = TimeSeriesSource(
                "./reconstruct-single/$(result.target_mast).csv",
                "./reconstruct-single/$(result.target_mast).sensors.yaml"
            )
        end

        if !haskey(mast_inputs, result.source_mast)
            mast_inputs[result.source_mast] = TimeSeriesSource(
                "./reconstruct-single/$(result.source_mast).csv",
                "./reconstruct-single/$(result.source_mast).sensors.yaml"
            )
        end
    end

    # Create mast configurations with output paths
    masts = ReconstructCrossMast[]
    for (mast_name, input_source) in mast_inputs
        output_source = TimeSeriesSource(
            "./reconstruct-cross/$(mast_name)_reconstructed.csv",
            "./reconstruct-cross/$(mast_name)_reconstructed.sensors.yaml"
        )

        push!(masts, ReconstructCrossMast(
            name = mast_name,
            input = input_source,
            output = output_source
        ))
    end

    return sort(masts, by = m -> m.name)
end

"""
    create_training_metadata(train_results_dict::Dict{String, Any}, train_results_path::String)::Dict{String, Any}

Create metadata dictionary from training results.
"""
function create_training_metadata(train_results_dict::Dict{String, Any}, train_results_path::String)::Dict{String, Any}
    metadata = Dict{String, Any}(
        "training_date" => string(now()),
        "train_results_file" => train_results_path
    )

    # Add summary statistics if available
    if haskey(train_results_dict, "mast_pairs")
        mast_pairs = train_results_dict["mast_pairs"]
        metadata["total_mast_pairs"] = length(mast_pairs)

        # Count qualified pairs
        qualified_speed = 0
        qualified_direction = 0

        for pair in mast_pairs
            if haskey(pair, "windspeed_model_file") && pair["windspeed_model_file"] !== nothing
                qualified_speed += 1
            end
            if haskey(pair, "winddirection_model_file") && pair["winddirection_model_file"] !== nothing
                qualified_direction += 1
            end
        end

        metadata["qualified_speed_pairs"] = qualified_speed
        metadata["qualified_direction_pairs"] = qualified_direction
    end

    return metadata
end

"""
    print_recommendation_summary(priority_levels::Vector{ReconstructionPriority}, output_path::String)

Print a summary of the reconstruction recommendations.
"""
function print_recommendation_summary(priority_levels::Vector{ReconstructionPriority}, output_path::String)
    println("\n✅ Generated reconstruction configuration: $output_path")
    println("\n📊 Reconstruction Summary:")

    total_jobs = sum(length(level.jobs) for level in priority_levels)
    println("  Total reconstruction jobs: $total_jobs")

    for level in priority_levels
        level_name = if level.priority_level == 1
            "Excellent (≥0.7 correlation)"
        elseif level.priority_level == 2
            "Good (≥0.5 correlation)"
        else
            "Acceptable (≥0.3 correlation)"
        end

        println("  Priority $(level.priority_level) - $level_name: $(length(level.jobs)) jobs")

        for job in level.jobs
            variables_str = join(job.variables, ", ")
            println("    $(job.target_mast) ← $(job.source_mast) ($(variables_str), r=$(round(job.speed_correlation, digits=3)))")
        end
    end

    println("\nNext steps:")
    println("  1. Review and edit $output_path if needed")
    println("  2. Run: julia bin/CleanMast.jl process reconstruct-cross $output_path")
end

end # module
