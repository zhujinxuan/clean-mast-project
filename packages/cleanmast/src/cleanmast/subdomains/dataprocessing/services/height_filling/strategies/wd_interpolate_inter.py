"""Wind direction interpolation strategy.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-003-strategy-pattern
Compliance: Subdomain layout ✓ | Strategy Pattern ✓
"""

from cleanmast.shared.timeseries import (
    HeightReference,
    SensorColumn,
    TimeSeriesData,
    WindDirectionHeightConfig,
)

from ..helpers import calculate_interpolation_weights, get_existing_sensors


class WDInterpolateInterStrategy:
    """Interpolate WD between two existing layers using vector components."""

    name = "wd-interpolate-inter"

    def build_config(
        self,
        timeseries: TimeSeriesData,
        target: SensorColumn,
        references: list[SensorColumn],
        deg_diff_per_m: float,
    ) -> WindDirectionHeightConfig | None:
        """Build configuration for WD interpolation at target height."""
        existing = get_existing_sensors(timeseries.sensors, "WindDirection")
        if not (min(s.height for s in existing) < target.height < max(s.height for s in existing)):
            return None

        lower_sensor = min(references, key=lambda s: s.height)
        higher_sensor = max(references, key=lambda s: s.height)

        w_low, w_high = calculate_interpolation_weights(target.height, lower_sensor.height, higher_sensor.height)

        return WindDirectionHeightConfig(
            target_sensor=target,
            references=[
                HeightReference(sensor=lower_sensor, weight=w_low),
                HeightReference(sensor=higher_sensor, weight=w_high)
            ],
            deg_diff_per_m=deg_diff_per_m
        )
