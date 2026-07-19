"""Wind speed extrapolation strategy.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-003-strategy-pattern
Compliance: Subdomain layout ✓ | Strategy Pattern ✓
"""

from cleanmast.shared.timeseries import (
    HeightReference,
    SensorColumn,
    TimeSeriesData,
    WindSpeedHeightConfig,
)

from ..helpers import get_existing_sensors


class WSExtrapolateTop3Strategy:
    """Extrapolate WS above highest layer using shear fitted from top 3 layers."""

    name = "ws-extrapolate-top3"

    def build_config(
        self,
        timeseries: TimeSeriesData,
        target: SensorColumn,
        references: list[SensorColumn],
        shear: float,
    ) -> WindSpeedHeightConfig | None:
        """Build configuration for WS extrapolation at target height."""
        existing = get_existing_sensors(timeseries.sensors, "WindSpeed")
        if target.height <= max(s.height for s in existing):
            return None

        ref_sensor = max(references, key=lambda s: s.height)

        return WindSpeedHeightConfig(
            target_sensor=target,
            references=[HeightReference(sensor=ref_sensor, weight=1.0)],
            shear=shear
        )
