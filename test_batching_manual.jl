#!/usr/bin/env julia
"""
Manual test script to verify job batching with real configuration.
This script loads a real reconstruct-cross.toml and shows how jobs are batched.
"""

using Pkg
Pkg.activate(".")

using CleanMastProject.Types.ReconstructCrossConfig: from_dict, ReconstructCrossConfiguration
using CleanMastProject.ReconstructCross.ProcessReconstructCrossCommand: create_job_batches
using CleanMastProject.CleanMastUtils: load_dict

# Check if config file exists
config_path = "projects/tgl-group1-10masts/reconstruct-cross.toml"

if !isfile(config_path)
    println("⚠️  Config file not found: $config_path")
    println("Please provide a valid reconstruct-cross.toml path")
    exit(1)
end

println("📋 Loading configuration from: $config_path")
config_dict = load_dict(config_path)
config = from_dict(ReconstructCrossConfiguration, config_dict)

println("\n" * "="^80)
println("Reconstruction Configuration Analysis")
println("="^80)

println("\n📊 Masts: $(length(config.masts))")
for mast in config.masts
    println("  - $(mast.name)")
end

total_jobs = sum(length(level.jobs) for level in config.reconstruction_priorities)
println("\n📦 Total jobs across all priority levels: $total_jobs")

for priority_level in config.reconstruction_priorities
    println("\n" * "-"^80)
    println("🎯 Priority Level $(priority_level.priority_level)")
    println("-"^80)
    println("Total jobs in this level: $(length(priority_level.jobs))")

    # Create batches
    batches = create_job_batches(priority_level.jobs)

    println("\n📦 Created $(length(batches)) batch(es) for parallel execution")
    println("   → Jobs in each batch can run simultaneously")
    println("   → Different batches run sequentially")

    # Analyze batch composition
    for (i, batch) in enumerate(batches)
        targets = unique([job.target_mast for job in batch])
        println("\n  Batch $i: $(length(batch)) job(s)")
        println("    Targets: $(join(targets, ", "))")

        # Show first few jobs in batch
        for (j, job) in enumerate(batch)
            if j <= 3 || j == length(batch)
                println("      $(j). $(job.target_mast) ← $(job.source_mast) (r=$(round(job.speed_correlation, digits=3)))")
            elseif j == 4 && length(batch) > 4
                println("      ... ($(length(batch) - 4) more)")
            end
        end

        # Verify uniqueness
        target_set = Set([job.target_mast for job in batch])
        if length(target_set) != length(batch)
            println("    ⚠️  WARNING: Duplicate targets detected in batch!")
        else
            println("    ✅ All targets unique - safe for parallel execution")
        end
    end

    # Show parallelization benefit
    sequential_time = length(priority_level.jobs)
    parallel_time = length(batches)
    speedup = sequential_time / parallel_time

    println("\n  ⚡ Parallelization benefit:")
    println("    Sequential execution: ~$(sequential_time) time units")
    println("    Parallel execution:   ~$(parallel_time) time units")
    println("    Potential speedup:    $(round(speedup, digits=2))x")
end

println("\n" * "="^80)
println("✅ Batching analysis complete!")
println("="^80)
