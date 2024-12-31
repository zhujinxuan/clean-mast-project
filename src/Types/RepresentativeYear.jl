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
    meso_ratio::Float64  # Ratio of mean speeds (training_range / full_period)
    directional_calibrations::Vector{DirectionalCalibration}
    is_calibration_needed::Bool
end

# Constants for direction sectors
const DIRECTION_SECTORS = [
    (name="N", center=0.0),
    (name="NNE", center=22.5),
    (name="NE", center=45.0),
    (name="ENE", center=67.5),
    (name="E", center=90.0),
    (name="ESE", center=112.5),
    (name="SE", center=135.0),
    (name="SSE", center=157.5),
    (name="S", center=180.0),
    (name="SSW", center=202.5),
    (name="SW", center=225.0),
    (name="WSW", center=247.5),
    (name="W", center=270.0),
    (name="WNW", center=292.5),
    (name="NW", center=315.0),
    (name="NNW", center=337.5)
]

export DirectionalCalibration, CalibrationResults, DIRECTION_SECTORS

end 