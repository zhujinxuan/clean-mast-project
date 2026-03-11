"""Pure helper functions for fill-heights operations.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Stateless utility functions for height filling operations

This module contains stateless utility functions used throughout the fill-heights
system. All functions are pure (no side effects, no external dependencies) making
them easy to test and reason about.
"""

from typing import Literal

import numpy as np

from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData


def get_existing_sensors(
    sensors: list[SensorColumn],
    sensor_type: Literal["WindSpeed", "WindDirection"]
) -> list[SensorColumn]:
    """Get sorted list of existing average sensors."""
    matching = [
        s for s in sensors
        if s.sensor_type == sensor_type and s.stat_type == "avg"
    ]
    return sorted(matching, key=lambda s: s.height)


def get_top_sensors(
    timeseries: TimeSeriesData,
    sensor_type: Literal["WindSpeed", "WindDirection"],
    n: int = 3
) -> list[SensorColumn]:
    """Get top N sensors sorted by height descending."""
    sensors = get_existing_sensors(timeseries.sensors, sensor_type)
    return sorted(sensors, key=lambda s: s.height, reverse=True)[:n]


def find_neighbor_sensors(
    target: float,
    sensors: list[SensorColumn]
) -> tuple[SensorColumn, SensorColumn]:
    """Find lower and higher neighbor sensors.

    Args:
        target: Target height to find neighbors for
        sensors: List of SensorColumn objects (should be sorted by height)

    Returns:
        Tuple of (lower_sensor, higher_sensor)

    Raises:
        ValueError: If cannot find valid neighbors for the target height
    """
    lower = max(
        [s for s in sensors if s.height < target],
        key=lambda s: s.height,
        default=None
    )
    higher = min(
        [s for s in sensors if s.height > target],
        key=lambda s: s.height,
        default=None
    )

    if lower is None or higher is None:
        raise ValueError(f"Cannot find neighbors for {target}m")

    return lower, higher


def create_fill_target_sensor(
    timeseries: TimeSeriesData,
    target_height: float,
    sensor_type: Literal["WindSpeed", "WindDirection"],
    method: Literal["interpolated", "extrapolated"]
) -> SensorColumn:
    """Create a SensorColumn for the fill target.

    Inherits metadata from nearest reference sensor:
    - sensor_direction: From nearest reference
    - unit: From nearest reference

    Generates column name: WS_{height}m_fill:{method} or WD_{height}m_fill:{method}
    """
    refs = get_existing_sensors(timeseries.sensors, sensor_type)
    if not refs:
        raise ValueError(f"No reference sensors for {sensor_type}")

    nearest = min(refs, key=lambda s: abs(s.height - target_height))

    prefix = "WS" if sensor_type == "WindSpeed" else "WD"
    column_name = f"{prefix}_{int(target_height)}m_fill:{method}"

    return SensorColumn(
        column_name=column_name,
        sensor_type=sensor_type,
        sensor_direction=nearest.sensor_direction,
        height=target_height,
        stat_type="avg",
        unit=nearest.unit,
    )


def calculate_interpolation_weights(
    target: float,
    lower: float,
    higher: float
) -> tuple[float, float]:
    """Calculate 1/distance weights for linear interpolation.

    Uses inverse-distance weighting, where closer reference points
    get higher weights. This is a standard approach in spatial
    interpolation.

    Returns:
        Tuple of (weight_lower, weight_higher) that sum to 1.0
    """
    dist_low = target - lower
    dist_high = higher - target
    total = (1 / dist_low) + (1 / dist_high)

    weight_low = (1 / dist_low) / total
    weight_high = (1 / dist_high) / total

    return weight_low, weight_high


def get_sensor_for_height(
    sensors: list[SensorColumn],
    sensor_type: Literal["WindSpeed", "WindDirection"],
    height: float
) -> SensorColumn | None:
    """Find sensor for given type and height."""
    for s in sensors:
        if (s.sensor_type == sensor_type and
            s.height == height and
            s.stat_type == "avg"):
            return s
    return None


def check_min_overlap(
    timeseries: TimeSeriesData,
    ref1_col: str,
    ref2_col: str,
    min_points: int = 1000
) -> bool:
    """Check if two columns have sufficient concurrent valid data."""
    df = timeseries.df
    valid_count = df.filter(
        df[ref1_col].is_not_null() & df[ref2_col].is_not_null()
    ).height
    return valid_count >= min_points


def degrees_to_vector(
    degrees: float | np.ndarray,
) -> tuple[float | np.ndarray, float | np.ndarray]:
    """Convert wind direction degrees to (u, v) vector components.

    Uses meteorological convention: direction FROM which wind blows.

    Vector components:
        u = East-West component (positive = East)
        v = North-South component (positive = North)

    Formulas:
        u = -sin(θ) where θ is in radians
        v = -cos(θ) where θ is in radians
    """
    theta_rad = np.radians(degrees)
    u = -np.sin(theta_rad)
    v = -np.cos(theta_rad)
    return u, v


def vector_to_degrees(
    u: float | np.ndarray,
    v: float | np.ndarray,
) -> float | np.ndarray:
    """Convert (u, v) vector components back to wind direction degrees.

    Uses atan2 to compute the angle from the vector, then converts
    to degrees and normalizes to [0, 360).
    """
    theta_rad = np.arctan2(-u, -v)
    degrees = np.degrees(theta_rad)
    return degrees % 360



def generate_target_column(
    sensor_type: Literal["WindSpeed", "WindDirection"],
    height: float,
    method: Literal["interpolated", "extrapolated"]
) -> str:
    """Generate standardized target column name.

    Creates a column name following the convention:
    - WindSpeed: WS_{height}m_fill:{method}
    - WindDirection: WD_{height}m_fill:{method}

    Args:
        sensor_type: 'WindSpeed' or 'WindDirection'
        height: Target height in meters (will be converted to integer)
        method: 'interpolated' or 'extrapolated'

    Returns:
        Standardized column name string

    Example:
        generate_target_column("WindSpeed", 120.0, "extrapolated")
        -> "WS_120m_fill:extrapolated"
    """
    prefix = "WS" if sensor_type == "WindSpeed" else "WD"
    return f"{prefix}_{int(height)}m_fill:{method}"
