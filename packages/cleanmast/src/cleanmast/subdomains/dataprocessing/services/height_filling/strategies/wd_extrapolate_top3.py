"""Wind direction extrapolation strategy.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-003-strategy-pattern
Compliance: Subdomain layout ✓ | Strategy Pattern ✓
"""

from cleanmast.shared.timeseries import (
    HeightReference,
    TimeSeriesData,
    WindDirectionHeightConfig,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn

from ..helpers import get_existing_sensors


class WDExtrapolateTop3Strategy:
    """Extrapolate WD above highest layer using deg_diff fitted from top 3."""

    name = "wd-extrapolate-top3"

    def build_config(
        self,
        timeseries: TimeSeriesData,
        target: SensorColumn,
        references: list[SensorColumn],
        deg_diff_per_m: float,
    ) -> WindDirectionHeightConfig | None:
        """Build configuration for WD extrapolation at target height."""
        existing = get_existing_sensors(timeseries.sensors, "WindDirection")
        if target.height <= max(s.height for s in existing):
            return None

        ref_sensor = max(references, key=lambda s: s.height)

        return WindDirectionHeightConfig(
            target_sensor=target,
            references=[HeightReference(sensor=ref_sensor, weight=1.0)],
            deg_diff_per_m=deg_diff_per_m
        )
