"""
    ReportFrozenPeriod.jl

Module for detecting and reporting frozen sensor periods in wind mast data.
Supports multiple threshold configurations (heated and non-heated sensors).
"""
module ReportFrozenPeriod

include("ReportFrozenPeriod/PeriodOperations.jl")
include("ReportFrozenPeriod/FrozenDetection.jl")
include("ReportFrozenPeriod/MonthlyStatistics.jl")
include("ReportFrozenPeriod/ReportGeneration.jl")
include("ReportFrozenPeriod/ReportFrozenPeriodCommand.jl")
include("ReportFrozenPeriod/RecommendReportFrozenCommand.jl")

using .PeriodOperations
using .FrozenDetection
using .MonthlyStatistics
using .ReportGeneration
using .ReportFrozenPeriodCommand
using .RecommendReportFrozenCommand

export PeriodOperations

end # module
