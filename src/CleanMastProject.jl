module CleanMastProject

include("./CleanMastUtils.jl")
export CleanMastUtils

module Types
  include("./Types/Utils.jl")
  export Utils
  include("./Types/SensorColumns.jl")
  export SensorColumns
  include("./Types/MastTimeSeries.jl")
  export MastTimeSeries
  include("./Types/CleanRules.jl")
  export CleanRules
  include("./Types/ParseSensorsConfig.jl")
  export ParseSensorsConfig
  include("./Types/ProcessCleanConfig.jl")
  export ProcessCleanConfig
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
  include("./Types/AnalyzeConfiguration.jl")
  export AnalyzeConfiguration
  include("./Types/AnalyzeENConfiguration.jl")
  export AnalyzeENConfiguration
  include("./Types/AnalyzeReconstructSingleConfiguration.jl")
  export AnalyzeReconstructSingleConfiguration
end

export Types

module ParseSensors
  include("./ParseSensors/ColumnParser.jl")
  include("./ParseSensors/FileProcessor.jl")
  include("./ParseSensors/DataFrameProcessor.jl")
  include("./ParseSensors/CommandParseSensors.jl")
  export ColumnParser, FileProcessor, DataFrameProcessor, CommandParseSensors
end
export ParseSensors

include("./CleanMastConfig.jl");
export CleanMastConfig

module DataClean
  module Rules
    include("./DataClean/Rules/ProcessTypes.jl")
    include("./DataClean/Rules/ProcessRange.jl")
    include("./DataClean/Rules/ProcessIcing.jl")
    include("./DataClean/Rules/ProcessLayerDiff.jl")
    include("./DataClean/Rules/Process.jl")
    export Process, ProcessTypes, ProcessIcing, ProcessRange, ProcessLayerDiff
  end
  export Rules
  
  include("./DataClean/ProcessCleanCommand.jl")
  include("./DataClean/RecommendProcessCleanCommand.jl")
  export ProcessCleanCommand, RecommendProcessCleanCommand
end
export DataClean

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
include("./ReconstructMeso.jl")
export ReconstructMeso

include("./RepresentativeYear.jl")
export RepresentativeYear

include("./AnalyzeTimeSeries.jl")
export AnalyzeTimeSeries

include("./AnalyzeReconstructSingle.jl")
export AnalyzeReconstructSingle

module AnalyzeEN
  include("./AnalyzeEN/WindSpeed.jl")
  include("./AnalyzeEN/CalculateAnalyzeEN.jl")
  include("./AnalyzeEN/WindSpeedMatrixSerialization.jl")
  export WindSpeedMatrixSerialization, WindSpeed, CalculateAnalyzeEN
end
export AnalyzeEN

module Command
  include("./Command/CheckConfig.jl")
  include("./Command/CleanFiles.jl")
  include("./Command/TowerShading.jl")
  include("./Command/ReconstructSingleMast.jl")
  include("./Command/TrainMesoModel.jl")
  include("./Command/ReconstructMeso.jl")
  include("./Command/RepresentativeYearCalibration.jl")
  include("./Command/QuickStart.jl")
  include("./Command/AnalyzeTimeSeriesCommand.jl")
  include("./Command/WtTimeSeries.jl")
  include("./Command/ProcessAll.jl")
  include("./Command/GenerateTimeSeriesReport.jl")
  include("./Command/AnalyzeEN.jl")
  include("./Command/AnalyzeReconstructSingle.jl")
  export CheckConfig, CleanFiles, TowerShading, 
         ReconstructSingleMast, TrainMesoModel, ReconstructMeso, RepresentativeYearCalibration, 
         QuickStart, ProcessAll, AnalyzeTimeSeriesCommand, WtTimeSeries,
         GenerateTimeSeriesReport, AnalyzeEN, AnalyzeReconstructSingle
end
export Command
include("./CleanMastCli.jl")
export CleanMastCli

end
