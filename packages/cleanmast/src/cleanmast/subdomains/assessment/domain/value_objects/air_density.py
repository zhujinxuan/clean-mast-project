"""Air density calculation for wind energy analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, domain-001-sensor-access, data-001-symbol-columns
Compliance: Subdomain layout ✓ | Value Object ✓ | Sensor-based access ✓ | No column name patterns ✓
Description: Air density calculation using sensor type metadata (NOT column name patterns)
"""

import math
from typing import Any

from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData

# Constants for air density calculation
GAS_CONSTANT_DRY_AIR = 287.05  # J/(kg·K), specific gas constant for dry air
STANDARD_AIR_DENSITY = 1.225  # kg/m³ at 15°C and 1013.25 hPa
KELVIN_OFFSET = 273.15  # Conversion from Celsius to Kelvin
HPA_TO_PA = 100  # Conversion from hectopascals to pascals
PA_TO_HPA = 0.01  # Conversion from pascals to hectopascals


def _is_valid_mean(value: Any) -> bool:
    """Check if a mean value is valid (numeric and not NaN)."""
    return isinstance(value, (int, float)) and not (isinstance(value, float) and math.isnan(value))


def _normalize_temperature(temp_value: float) -> float:
    """Normalize temperature to Kelvin.

    If value is below 100, assumes Celsius and converts to Kelvin.
    If value is 100 or above, assumes already in Kelvin.
    """
    if temp_value < 100:
        # Celsius to Kelvin
        return temp_value + KELVIN_OFFSET
    return temp_value


def _normalize_pressure(pressure_value: float) -> float:
    """Normalize pressure to Pascals.

    If value is below 10000, assumes hPa and converts to Pa.
    If value is 10000 or above, assumes already in Pa.
    """
    if pressure_value < 10000:
        # hPa to Pa
        return pressure_value * HPA_TO_PA
    return pressure_value


def calculate_air_density(data: TimeSeriesData) -> float:
    """Calculate air density from temperature and pressure data.

    Uses the ideal gas law: ρ = P / (R * T)
    where:
    - ρ = air density (kg/m³)
    - P = pressure (Pa)
    - R = specific gas constant for dry air (287.05 J/(kg·K))
    - T = temperature (K)

    Finds temperature and pressure sensors by their sensor_type metadata
    (NOT by pattern matching on column names - that is the anti-pattern).

    Args:
        data: TimeSeriesData containing DataFrame and sensor metadata

    Returns:
        Average air density (kg/m³). Returns 1.225 if temp/pressure not found.
    """
    df = data.df
    sensors = data.sensors

    # Find sensors by TYPE (not column name pattern!)
    temp_sensor = next(
        (s for s in sensors if s.sensor_type == "Temperature" and s.stat_type == "avg"),
        None,
    )
    pressure_sensor = next(
        (s for s in sensors if s.sensor_type == "Pressure" and s.stat_type == "avg"),
        None,
    )

    # Fallback to standard air density if sensors not found
    if temp_sensor is None or pressure_sensor is None:
        return STANDARD_AIR_DENSITY

    temp_col = temp_sensor.column_name
    pressure_col = pressure_sensor.column_name

    # Validate columns exist
    columns = df.columns
    if temp_col not in columns or pressure_col not in columns:
        return STANDARD_AIR_DENSITY

    try:
        # Get mean values (Polars .mean() automatically skips nulls)
        temp_mean = df[temp_col].mean()
        pressure_mean = df[pressure_col].mean()

        # Check for invalid: None, non-numeric, or NaN
        if not _is_valid_mean(temp_mean) or not _is_valid_mean(pressure_mean):
            return STANDARD_AIR_DENSITY

        # Normalize units - safe to cast now that we've validated
        temp_k = _normalize_temperature(float(temp_mean))
        pressure_pa = _normalize_pressure(float(pressure_mean))

        # Calculate air density using ideal gas law
        air_density = pressure_pa / (GAS_CONSTANT_DRY_AIR * temp_k)

        return air_density
    except (TypeError, ValueError, ZeroDivisionError):
        # Return standard value on any calculation error
        return STANDARD_AIR_DENSITY


def convert_to_standard_air_density(wind_speed: float, actual_density: float) -> float:
    """Convert wind speed to standard air density equivalent.

    Formula: v_std = v * sqrt(ρ_actual / ρ_std)

    Args:
        wind_speed: Wind speed at actual air density (m/s)
        actual_density: Actual air density (kg/m³)

    Returns:
        Wind speed equivalent at standard air density (m/s)
    """
    return wind_speed * math.sqrt(actual_density / STANDARD_AIR_DENSITY)


def calculate_air_density_for_height(
    height: float, reference_density: float, reference_height: float
) -> float:
    """Extrapolate air density from a reference height to target height.

    Uses the barometric formula for density extrapolation.

    Formula:
        ρ = ρ_ref * exp(-g * (h - h_ref) / (R * (288.15 - 0.0065 * h_ref)))
    where:
    - g = 9.81 m/s² (gravitational acceleration)
    - R = 287.05 J/(kg·K) (specific gas constant for dry air)
    - 288.15 K = temperature at sea level in standard atmosphere
    - 0.0065 K/m = temperature lapse rate

    Args:
        height: Target height (m)
        reference_density: Air density at reference height (kg/m³)
        reference_height: Reference height (m)

    Returns:
        Extrapolated air density at target height (kg/m³)
    """
    return reference_density * math.exp(
        -9.81 * (height - reference_height) / (287.05 * (288.15 - 0.0065 * reference_height))
    )
