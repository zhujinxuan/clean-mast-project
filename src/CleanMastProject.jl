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
  include("./Types/ReconstructMeso.jl")
  export ReconstructMeso
  include("./Types/ReconstructSingleMast.jl")
  export ReconstructSingleMast
end
export Types

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

module ReconstructSingleMast
  include("./ReconstructSingleMast/WindSpeedTraining.jl")
  include("./ReconstructSingleMast/DirectionTraining.jl")
  include("./ReconstructSingleMast/ProcessData.jl")
  export ProcessData, WindSpeedTraining, DirectionTraining
end
export ReconstructSingleMast

module Command
  include("./Command/CheckConfig.jl")
  include("./Command/CheckSensors.jl")
  include("./Command/CleanData.jl")
  include("./Command/CleanFiles.jl")
  include("./Command/TowerShading.jl")
  include("./Command/ReconstructSingleMast.jl")
  include("./Command/QuickStart.jl")
  export CheckConfig, CheckSensors, CleanData, CleanFiles, TowerShading, ReconstructSingleMast, QuickStart
end
export Command

include("./ReconstructMeso.jl")
export ReconstructMeso

end
