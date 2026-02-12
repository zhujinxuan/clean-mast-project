"""Validation utilities for fill-heights configuration.

This module provides runtime validation for HeightReference configurations
against actual sensor metadata in timeseries data.

Functions:
    _build_sensor_column_map: Build column name to SensorColumn mapping
    _validate_references: Validate all HeightReference configurations
    _validate_single_reference: Validate a single HeightReference

These functions are used by the fill_heights CLI commands to ensure
reference configurations match actual sensor metadata before processing.
"""

from ...models.sensor import SensorColumn
from ..config import MastFillConfig, HeightReference


def _build_sensor_column_map(timeseries) -> dict[str, SensorColumn]:
    """Build a mapping from column names to SensorColumn metadata.

    Args:
        timeseries: TimeSeriesData containing sensor metadata

    Returns:
        Dictionary mapping column_name to SensorColumn
    """
    return {sensor.column_name: sensor for sensor in timeseries.sensors}


def _validate_references(timeseries, mast_config: MastFillConfig) -> None:
    """Validate HeightReference configurations against actual sensor metadata.

    This function performs runtime validation to ensure that all reference
    configurations point to valid sensors in the timeseries data. It checks:
    1. Reference column exists in timeseries
    2. Reference sensor_type matches expected type (WindSpeed/WindDirection)
    3. Reference height matches sensor height within tolerance

    Args:
        timeseries: Loaded TimeSeriesData with sensor metadata
        mast_config: MastFillConfig containing WS and WD fill configurations

    Raises:
        ValueError: If any validation fails, with all errors collected
    """
    errors: list[str] = []
    column_map = _build_sensor_column_map(timeseries)

    # Validate wind speed references
    for ws_config in mast_config.windspeed:
        for ref in ws_config.references:
            ref_errors = _validate_single_reference(
                ref=ref,
                expected_sensor_type="WindSpeed",
                column_map=column_map,
                target_info=f"WS config '{ws_config.target_column}'"
            )
            errors.extend(ref_errors)

    # Validate wind direction references
    for wd_config in mast_config.winddirection:
        for ref in wd_config.references:
            ref_errors = _validate_single_reference(
                ref=ref,
                expected_sensor_type="WindDirection",
                column_map=column_map,
                target_info=f"WD config '{wd_config.target_column}'"
            )
            errors.extend(ref_errors)

    # Raise all collected errors at once
    if errors:
        error_msg = "Validation failed for HeightReference configurations:\n  - " + "\n  - ".join(errors)
        raise ValueError(error_msg)


def _validate_single_reference(
    ref: HeightReference,
    expected_sensor_type: str,
    column_map: dict[str, SensorColumn],
    target_info: str,
) -> list[str]:
    """Validate a single HeightReference against sensor metadata.

    Args:
        ref: HeightReference to validate
        expected_sensor_type: Expected sensor type (WindSpeed or WindDirection)
        column_map: Mapping from column names to SensorColumn
        target_info: Info string for error messages (e.g., "WS config 'WS_100m_fill:extrapolated'")

    Returns:
        List of error messages (empty if validation passes)
    """
    errors: list[str] = []

    # Check 1: Column exists in timeseries
    if ref.sensor.column_name not in column_map:
        errors.append(
            f"Reference '{ref.sensor.column_name}' not found in timeseries columns. "
            f"Available columns: {list(column_map.keys())}"
        )
        # Can't continue validation if column doesn't exist
        return errors

    sensor = column_map[ref.sensor.column_name]

    # Check 2: Sensor type matches expected type
    if sensor.sensor_type != expected_sensor_type:
        errors.append(
            f"Reference '{ref.sensor.column_name}' has sensor_type '{sensor.sensor_type}' "
            f"but expected '{expected_sensor_type}' for {target_info}"
        )

    # Check 3: Height matches (with 0.01m tolerance)
    height_diff = abs(ref.sensor.height - sensor.height)
    if height_diff >= 0.01:
        errors.append(
            f"Reference height {ref.sensor.column_name}m does not match sensor height "
            f"{sensor.height}m (diff={height_diff:.2f}m) for column '{ref.sensor.column_name}'"
        )

    return errors
