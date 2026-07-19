"""Wind speed interpolation strategy between two layers.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-003-strategy-pattern
Compliance: Subdomain layout ✓ | Strategy Pattern ✓ | Domain Service ✓
Description: Strategy for interpolating wind speed between two existing sensor heights

This strategy fills wind speed at a target height by interpolating between
two existing sensor heights using inverse-distance weighting.

Strategy Pattern:
================

Each strategy implements the HeightStrategy protocol with:
    - name: Class attribute for identification
    - build_config(): Method to generate configuration for a target height

Why Receive Pre-Fitted Parameters?
==================================

Strategies receive pre-fitted shear values rather than fitting them
themselves because:

1. Separation of Concerns: Fitting is done once in planner.py
2. Reusability: Same strategy can work with different fitted values
3. Efficiency: No redundant fitting for each target height
4. Consistency: All targets in same mast use same shear value

Interpolation Method:
====================

1. Find lower and higher neighbor heights from existing sensors
2. Calculate 1/distance weights (closer sensor gets higher weight)
3. Extrapolate both reference values to target height using power law
4. Weight-average the two extrapolated values

Power law extrapolation for each reference:
    V_target = V_ref * (H_target / H_ref)^shear

The shear value should be fitted from the same or similar heights
for best accuracy.

Applicability:
=============

This strategy is applicable when:
    min(existing_heights) < target_height < max(existing_heights)

If target is outside this range, the strategy returns None and the
planner should use extrapolation instead.
"""

from cleanmast.shared.timeseries import (
    HeightReference,
    TimeSeriesData,
    WindSpeedHeightConfig,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
from cleanmast.subdomains.dataprocessing.services.strategies._helpers import (
    calculate_interpolation_weights,
    get_existing_sensors,
)


class WSInterpolateInterStrategy:
    """Interpolate WS between two existing layers using 1/distance weighting.

    This strategy generates a configuration for interpolating wind speed
    at a target height between two existing sensor heights.

    The interpolation uses inverse-distance weighting:
        weight_lower = 1/dist_lower / (1/dist_lower + 1/dist_higher)
        weight_higher = 1/dist_higher / (1/dist_lower + 1/dist_higher)

    Each reference value is first extrapolated to the target height using
    the power law, then the extrapolated values are weighted and averaged.

    Example:
        Existing sensors at 80m and 120m, target at 100m:
            - dist_lower = 20m, dist_higher = 20m
            - weights = (0.5, 0.5)
            - Both references extrapolate to 100m with power law
            - Results averaged with equal weights
    """

    name = "ws-interpolate-inter"

    def build_config(
        self,
        timeseries: TimeSeriesData,
        target: SensorColumn,  # Pre-generated target sensor
        references: list[SensorColumn],  # Should contain exactly 2: lower and higher
        shear: float,  # Pre-fitted from neighbors!
    ) -> WindSpeedHeightConfig | None:
        """Build configuration for WS interpolation at target height.

        Args:
            timeseries: Time series data with existing WS sensors
            target: Pre-generated target sensor column
            references: List of 2 reference sensors (lower and higher)
            shear: Pre-fitted power law exponent (from fitting.py)

        Returns:
            WindSpeedHeightConfig if applicable, None otherwise

        Applicability Check:
            Returns None if target.height is not between min and max
            existing heights. This allows the planner to try other strategies.
        """
        # Check applicability
        existing = get_existing_sensors(timeseries.sensors, "WindSpeed")
        if not (min(s.height for s in existing) < target.height < max(s.height for s in existing)):
            return None

        # Get lower and higher sensors from references
        lower_sensor = min(references, key=lambda s: s.height)
        higher_sensor = max(references, key=lambda s: s.height)

        # Calculate weights
        w_low, w_high = calculate_interpolation_weights(target.height, lower_sensor.height, higher_sensor.height)

        return WindSpeedHeightConfig(
            target_sensor=target,  # Use pre-generated target
            references=[
                HeightReference(sensor=lower_sensor, weight=w_low),
                HeightReference(sensor=higher_sensor, weight=w_high)
            ],
            shear=shear  # Use pre-fitted value from neighbors
        )
