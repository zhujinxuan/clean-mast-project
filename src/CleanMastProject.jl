module CleanMastProject

module Types
  include("./Types/CleanRules.jl")
  export CleanRules
  include("./Types/CleanMastConfig.jl")
  export CleanMastConfig
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

module Command
  include("./Command/CheckConfig.jl")
  include("./Command/CheckSensors.jl")
  include("./Command/CleanData.jl")
  export CheckConfig, CheckSensors, CleanData
end
export Command
include("./TowerShading.jl")
export TowerShading

end
