module RepresentativeYear

using DataFrames
using Dates
import ..Utils: show_as_dataframe
using ..Sector: DirectionSector
using ..MastTimeSeries: TimeSeriesData, SensorColumn

struct DirectionalCalibration
    direction_sector:: DirectionSector  # Center of direction sector (0 for N, 22.5 for NNE, etc.)
    slope::Float64            # Calibration slope for this direction
    meso_speed_diff::Float64  # Difference in meso speeds (rep_year - training_range)
end

struct CalibrationEachWSSensor
    target_sensor::SensorColumn  # The sensor being calibrated
    meso_direction_sensor::SensorColumn  # The meso direction sensor
    directional_calibrations::Vector{DirectionalCalibration}
end
show_as_dataframe(cal::CalibrationEachWSSensor) = DataFrame(
    target_sensor = [cal.target_sensor.columnName for _ in cal.directional_calibrations],
    meso_direction_sensor = [cal.meso_direction_sensor.columnName for _ in cal.directional_calibrations],
    sector = [directional_cal.direction_sector.name for directional_cal in cal.directional_calibrations],
    slope = [directional_cal.slope for directional_cal in cal.directional_calibrations],
    meso_speed_diff = [directional_cal.meso_speed_diff for directional_cal in cal.directional_calibrations]
)

struct CalibrationResults
    calibrations ::Vector{CalibrationEachWSSensor}
    reference_year::DateTime
end
function show_as_dataframe(cal::CalibrationResults) :: DataFrame
    dfs = vcat([show_as_dataframe(calibration) for calibration in cal.calibrations]...)
    dfs.reference_year = [cal.reference_year for _ in dfs.target_sensor]
    return dfs
end

export DirectionalCalibration, CalibrationResults, CalibrationEachWSSensor

end 