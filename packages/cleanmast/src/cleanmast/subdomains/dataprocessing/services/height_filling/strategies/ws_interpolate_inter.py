"""Wind speed interpolation strategy.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-003-strategy-pattern
Compliance: Subdomain layout ✓ | Strategy Pattern ✓
"""

from cleanmast.subdomains.configuration.value_objects.fill_height_config import (
    WindSpeedHeightConfig,
    HeightReference,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from ..helpers import get_existing_sensors, calculate_interpolation_weights


class WSInterpolateInterStrategy:
    """Interpolate WS between two existing layers using 1/distance weighting."""

    name = "ws-interpolate-inter"

    def build_config(
        self,
        timeseries: TimeSeriesData,
        target: SensorColumn,
        references: list[SensorColumn],
        shear: float,
    ) -> WindSpeedHeightConfig | None:
        """Build configuration for WS interpolation at target height."""
        existing = get_existing_sensors(timeseries.sensors, "WindSpeed")
        if not (min(s.height for s in existing) < target.height < max(s.height for s in existing)):
            return None

        lower_sensor = min(references, key=lambda s: s.height)
        higher_sensor = max(references, key=lambda s: s.height)

        w_low, w_high = calculate_interpolation_weights(target.height, lower_sensor.height, higher_sensor.height)

        return WindSpeedHeightConfig(
            target_sensor=target,
            references=[
                HeightReference(sensor=lower_sensor, weight=w_low),
                HeightReference(sensor=higher_sensor, weight=w_high)
            ],
            shear=shear
        )
