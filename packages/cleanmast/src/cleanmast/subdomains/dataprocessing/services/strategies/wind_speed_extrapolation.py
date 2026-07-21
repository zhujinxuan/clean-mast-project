"""Wind speed extrapolation strategy using top 3 fitted shear.

Description: Strategy for extrapolating wind speed above highest sensor using top 3 shear

This strategy fills wind speed at a target height ABOVE the highest existing
sensor using power law extrapolation with shear fitted from the top 3 layers.

Extrapolation Method:
====================

1. Use the highest existing sensor as the reference
2. Extrapolate to target height using the power law:
   V_target = V_ref * (H_target / H_ref)^shear

3. The shear value should be fitted from the top 3 existing layers:
   - Most relevant for extrapolation (same atmospheric layer)
   - Less affected by ground roughness effects
   - More representative of free-stream conditions

Why Top 3?
==========

Using top 3 layers (instead of just top 2) provides:
1. Better statistical robustness (more data points)
2. Still captures upper-level shear profile
3. Not contaminated by surface layer effects

Applicability:
=============

This strategy is applicable when:
    target_height > max(existing_heights)

If target is not above max existing, returns None and the planner
should use interpolation instead.

Example:
========

Existing sensors at 40m, 60m, 80m, 100m (max = 100m)
Target height = 120m

Shear fitted from top 3 (60m, 80m, 100m) = 0.15

Configuration:
    reference = WS_100m_avg (highest existing)
    shear = 0.15 (fitted from top 3)

Execution will compute:
    WS_120m = WS_100m * (120/100)^0.15
"""

from cleanmast.shared.timeseries import (
    HeightReference,
    SensorColumn,
    TimeSeriesData,
    WindSpeedHeightConfig,
)
from cleanmast.subdomains.dataprocessing.services.strategies._helpers import (
    get_existing_sensors,
)


class WSExtrapolateTop3Strategy:
    """Extrapolate WS above highest layer using shear fitted from top 3 layers.

    This strategy generates a configuration for extrapolating wind speed
    at a target height above the highest existing sensor.

    The configuration specifies:
    - Reference: highest existing sensor
    - Method: power law extrapolation
    - Shear: pre-fitted from top 3 layers
    """

    name = "ws-extrapolate-top3"

    def build_config(
        self,
        timeseries: TimeSeriesData,
        target: SensorColumn,  # Pre-generated target sensor
        references: list[SensorColumn],  # Reference sensors (highest will be used)
        shear: float,  # Pre-fitted from top 3!
    ) -> WindSpeedHeightConfig | None:
        """Build configuration for WS extrapolation at target height.

        Args:
            timeseries: Time series data with existing WS sensors
            target: Pre-generated target sensor column
            references: List of reference sensors (highest will be used)
            shear: Pre-fitted power law exponent from top 3 layers

        Returns:
            WindSpeedHeightConfig if applicable, None otherwise

        Applicability Check:
            Returns None if target.height <= max existing height.
            This allows the planner to try interpolation instead.
        """
        # Check applicability
        existing = get_existing_sensors(timeseries.sensors, "WindSpeed")
        if target.height <= max(s.height for s in existing):
            return None  # Not applicable

        # Get reference from references parameter (highest)
        ref_sensor = max(references, key=lambda s: s.height)

        return WindSpeedHeightConfig(
            target_sensor=target,  # Use pre-generated target
            references=[HeightReference(sensor=ref_sensor, weight=1.0)],
            shear=shear  # Use pre-fitted value
        )
