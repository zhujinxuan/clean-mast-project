module ProcessAll

using ...DataClean.ProcessCleanCommand
using ...DataClean.RecommendProcessCleanCommand
using ...TowerShading.CommandTowerShading
using ...TowerShading.RecommendTowerShadingCommand
using ...ReconstructSingleMast.CommandReconstructSingle
using ...ReconstructSingleMast.RecommendReconstructSingleCommand
using ...TrainReconstructCross.RecommendTrainReconstructCrossCommand
using ...TrainReconstructCross.TrainReconstructCrossCommand
using ...ReconstructCross.RecommendReconstructCrossCommand
using ...ReconstructCross.ProcessReconstructCrossCommand
using ...TrainMeso.CommandTrainMeso
using ...TrainMeso.RecommendTrainMesoCommand
using ...ReconstructMeso.CommandReconstructMeso
using ...ReconstructMeso.RecommendReconstructMesoCommand
using ...RepresentativeYear.CommandRepresentativeYear
using ...RepresentativeYear.RecommendRepresentativeYearCommand
using ...WTTimeSeries.CommandWtTimeSeries
using ...WTTimeSeries.RecommendWtTimeSeriesCommand

export execute

"""
    execute(dir::String)

Execute all processing steps in sequence:
1. Clean data
2. Tower shading
3. Reconstruct single mast
4. Train cross-mast models
5. Reconstruct cross-mast
6. Train meso models
7. Reconstruct meso
8. Representative year calibration

# Arguments
- `dir::String`: Project directory containing config.yaml
"""
function execute(dir::String)

    println("Processing all steps for project: $dir")
    
    println("\n0. Recommending clean data config...")
    RecommendProcessCleanCommand.execute(dir)

    println("\n1. Cleaning data...")
    ProcessCleanCommand.execute(joinpath(dir, "process-clean.toml"))
    
    println("\n2. Recommending tower shading config...")
    RecommendTowerShadingCommand.execute(dir)
    
    println("\n3. Processing tower shading...")
    CommandTowerShading.execute(joinpath(dir, "tower-shading.toml"))
    
    println("\n4. Recommending reconstruct single config...")
    RecommendReconstructSingleCommand.execute(dir)
    
    println("\n5. Reconstructing single mast data...")
    CommandReconstructSingle.execute(joinpath(dir, "reconstruct-single.toml"))

    println("\n6. Recommending train cross-mast config...")
    RecommendTrainReconstructCrossCommand.execute(dir)

    println("\n7. Training cross-mast models...")
    TrainReconstructCrossCommand.execute(joinpath(dir, "train-reconstruct-cross.toml"))

    println("\n8. Recommending reconstruct cross-mast config...")
    RecommendReconstructCrossCommand.execute(joinpath(dir, "train-reconstruct-cross", "train-results.toml"), dir)

    println("\n9. Reconstructing cross-mast data...")
    ProcessReconstructCrossCommand.execute(joinpath(dir, "reconstruct-cross.toml"))

    println("\n10. Recommending train meso config...")
    RecommendTrainMesoCommand.execute(dir)
    
    println("\n11. Training mesoscale models...")
    CommandTrainMeso.execute(joinpath(dir, "train-meso.toml"))

    println("\n12. Recommending reconstruct meso config...")
    RecommendReconstructMesoCommand.execute(dir)

    println("\n13. Reconstructing with mesoscale data...")
    CommandReconstructMeso.execute(joinpath(dir, "reconstruct-meso.toml"))

    println("\n14. Recommending representative year config...")
    RecommendRepresentativeYearCommand.execute(dir)

    println("\n15. Calibrating to representative year...")
    CommandRepresentativeYear.execute(joinpath(dir, "representative-year.toml"))

    println("\n16. Recommending wt-timeseries config...")
    RecommendWtTimeSeriesCommand.execute(dir)

    println("\n17. Producing MeteoDyn WT time series data...")
    CommandWtTimeSeries.execute(joinpath(dir, "wt-timeseries.toml"))
    
    println("\nComplete processing pipeline finished successfully!")
end

end # module 