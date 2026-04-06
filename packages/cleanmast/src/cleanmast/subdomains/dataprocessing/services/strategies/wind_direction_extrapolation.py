"""Wind direction extrapolation strategy using top 3 fitted deg_diff.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-003-strategy-pattern
Compliance: Subdomain layout ✓ | Strategy Pattern ✓ | Domain Service ✓
Description: Strategy for extrapolating wind direction above highest sensor using top 3 deg_diff

This strategy fills wind direction at a target height ABOVE the highest existing
sensor using linear extrapolation with deg_diff_per_m fitted from top 3 layers.

Extrapolation Method:
====================

1. Use the highest existing WD sensor as the reference
2. Extrapolate to target height using:
   WD_target = WD_ref + deg_diff_per_m * (H_target - H_ref)

3. Result is wrapped to [0, 360) degrees

4. The deg_diff_per_m value should be fitted from the top 3 WD layers

Why Top 3?
==========

Using top 3 layers (instead of just top 2) provides:
1. Better statistical robustness
2. Captures upper-level direction shear profile
3. Not contaminated by surface layer effects

Physical Interpretation:
=======================

- Positive deg_diff_per_m: Veering (clockwise turn with height)
  Example: S→SW→W as you go up (180°→225°→270°)

- Negative deg_diff_per_m: Backing (counter-clockwise turn with height)
  Example: N→NW→W as you go up (0°→315°→270°)

- Near zero: Direction largely constant with height

Applicability:
=============

This strategy is applicable when:
    target_height > max(existing_heights)

If target is not above max existing, returns None and the planner
should use interpolation instead.

Example:
========

Existing WD sensors at 60m, 80m, 100m (max = 100m)
Target height = 120m

deg_diff fitted from top 3 = 0.1°/m (veering)

Configuration:
    reference = WD_100m_avg (highest existing)
    deg_diff_per_m = 0.1 (fitted from top 3)

Execution will compute:
    WD_120m = WD_100m + 0.1 * (120 - 100)
           = WD_100m + 2.0° (slightly veered)

Wraparound example:
    If WD_100m = 358°
    WD_120m = 358° + 2° = 360° → 0°
    (Correctly wraps to 0°, not 360°)
"""

from cleanmast.subdomains.configuration.value_objects.fill_height_config import (
    HeightReference,
    WindDirectionHeightConfig,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
from cleanmast.subdomains.dataprocessing.services.strategies._helpers import (
    get_existing_sensors,
)


class WDExtrapolateTop3Strategy:
    """Extrapolate WD above highest layer using deg_diff fitted from top 3.

    This strategy generates a configuration for extrapolating wind direction
    at a target height above the highest existing sensor.

    The configuration specifies:
    - Reference: highest existing WD sensor
    - Method: linear extrapolation with deg_diff_per_m
    - deg_diff: pre-fitted from top 3 layers

    Physical interpretation of deg_diff_per_m:
    - Positive: Veering (clockwise) with height
    - Negative: Backing (counter-clockwise) with height
    - Near zero: Direction constant with height
    """

    name = "wd-extrapolate-top3"

    def build_config(
        self,
        timeseries: TimeSeriesData,
        target: SensorColumn,  # Pre-generated target sensor
        references: list[SensorColumn],  # Reference sensors (highest will be used)
        deg_diff_per_m: float,  # Pre-fitted from top 3!
    ) -> WindDirectionHeightConfig | None:
        """Build configuration for WD extrapolation at target height.

        Args:
            timeseries: Time series data with existing WD sensors
            target: Pre-generated target sensor column
            references: List of reference sensors (highest will be used)
            deg_diff_per_m: Pre-fitted direction change per meter from top 3

        Returns:
            WindDirectionHeightConfig if applicable, None otherwise

        Applicability Check:
            Returns None if target.height <= max existing height.
            This allows the planner to try interpolation instead.
        """
        # Check applicability
        existing = get_existing_sensors(timeseries.sensors, "WindDirection")
        if target.height <= max(s.height for s in existing):
            return None  # Not applicable

        # Get reference from references parameter (highest)
        ref_sensor = max(references, key=lambda s: s.height)

        return WindDirectionHeightConfig(
            target_sensor=target,  # Use pre-generated target
            references=[HeightReference(sensor=ref_sensor, weight=1.0)],
            deg_diff_per_m=deg_diff_per_m  # Use pre-fitted value
        )
