"""Wind direction interpolation strategy between two layers.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-003-strategy-pattern
Compliance: Subdomain layout ✓ | Strategy Pattern ✓ | Domain Service ✓
Description: Strategy for interpolating wind direction between two existing sensor heights

This strategy fills wind direction at a target height by interpolating between
two existing sensor heights using vector-based averaging.

Vector-Based Interpolation (Critical!):
========================================

Wind direction is a circular quantity (0° ≡ 360°). Direct arithmetic fails:
    - (350° + 10°) / 2 = 180°  (WRONG!)
    - Correct answer: ~0° or 360°

This strategy uses vector components to handle wraparound:
    1. Convert each reference direction to (u, v) vector
    2. Extrapolate each to target height using deg_diff_per_m
    3. Weight-average the vectors component-wise
    4. Convert back to degrees

Why Receive Pre-Fitted Parameters?
==================================

Strategies receive pre-fitted deg_diff_per_m values rather than fitting them
themselves because:

1. Separation of Concerns: Fitting is done once in planner.py
2. Reusability: Same strategy works with different fitted values
3. Efficiency: No redundant fitting for each target height
4. Consistency: All targets in same mast use same deg_diff

Interpolation Method:
====================

1. Find lower and higher neighbor heights
2. Calculate 1/distance weights
3. Extrapolate both references to target height:
   WD_target = WD_ref + deg_diff_per_m * (H_target - H_ref)
4. Convert to vectors, weight-average, convert back

Example:
========

Existing WD sensors at 80m and 120m, target at 100m:
    - WD at 80m = 350°, WD at 120m = 10°
    - deg_diff_per_m = 0.1°/m (fitted from data)

    - Extrapolate 80m→100m: 350° + 0.1*20 = 352°
    - Extrapolate 120m→100m: 10° - 0.1*20 = 350°
    - Vector average of 352° and 350° = ~351° (correct!)

Without vector math: (352° + 350°)/2 = 171° (WRONG!)
"""

from cleanmast.subdomains.configuration.value_objects.fill_height_config import (
    WindDirectionHeightConfig,
    HeightReference,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataprocessing.services.strategies._helpers import (
    get_existing_sensors,
    calculate_interpolation_weights,
)


class WDInterpolateInterStrategy:
    """Interpolate WD between two existing layers using vector components.

    This strategy generates a configuration for interpolating wind direction
    at a target height between two existing sensor heights.

    Critical: Uses vector components to handle 0°/360° wraparound correctly.

    The interpolation:
    1. Extrapolates both references to target height using deg_diff_per_m
    2. Converts to (u, v) vector components
    3. Weight-averages the vectors
    4. Converts back to degrees

    This ensures correct results even when directions span 0°/360°.
    """

    name = "wd-interpolate-inter"

    def build_config(
        self,
        timeseries: TimeSeriesData,
        target: SensorColumn,  # Pre-generated target sensor
        references: list[SensorColumn],  # Should contain exactly 2: lower and higher
        deg_diff_per_m: float,  # Pre-fitted from neighbors!
    ) -> WindDirectionHeightConfig | None:
        """Build configuration for WD interpolation at target height.

        Args:
            timeseries: Time series data with existing WD sensors
            target: Pre-generated target sensor column
            references: List of 2 reference sensors (lower and higher)
            deg_diff_per_m: Pre-fitted direction change per meter

        Returns:
            WindDirectionHeightConfig if applicable, None otherwise

        Applicability Check:
            Returns None if target.height is not between min and max
            existing heights. This allows the planner to try other strategies.
        """
        # Check applicability
        existing = get_existing_sensors(timeseries.sensors, "WindDirection")
        if not (min(s.height for s in existing) < target.height < max(s.height for s in existing)):
            return None

        # Get lower and higher sensors from references
        lower_sensor = min(references, key=lambda s: s.height)
        higher_sensor = max(references, key=lambda s: s.height)

        # Calculate weights
        w_low, w_high = calculate_interpolation_weights(target.height, lower_sensor.height, higher_sensor.height)

        return WindDirectionHeightConfig(
            target_sensor=target,  # Use pre-generated target
            references=[
                HeightReference(sensor=lower_sensor, weight=w_low),
                HeightReference(sensor=higher_sensor, weight=w_high)
            ],
            deg_diff_per_m=deg_diff_per_m  # Use pre-fitted value
        )
