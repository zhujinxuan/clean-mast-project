module CleanMastProject
  include("./CleanMastConfig.jl");
  export CleanMastConfig

  include("./MastTimeSeries.jl")
  export MastTimeSeries

  module CleanMastRules
    include("./CleanMastRules/Rules.jl")
    include("./CleanMastRules/ProcessTypes.jl")
    include("./CleanMastRules/ProcessRange.jl")
    include("./CleanMastRules/ProcessIcing.jl")
    include("./CleanMastRules/ProcessLayerDiff.jl")
    include("./CleanMastRules/Process.jl")
    export Rules,Process,ProcessTypes, ProcessIcing, ProcessRange, ProcessLayerDiff
  end
  export CleanMastRules
end
