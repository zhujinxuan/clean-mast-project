"""Fifty-year max wind Method 1 (五倍风速法) calculator.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Domain service for calculating 50-year max wind using IEC 61400-1 Method 1
(5x average wind speed rule).
"""

from datetime import datetime
from typing import cast

import polars as pl

from cleanmast.subdomains.assessment.domain.services.calculators.air_density_calculator import (
    AirDensityCalculator,
)
from cleanmast.subdomains.assessment.domain.value_objects.air_density import (
    calculate_air_density_for_height,
    convert_to_standard_air_density,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_metadata import (
    AnalysisMetadata,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    FiftyYearMaxWindMethod1DetailSchema,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


class Method1Calculator:
    """Calculate fifty-year maximum wind speed using Method 1 (五倍风速法).

    For each analysis height:
    - Find the avg WindSpeed sensor at that exact height
    - Compute mean of valid wind speed values (>0, not null, finite)
    - Sustained wind speed = 5.0 * mean
    - Extreme wind speed = 1.4 * sustained
    - Convert both to standard air density equivalent

    Key formulas:
        sustained = 5.0 * avg_speed
        extreme = 1.4 * sustained
        v_std = v * sqrt(ρ_actual / ρ_std)
    """

    def calculate(
        self,
        input: SingleMastAnalysisInput,
    ) -> AnalysisResult[FiftyYearMaxWindMethod1DetailSchema]:
        """Calculate Method 1 fifty-year max wind for all heights.

        Args:
            input: SingleMastAnalysisInput containing time series data and parameters

        Returns:
            AnalysisResult with FiftyYearMaxWindMethod1DetailSchema
        """
        df = input.time_series.df
        sensors = input.time_series.sensors
        heights = input.parameters.heights

        # Determine air density and reference height
        if input.parameters.air_density is not None:
            air_density = input.parameters.air_density
            reference_height = self._get_reference_height_from_sensors(sensors, default=10.0)
        else:
            air_density = AirDensityCalculator().calculate(input.time_series)
            reference_height = self._get_reference_height_from_sensors(sensors, default=10.0)

        rows: list[dict] = []
        for height in heights:
            sensor = self._find_avg_wind_speed_sensor(sensors, height)
            if sensor is None:
                continue

            ws_col = sensor.column_name
            if ws_col not in df.columns:
                continue

            # Filter valid values: > 0, not null, finite
            valid_series = df.filter(
                pl.col(ws_col).is_not_null()
                & (pl.col(ws_col) > 0)
                & pl.col(ws_col).is_finite()
            )[ws_col]

            if valid_series.is_empty():
                continue

            avg_speed = cast(float, valid_series.mean())
            sustained = 5.0 * avg_speed
            extreme = 1.4 * sustained

            interpolation_marker = sensor.detect_interpolation_marker()
            air_density_at_height = calculate_air_density_for_height(
                height=height,
                reference_density=air_density,
                reference_height=reference_height,
            )

            sustained_std = convert_to_standard_air_density(sustained, air_density_at_height)
            extreme_std = convert_to_standard_air_density(extreme, air_density_at_height)

            rows.append({
                "height": height,
                "interpolation_marker": interpolation_marker or None,
                "wind_speed_type": "sustained",
                "method": "method1",
                "max_wind_speed": sustained,
                "standard_density_wind_speed": sustained_std,
                "average_wind_speed": avg_speed,
                "air_density": air_density_at_height,
            })
            rows.append({
                "height": height,
                "interpolation_marker": interpolation_marker or None,
                "wind_speed_type": "extreme",
                "method": "method1",
                "max_wind_speed": extreme,
                "standard_density_wind_speed": extreme_std,
                "average_wind_speed": avg_speed,
                "air_density": air_density_at_height,
            })

        result_df = pl.DataFrame(rows) if rows else self._create_empty_dataframe()

        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=FiftyYearMaxWindMethod1DetailSchema,
            data=result_df,
            metadata=metadata,
        )

    def _find_avg_wind_speed_sensor(
        self,
        sensors: list[SensorColumn],
        height: float,
    ) -> SensorColumn | None:
        """Find the avg WindSpeed sensor at the exact given height.

        Args:
            sensors: List of sensor metadata
            height: Target height in meters

        Returns:
            Matching SensorColumn or None
        """
        return next(
            (
                s
                for s in sensors
                if s.sensor_type == "WindSpeed" and s.stat_type == "avg" and s.height == height
            ),
            None,
        )

    def _get_reference_height_from_sensors(
        self,
        sensors: list[SensorColumn],
        default: float = 10.0,
    ) -> float:
        """Get reference height from temperature or pressure sensors.

        Args:
            sensors: List of sensor metadata
            default: Default reference height if no temp/pressure sensor found

        Returns:
            Reference height in meters
        """
        temp_sensor = next(
            (s for s in sensors if s.sensor_type == "Temperature" and s.stat_type == "avg"),
            None,
        )
        if temp_sensor is not None:
            return temp_sensor.height

        pressure_sensor = next(
            (s for s in sensors if s.sensor_type == "Pressure" and s.stat_type == "avg"),
            None,
        )
        if pressure_sensor is not None:
            return pressure_sensor.height

        return default

    def _create_empty_dataframe(self) -> pl.DataFrame:
        """Create an empty DataFrame with FiftyYearMaxWindMethod1DetailSchema columns.

        Returns:
            Empty polars DataFrame with correct schema
        """
        return pl.DataFrame({
            "height": pl.Series([], dtype=pl.Float64),
            "interpolation_marker": pl.Series([], dtype=pl.String),
            "wind_speed_type": pl.Series([], dtype=pl.String),
            "method": pl.Series([], dtype=pl.String),
            "max_wind_speed": pl.Series([], dtype=pl.Float64),
            "standard_density_wind_speed": pl.Series([], dtype=pl.Float64),
            "average_wind_speed": pl.Series([], dtype=pl.Float64),
            "air_density": pl.Series([], dtype=pl.Float64),
        })

    def _get_time_range(self, df: pl.DataFrame) -> str:
        """Extract time range from DataFrame as formatted string.

        Args:
            df: DataFrame with timestamp column

        Returns:
            Time range string or "Unknown"
        """
        if "timestamp" not in df.columns or df.is_empty():
            return "Unknown"

        timestamps = df["timestamp"]
        start = timestamps.min()
        end = timestamps.max()

        if start is None or end is None:
            return "Unknown"

        start_str = str(start)[:10]
        end_str = str(end)[:10]

        return f"{start_str} to {end_str}"
