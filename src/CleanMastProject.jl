module CleanMastProject

include("./CleanMastUtils.jl")
export CleanMastUtils

include("./TypstUtils.jl")
export TypstUtils

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
  include("./Types/ReportCleanConfig.jl")
  export ReportCleanConfig
  include("./Types/ReportRecoveryConfig.jl")
  export ReportRecoveryConfig
  include("./Types/ReportRecoveryData.jl")
  export ReportRecoveryData
  include("./Types/TowerShadingConfig.jl")
  export TowerShadingConfig
  include("./Types/ReconstructSingleConfig.jl")
  export ReconstructSingleConfig
  include("./Types/TrainMesoConfig.jl")
  export TrainMesoConfig
  include("./Types/ReconstructMesoConfig.jl")
  export ReconstructMesoConfig
  include("./Types/RepresentativeYearConfig.jl")
  include("./Types/TrainMesoResultsTypes.jl")
  export TrainMesoResultsTypes

  export RepresentativeYearConfig
  include("./Types/WtTimeSeriesConfig.jl")
  export WtTimeSeriesConfig
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
  include("./Types/TrainReconstructCrossConfig.jl")
  export TrainReconstructCrossConfig
  include("./Types/AnalyzeReconstructCrossConfig.jl")
  export AnalyzeReconstructCrossConfig
  include("./Types/CrossMastSpeedModels.jl")
  export CrossMastSpeedModels
  include("./Types/CrossMastDirectionModels.jl")
  export CrossMastDirectionModels
  include("./Types/CrossMastAnalysisResults.jl")
  export CrossMastAnalysisResults
  include("./Types/CrossMastTrainParams.jl")
  export CrossMastTrainParams
  include("./Types/ReconstructCrossConfig.jl")
  export ReconstructCrossConfig
  include("./Types/ReconstructCrossResults.jl")
  export ReconstructCrossResults
  include("./Types/ViolationData.jl")
  export ViolationData
  include("./Types/ReportCleanData.jl")
  export ReportCleanData
end

export Types

module TimeSeriesProcessing
  include("./TimeSeriesProcessing/Interpolation.jl")
  include("./TimeSeriesProcessing/Regularization.jl")
  include("./TimeSeriesProcessing/IntervalDetection.jl")
  include("./TimeSeriesProcessing/MeasurementPeriodCalculator.jl")
  export Interpolation, Regularization, IntervalDetection, MeasurementPeriodCalculator
end
export TimeSeriesProcessing

module ParseSensors
  include("./ParseSensors/ColumnParser.jl")
  include("./ParseSensors/FileProcessor.jl")
  include("./ParseSensors/DataFrameProcessor.jl")
  include("./ParseSensors/CommandParseSensors.jl")
  include("./ParseSensors/RecommendParseSensorsCommand.jl")
  export ColumnParser, FileProcessor, DataFrameProcessor, CommandParseSensors, RecommendParseSensorsCommand
end
export ParseSensors

module DataClean
  module Rules
    include("./DataClean/Rules/ProcessTypes.jl")
    include("./DataClean/Rules/ProcessRange.jl")
    include("./DataClean/Rules/ProcessIcing.jl")
    include("./DataClean/Rules/ProcessLayerDiff.jl")
    include("./DataClean/Rules/ProcessAvailability.jl")
    include("./DataClean/Rules/Process.jl")
    export Process, ProcessTypes, ProcessIcing, ProcessRange, ProcessLayerDiff, ProcessAvailability
  end
  export Rules

  include("./DataClean/ProcessCleanCommand.jl")
  include("./DataClean/RecommendProcessCleanCommand.jl")
  export ProcessCleanCommand, RecommendProcessCleanCommand
end
export DataClean

module ReportClean
  include("./ReportClean/SensorInventoryReport.jl")
  include("./ReportClean/DataCoverageReport.jl")
  include("./ReportClean/ViolationAnalysisReport.jl")
  include("./ReportClean/RecommendReportCleanCommand.jl")
  include("./ReportClean/ReportCleanCommand.jl")
  include("./ReportClean/ReportAllCommand.jl")
  export SensorInventoryReport, DataCoverageReport, ViolationAnalysisReport
  export RecommendReportCleanCommand, ReportCleanCommand, ReportAllCommand
end
export ReportClean

module ReportRecovery
  include("./ReportRecovery/RecoveryAnalysis.jl")
  include("./ReportRecovery/RecoveryStatusReport.jl")
  include("./ReportRecovery/RecommendReportRecoveryCommand.jl")
  include("./ReportRecovery/ReportRecoveryCommand.jl")
  export RecoveryAnalysis, RecoveryStatusReport
  export RecommendReportRecoveryCommand, ReportRecoveryCommand
end
export ReportRecovery

module ReportReconstructSingle
  include("./ReportReconstructSingle/DataCoverage.jl")
  include("./ReportReconstructSingle/WindSpeedCorrelation.jl")
  include("./ReportReconstructSingle/WindDirectionDifference.jl")
  include("./ReportReconstructSingle/ReportGeneration.jl")
  include("./ReportReconstructSingle/ReportReconstructSingleAnalysis.jl")
  include("./ReportReconstructSingle/ReportReconstructSingleCommand.jl")
  include("./ReportReconstructSingle/RecommendReportReconstructSingleCommand.jl")
  export DataCoverage, WindSpeedCorrelation, WindDirectionDifference, ReportGeneration
  export ReportReconstructSingleAnalysis, ReportReconstructSingleCommand, RecommendReportReconstructSingleCommand
end
export ReportReconstructSingle

module TowerShading
  include("./TowerShading/Core.jl")
  include("./TowerShading/CommandTowerShading.jl")
  include("./TowerShading/RecommendTowerShadingCommand.jl")
  # Export command modules
  export CommandTowerShading, RecommendTowerShadingCommand, Core
end
export TowerShading


module ReconstructSingleMast
  include("./ReconstructSingleMast/WindSpeedTraining.jl")
  include("./ReconstructSingleMast/DirectionTraining.jl")
  include("./ReconstructSingleMast/ProcessData.jl")
  include("./ReconstructSingleMast/CommandReconstructSingle.jl")
  include("./ReconstructSingleMast/RecommendReconstructSingleCommand.jl")
  export ProcessData, WindSpeedTraining, DirectionTraining
  export CommandReconstructSingle, RecommendReconstructSingleCommand
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

module TrainMeso
  include("./TrainMeso/Core.jl")
  include("./TrainMeso/CommandTrainMeso.jl")
  include("./TrainMeso/RecommendTrainMesoCommand.jl")
  export CommandTrainMeso, RecommendTrainMesoCommand, Core
end
export TrainMeso
module ReconstructMeso
  include("./ReconstructMeso/Core.jl")
  include("./ReconstructMeso/CommandReconstructMeso.jl")
  include("./ReconstructMeso/RecommendReconstructMesoCommand.jl")
  export CommandReconstructMeso, RecommendReconstructMesoCommand, Core
end
export ReconstructMeso

module RepresentativeYear
  include("./RepresentativeYear/Analysis.jl")
  include("./RepresentativeYear/Core.jl")
  include("./RepresentativeYear/CommandRepresentativeYear.jl")
  include("./RepresentativeYear/RecommendRepresentativeYearCommand.jl")
  include("./RepresentativeYear/ReportGeneration.jl")
  include("./RepresentativeYear/ReportRepresentativeYearCommand.jl")
  export calibrate_to_representative_year
  export CommandRepresentativeYear, RecommendRepresentativeYearCommand
  export ReportGeneration, ReportRepresentativeYearCommand
  export Analysis
end
export RepresentativeYear
module WTTimeSeries
  include("./WTTimeSeries/Core.jl")
  include("./WTTimeSeries/CommandWtTimeSeries.jl")
  include("./WTTimeSeries/RecommendWtTimeSeriesCommand.jl")
  export CommandWtTimeSeries, RecommendWtTimeSeriesCommand, Core
end
export WTTimeSeries

module ReportTimeSeries
  include("./ReportTimeSeries/Utils.jl")
  include("./ReportTimeSeries/AirDensity.jl")
  include("./ReportTimeSeries/WindTemporal.jl")
  include("./ReportTimeSeries/Vertical.jl")
  include("./ReportTimeSeries/WindFrequency.jl")
  include("./ReportTimeSeries/WindRose.jl")
  include("./ReportTimeSeries/Turbulence.jl")
  include("./ReportTimeSeries/Weibull.jl")
  include("./ReportTimeSeries/FiftyYearsExtremeWind.jl")
  include("./ReportTimeSeries/TimeSeriesAnalysis.jl")
  include("./ReportTimeSeries/ReportTimeSeriesCommand.jl")
  include("./ReportTimeSeries/RecommendReportTimeSeriesMesoCommand.jl")
  include("./ReportTimeSeries/RecommendReportTimeSeriesRepCommand.jl")
  export Utils, AirDensity, WindTemporal, Vertical, WindFrequency, WindRose, Turbulence, Weibull, FiftyYearsExtremeWind
  export TimeSeriesAnalysis, ReportTimeSeriesCommand, RecommendReportTimeSeriesMesoCommand, RecommendReportTimeSeriesRepCommand
end
export ReportTimeSeries


module AnalyzeEN
  include("./AnalyzeEN/WindSpeed.jl")
  include("./AnalyzeEN/CalculateAnalyzeEN.jl")
  include("./AnalyzeEN/WindSpeedMatrixSerialization.jl")
  export WindSpeedMatrixSerialization, WindSpeed, CalculateAnalyzeEN
end
export AnalyzeEN

module TrainReconstructCross
  include("./TrainReconstructCross/DataCoverage.jl")
  include("./TrainReconstructCross/CrossMastSpeedCorrelation.jl")
  include("./TrainReconstructCross/CrossMastDirectionAnalysis.jl")
  include("./TrainReconstructCross/CrossMastSummary.jl")
  include("./TrainReconstructCross/TrainReconstructCrossCommand.jl")
  include("./TrainReconstructCross/RecommendTrainReconstructCrossCommand.jl")
  export DataCoverage, CrossMastSpeedCorrelation, CrossMastDirectionAnalysis, CrossMastSummary
  export TrainReconstructCrossCommand, RecommendTrainReconstructCrossCommand
end
export TrainReconstructCross

module AnalyzeReconstructCross
  include("./AnalyzeReconstructCross/AnalysisCore.jl")
  include("./AnalyzeReconstructCross/DataVisualization.jl")
  include("./AnalyzeReconstructCross/ReportGeneration.jl")
  include("./AnalyzeReconstructCross/CommandAnalyzeReconstructCross.jl")
  include("./AnalyzeReconstructCross/RecommendAnalyzeReconstructCrossCommand.jl")
  include("./AnalyzeReconstructCross/RecommendCrossMastReportCommand.jl")
  export AnalysisCore, DataVisualization, ReportGeneration
  export CommandAnalyzeReconstructCross, RecommendAnalyzeReconstructCrossCommand, RecommendCrossMastReportCommand
end
export AnalyzeReconstructCross

module ReportAllMasts
  include("./ReportAllMasts/ReportAllMastsCommand.jl")
  include("./ReportAllMasts/RecommendReportAllCommand.jl")
  export ReportAllMastsCommand, RecommendReportAllCommand
end
export ReportAllMasts

module ReconstructCross
  include("./ReconstructCross/RecommendReconstructCrossCommand.jl")
  include("./ReconstructCross/ProcessReconstructCrossCommand.jl")
  export RecommendReconstructCrossCommand, ProcessReconstructCrossCommand
end
export ReconstructCross

module Command
  include("./Command/QuickStart.jl")
  include("./Command/ProcessSteps.jl")
  include("./Command/AnalyzeEN.jl")
  include("./Command/CalculateAirDensityCommand.jl")
  export  QuickStart, ProcessSteps,
         AnalyzeEN, CalculateAirDensityCommand
end
export Command
include("./CleanMastCli.jl")
export CleanMastCli

end
