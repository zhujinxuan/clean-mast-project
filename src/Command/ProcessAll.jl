module ProcessAll

using ...Types.CleanMastConfig
using ...CleanMastConfig
using ...Command.CleanData
using ...Command.TowerShading
using ...Command.ReconstructSingleMast
using ...Command.TrainMesoModel
using ...Command.ReconstructMeso
using ...Command.RepresentativeYearCalibration
using ...Command.WtTimeSeries

export execute

"""
    execute(dir::String)

Execute all processing steps in sequence:
1. Clean data
2. Tower shading
3. Reconstruct single mast
4. Train meso models
5. Reconstruct meso
6. Representative year calibration

# Arguments
- `dir::String`: Project directory containing config.yaml
"""
function execute(dir::String)
    println("\nStarting complete processing pipeline...")
    
    println("\n1. Cleaning data...")
    CleanData.execute(dir)
    
    println("\n2. Processing tower shading...")
    TowerShading.execute(dir)
    
    println("\n3. Reconstructing single mast data...")
    ReconstructSingleMast.execute(dir)
    
    println("\n4. Training mesoscale models...")
    TrainMesoModel.execute(dir)
    
    println("\n5. Reconstructing with mesoscale data...")
    ReconstructMeso.execute(dir)
    
    println("\n6. Calibrating to representative year...")
    RepresentativeYearCalibration.execute(dir)

    println("\n7. Producing MeteoDyn WT time series data...")
    WtTimeSeries.execute(dir)
    
    println("\nComplete processing pipeline finished successfully!")
end

end # module 