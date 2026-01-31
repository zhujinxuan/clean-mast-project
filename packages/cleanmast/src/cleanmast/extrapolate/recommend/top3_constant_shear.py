"""Top-3 Constant Shear strategy for wind extrapolation.

Uses the top 3 measurement heights to fit a constant power law shear exponent.
"""

import numpy as np
import polars as pl

from ...io.timeseries_io import load_timeseries
from ...models.reconstruct_meso import ReconstructMesoConfiguration
from ...models.sensor import SensorColumn
from ...models.timeseries import TimeSeriesSource
from ..config import (
    ExtrapolateConfiguration,
    MastExtrapolateConfig,
    WindDirectionConfig,
    WindDirectionHeightConfig,
    WindDirectionReference,
    WindSpeedConfig,
    WindSpeedHeightConfig,
    WindSpeedReference,
)
from ..shear import fit_shear_from_heights
from .registry import RecommendStrategy, register_strategy


@register_strategy
class Top3ConstantShearStrategy(RecommendStrategy):
    """Strategy that uses top 3 heights to fit a constant shear exponent.

    Algorithm:
    1. Load timeseries data from reconstruct-meso output
    2. Find top 3 wind speed sensor heights (only avg stat_type)
    3. Calculate power law shear exponent using linear regression
    4. For wind direction: calculate average deg_diff_per_m from top layers
    5. Use only top layer as reference in output config
    """

    name = "top3-constant-shear"

    def recommend(
        self,
        reconstruct_config: ReconstructMesoConfiguration,
        base_dir: str,
        extrapolate_heights: list[float],
    ) -> ExtrapolateConfiguration:
        """Generate extrapolation configuration using top-3 constant shear.

        Args:
            reconstruct_config: ReconstructMeso configuration
            base_dir: Base directory for resolving paths
            extrapolate_heights: Target heights for extrapolation (m)

        Returns:
            ExtrapolateConfiguration with fitted shear values
        """
        mast_configs: list[MastExtrapolateConfig] = []

        # Process each mast individually for per-mast shear
        for mast in reconstruct_config.masts:
            timeseries = load_timeseries(mast.output, base_dir)

            # Calculate shear from this mast's top 3 wind speed sensors
            shear = self._fit_wind_speed_shear(timeseries.sensors, timeseries.df)

            # Calculate wind direction deg_diff_per_m for this mast
            deg_diff_per_m = self._fit_wind_direction_change(
                timeseries.sensors, timeseries.df
            )

            # Get existing heights for this mast
            existing_ws_heights = sorted(
                self._get_all_heights(timeseries.sensors, "WindSpeed")
            )
            existing_wd_heights = sorted(
                self._get_all_heights(timeseries.sensors, "WindDirection")
            )

            # Filter out heights that already exist in this mast
            ws_target_heights = [
                h for h in extrapolate_heights if h not in set(existing_ws_heights)
            ]
            wd_target_heights = [
                h for h in extrapolate_heights if h not in set(existing_wd_heights)
            ]

            # Build wind speed config with weighted references
            ws_heights = [
                WindSpeedHeightConfig(
                    height=target_height,
                    references=self._build_weighted_ws_references(
                        target_height, existing_ws_heights, shear
                    ),
                )
                for target_height in ws_target_heights
            ]

            # Build wind direction config with weighted references
            wd_heights = [
                WindDirectionHeightConfig(
                    height=target_height,
                    references=self._build_weighted_wd_references(
                        target_height, existing_wd_heights, deg_diff_per_m
                    ),
                )
                for target_height in wd_target_heights
            ]

            # Build mast config with embedded windspeed/winddirection
            mast_configs.append(
                MastExtrapolateConfig(
                    name=mast.name,
                    input=mast.output,  # Input comes from reconstruct-meso output
                    output=TimeSeriesSource(
                        data=f"./extrapolated/{mast.name}.csv",
                        sensors=f"./extrapolated/{mast.name}.sensors.yaml",
                    ),
                    windspeed=WindSpeedConfig(heights=ws_heights),
                    winddirection=WindDirectionConfig(heights=wd_heights),
                )
            )

        return ExtrapolateConfiguration(
            strategy=self.name,
            masts=mast_configs,
        )

    def _get_avg_sensors(
        self, sensors: list[SensorColumn], sensor_type: str
    ) -> list[SensorColumn]:
        """Filter sensors by type and avg stat_type.

        CRITICAL: Only use avg sensors for shear fitting, not min/max/sd.
        """
        return [
            s
            for s in sensors
            if s.sensor_type == sensor_type and s.stat_type == "avg"
        ]

    def _get_top_heights(
        self, sensors: list[SensorColumn], sensor_type: str, n: int = 3
    ) -> list[float]:
        """Get top N unique heights for a sensor type (avg only)."""
        avg_sensors = self._get_avg_sensors(sensors, sensor_type)
        heights = sorted(set(s.height for s in avg_sensors), reverse=True)
        return heights[:n]

    def _get_top_height(self, sensors: list[SensorColumn], sensor_type: str) -> float:
        """Get the top (highest) height for a sensor type (avg only)."""
        heights = self._get_top_heights(sensors, sensor_type, n=1)
        return heights[0]

    def _get_all_heights(
        self, sensors: list[SensorColumn], sensor_type: str
    ) -> list[float]:
        """Get all unique heights for a sensor type (avg only)."""
        avg_sensors = self._get_avg_sensors(sensors, sensor_type)
        return list(set(s.height for s in avg_sensors))

    def _fit_wind_speed_shear(
        self, sensors: list[SensorColumn], df: pl.DataFrame
    ) -> float:
        """Fit power law shear exponent from top heights.

        Uses linear regression on log-transformed wind speed data.
        """
        # Get top 3 heights
        top_heights = self._get_top_heights(sensors, "WindSpeed", n=3)

        if len(top_heights) < 2:
            raise ValueError("Need at least 2 wind speed heights to fit shear")

        # Get sensor columns for these heights
        avg_sensors = self._get_avg_sensors(sensors, "WindSpeed")
        height_to_col = {s.height: s.column_name for s in avg_sensors}

        # Extract mean wind speeds for each height
        heights: list[float] = []
        speeds: list[float] = []
        for h in top_heights:
            if h in height_to_col:
                col = height_to_col[h]
                if col in df.columns:
                    mean_speed = df[col].drop_nulls().mean()
                    if mean_speed is not None:
                        mean_speed_float = float(mean_speed)  # type: ignore[arg-type]
                        if mean_speed_float > 0:
                            heights.append(h)
                            speeds.append(mean_speed_float)

        if len(heights) < 2:
            raise ValueError("Need at least 2 valid height measurements to fit shear")

        return fit_shear_from_heights(np.array(heights), np.array(speeds))

    def _fit_wind_direction_change(
        self, sensors: list[SensorColumn], df: pl.DataFrame
    ) -> float:
        """Calculate wind direction change per meter.

        For each timestamp, calculates direction difference from lowest height
        to each other height. Then fits linear regression on all (Δdeg, Δh) pairs.
        This correctly handles the circular nature of wind direction.
        """
        # Get top 3 heights
        top_heights = self._get_top_heights(sensors, "WindDirection", n=3)

        if len(top_heights) < 2:
            return 0.0

        # Get sensor columns for these heights, sorted by height
        avg_sensors = self._get_avg_sensors(sensors, "WindDirection")
        height_to_col = {s.height: s.column_name for s in avg_sensors}

        # Filter to heights we have columns for
        valid_heights = sorted([h for h in top_heights if h in height_to_col])
        if len(valid_heights) < 2:
            return 0.0

        # Get column names sorted by height
        cols = [height_to_col[h] for h in valid_heights]

        # Check all columns exist
        for col in cols:
            if col not in df.columns:
                return 0.0

        # Lowest height is reference
        ref_height = valid_heights[0]
        ref_col = cols[0]

        # Accumulate sum(Δh * Δdir) and sum(Δh²) for regression through origin
        sum_dh_ddir = 0.0
        sum_dh_sq = 0.0

        for i in range(1, len(valid_heights)):
            target_height = valid_heights[i]
            target_col = cols[i]
            delta_h = target_height - ref_height

            # Circular difference: ((target - ref + 180) % 360) - 180
            # This gives range [-180, 180]
            diff_expr = ((pl.col(target_col) - pl.col(ref_col) + 180) % 360) - 180

            # Calculate sum of differences (excluding nulls)
            result = df.select(diff_expr.alias("diff")).drop_nulls()
            diffs = result["diff"]

            n = len(diffs)
            if n == 0:
                continue

            sum_dh_ddir += delta_h * diffs.sum()
            sum_dh_sq += delta_h * delta_h * n

        if sum_dh_sq == 0:
            return 0.0

        # Least squares fit through origin: slope = sum(Δh * Δdir) / sum(Δh²)
        deg_diff_per_m = sum_dh_ddir / sum_dh_sq

        return float(deg_diff_per_m)

    def _find_neighbors(
        self, target: float, existing: list[float]
    ) -> tuple[float | None, float | None]:
        """Find closest lower and higher heights from existing heights.

        Args:
            target: Target height to find neighbors for
            existing: Sorted list of existing heights

        Returns:
            Tuple of (lower_height, higher_height), either can be None
        """
        lower: float | None = None
        higher: float | None = None

        for h in existing:
            if h < target:
                lower = h  # Keep updating to get the closest lower
            elif h > target:
                higher = h
                break  # First one greater is the closest higher

        return lower, higher

    def _build_weighted_ws_references(
        self, target_height: float, existing_heights: list[float], shear: float
    ) -> list[WindSpeedReference]:
        """Build wind speed references with 1/distance weights.

        Uses both lower and higher neighbors if available, with weights
        inversely proportional to distance (normalized to sum to 1).
        """
        lower, higher = self._find_neighbors(target_height, existing_heights)

        refs: list[WindSpeedReference] = []

        if lower is not None and higher is not None:
            # Both neighbors available - use 1/distance weights
            dist_lower = target_height - lower
            dist_higher = higher - target_height
            weight_lower = (1 / dist_lower) / (1 / dist_lower + 1 / dist_higher)
            weight_higher = (1 / dist_higher) / (1 / dist_lower + 1 / dist_higher)
            refs.append(WindSpeedReference(height=lower, shear=shear, weight=weight_lower))
            refs.append(WindSpeedReference(height=higher, shear=shear, weight=weight_higher))
        elif lower is not None:
            # Only lower available (extrapolating upward)
            refs.append(WindSpeedReference(height=lower, shear=shear, weight=1.0))
        elif higher is not None:
            # Only higher available (extrapolating downward)
            refs.append(WindSpeedReference(height=higher, shear=shear, weight=1.0))
        else:
            # No existing heights - shouldn't happen but fallback to first
            if existing_heights:
                refs.append(WindSpeedReference(height=existing_heights[0], shear=shear, weight=1.0))

        return refs

    def _build_weighted_wd_references(
        self, target_height: float, existing_heights: list[float], deg_diff_per_m: float
    ) -> list[WindDirectionReference]:
        """Build wind direction references with 1/distance weights.

        Uses both lower and higher neighbors if available, with weights
        inversely proportional to distance (normalized to sum to 1).
        """
        lower, higher = self._find_neighbors(target_height, existing_heights)

        refs: list[WindDirectionReference] = []

        if lower is not None and higher is not None:
            # Both neighbors available - use 1/distance weights
            dist_lower = target_height - lower
            dist_higher = higher - target_height
            weight_lower = (1 / dist_lower) / (1 / dist_lower + 1 / dist_higher)
            weight_higher = (1 / dist_higher) / (1 / dist_lower + 1 / dist_higher)
            refs.append(WindDirectionReference(height=lower, deg_diff_per_m=deg_diff_per_m, weight=weight_lower))
            refs.append(WindDirectionReference(height=higher, deg_diff_per_m=deg_diff_per_m, weight=weight_higher))
        elif lower is not None:
            # Only lower available (extrapolating upward)
            refs.append(WindDirectionReference(height=lower, deg_diff_per_m=deg_diff_per_m, weight=1.0))
        elif higher is not None:
            # Only higher available (extrapolating downward)
            refs.append(WindDirectionReference(height=higher, deg_diff_per_m=deg_diff_per_m, weight=1.0))
        else:
            # No existing heights - shouldn't happen but fallback to first
            if existing_heights:
                refs.append(WindDirectionReference(height=existing_heights[0], deg_diff_per_m=deg_diff_per_m, weight=1.0))

        return refs
