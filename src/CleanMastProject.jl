module CleanMastProject

module Types
  include("./Types/Utils.jl")
  export Utils
  include("./Types/MastTimeSeries.jl")
  export MastTimeSeries
  include("./Types/CleanRules.jl")
  export CleanRules
  include("./Types/CleanMastConfig.jl")
  export CleanMastConfig
  include("./Types/Sector.jl")
  export Sector
  include("./Types/MastReferenceModel.jl")
  export MastReferenceModel
  module DirectionReferenceModel
    include("./Types/DirectionReferenceModel/DirectionOffset.jl")
    export DirectionOffset
  end 
  export DirectionReferenceModel
  module SpeedReferenceModel
    include("./Types/SpeedReferenceModel/SectorizedRegression.jl")
    export SectorizedRegression
  end
  export SpeedReferenceModel
  include("./Types/ReconstructSingleMast.jl")
  export ReconstructSingleMast
  include("./Types/RepresentativeYear.jl")
  export RepresentativeYear
  include("./Types/TurbulenceIntensity.jl")
  export TurbulenceIntensity
end
export Types
include("./SensorFormats.jl")
export SensorFormats

include("./CleanMastConfig.jl");
export CleanMastConfig

include("./MastTimeSeries.jl")
export MastTimeSeries

module CleanMastRules
  include("./CleanMastRules/ProcessTypes.jl")
  include("./CleanMastRules/ProcessRange.jl")
  include("./CleanMastRules/ProcessIcing.jl")
  include("./CleanMastRules/ProcessLayerDiff.jl")
  include("./CleanMastRules/Process.jl")
  export Process,ProcessTypes, ProcessIcing, ProcessRange, ProcessLayerDiff
end
export CleanMastRules


include("./TowerShading.jl")
export TowerShading

module TimeSeriesProcessing
  include("./TimeSeriesProcessing/Interpolation.jl")
  include("./TimeSeriesProcessing/Regularization.jl")
  include("./TimeSeriesProcessing/TimeRangeProcessor.jl")
  export Interpolation, Regularization, TimeRangeProcessor
end
export TimeSeriesProcessing

module ReconstructSingleMast
  include("./ReconstructSingleMast/WindSpeedTraining.jl")
  include("./ReconstructSingleMast/DirectionTraining.jl")
  include("./ReconstructSingleMast/ProcessData.jl")
  export ProcessData, WindSpeedTraining, DirectionTraining
end
export ReconstructSingleMast

module WindSpeedModels
  include("./WindSpeedModels/SectorizedRegressionTraining.jl")
  include("./WindSpeedModels/SectorizedRegressionReconstruction.jl")
  export SectorizedRegressionTraining, SectorizedRegressionReconstruction
end
export WindSpeedModels
module WindDirectionModels
  include("./WindDirectionModels/DirectionOffsetTraining.jl")
  include("./WindDirectionModels/DirectionOffsetReconstruction.jl")
  export DirectionOffsetTraining, DirectionOffsetReconstruction
end
export WindDirectionModels

include("./TrainMeso.jl")
export TrainMeso
include("./MergeReconstructMeso.jl")
export MergeReconstructMeso

include("./RepresentativeYear.jl")
export RepresentativeYear

include("./TurbulenceIntensity.jl")
export TurbulenceIntensity

module Command
  include("./Command/CheckConfig.jl")
  include("./Command/CheckSensors.jl")
  include("./Command/CleanData.jl")
  include("./Command/CleanFiles.jl")
  include("./Command/TowerShading.jl")
  include("./Command/ReconstructSingleMast.jl")
  include("./Command/TrainMesoModel.jl")
  include("./Command/ReconstructMeso.jl")
  include("./Command/RepresentativeYearCalibration.jl")
  include("./Command/TurbulenceIntensity.jl")
  include("./Command/QuickStart.jl")
  include("./Command/ProcessAll.jl")
  export CheckConfig, CheckSensors, CleanData, CleanFiles, TowerShading, 
         ReconstructSingleMast, TrainMesoModel, ReconstructMeso, RepresentativeYearCalibration, 
         TurbulenceIntensity, QuickStart, ProcessAll
end
export Command
include("./CleanMastCli.jl")
export CleanMastCli

end
