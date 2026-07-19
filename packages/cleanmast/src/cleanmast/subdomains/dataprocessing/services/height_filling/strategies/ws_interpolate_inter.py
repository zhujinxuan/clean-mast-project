"""Wind speed interpolation strategy.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-003-strategy-pattern
Compliance: Subdomain layout ✓ | Strategy Pattern ✓
"""

from cleanmast.shared.timeseries import (
    HeightReference,
    SensorColumn,
    TimeSeriesData,
    WindSpeedHeightConfig,
)

from ..helpers import calculate_interpolation_weights, get_existing_sensors


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
