"""Pure helper functions for height filling strategies.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-003-strategy-pattern
Compliance: Subdomain layout ✓ | Pure Functions ✓ | Strategy Support ✓
Description: Stateless utility functions used by height filling strategies

This module contains stateless utility functions used by the height filling
strategies. All functions are pure (no side effects) making them easy to test.
"""

from typing import Literal

from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


def get_existing_sensors(
    sensors: list[SensorColumn],
    sensor_type: Literal["WindSpeed", "WindDirection"]
) -> list[SensorColumn]:
    """Get sorted list of existing average sensors.

    Filters sensors by type and stat_type='avg', then returns them
    sorted by height in ascending order.

    Args:
        sensors: List of SensorColumn definitions from the timeseries
        sensor_type: Type of sensor to filter ('WindSpeed' or 'WindDirection')

    Returns:
        Sorted list of SensorColumn objects with stat_type='avg'

    Example:
        sensors = [WS_80m_avg, WS_100m_avg, WD_80m_avg]
        get_existing_sensors(sensors, "WindSpeed") -> [WS_80m_avg, WS_100m_avg]
        get_existing_sensors(sensors, "WindDirection") -> [WD_80m_avg]
    """
    matching = [
        s for s in sensors
        if s.sensor_type == sensor_type and s.stat_type == "avg"
    ]
    return sorted(matching, key=lambda s: s.height)


def calculate_interpolation_weights(
    target: float,
    lower: float,
    higher: float
) -> tuple[float, float]:
    """Calculate 1/distance weights for linear interpolation.

    Uses inverse-distance weighting, where closer reference points
    get higher weights. This is a standard approach in spatial
    interpolation.

    Weight formula:
        weight_lower = (1/dist_lower) / (1/dist_lower + 1/dist_higher)
        weight_higher = (1/dist_higher) / (1/dist_lower + 1/dist_higher)

    Where:
        dist_lower = target - lower
        dist_higher = higher - target

    Args:
        target: Target height in meters
        lower: Lower reference height (must be < target)
        higher: Higher reference height (must be > target)

    Returns:
        Tuple of (weight_lower, weight_higher) that sum to 1.0

    Example:
        calculate_interpolation_weights(100.0, 80.0, 120.0)
        -> (0.5, 0.5)  # Equal distance from both

        calculate_interpolation_weights(90.0, 80.0, 120.0)
        -> (0.75, 0.25)  # Much closer to lower (10m away vs 30m)
    """
    dist_low = target - lower
    dist_high = higher - target
    total = (1 / dist_low) + (1 / dist_high)

    weight_low = (1 / dist_low) / total
    weight_high = (1 / dist_high) / total

    return weight_low, weight_high
