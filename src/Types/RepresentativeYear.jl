module RepresentativeYear

using DataFrames
using Dates
using ..MastTimeSeries: TimeSeriesData, SensorColumn
using ..ReconstructMeso: TrainingTimeRange

struct DirectionalCalibration
    direction_center::Float64  # Center of direction sector (0 for N, 22.5 for NNE, etc.)
    slope::Float64            # Calibration slope for this direction
    meso_speed_diff::Float64  # Difference in meso speeds (rep_year - training_range)
end

struct CalibrationResults
    reference_year::DateTime
    target_sensor::SensorColumn  # The sensor being calibrated
    directional_calibrations::Vector{DirectionalCalibration}
    is_calibration_needed::Bool
end


export DirectionalCalibration, CalibrationResults

end 