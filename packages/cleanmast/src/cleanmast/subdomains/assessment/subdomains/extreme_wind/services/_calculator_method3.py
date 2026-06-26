"""Fifty-year max wind Method 3 (极端风速模型法 / EWM) calculator.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Domain service for calculating 50-year max wind using extreme wind model.
"""

from datetime import datetime
from typing import cast

import polars as pl

from cleanmast.subdomains.assessment.shared.utils.air_density import (
    calculate_air_density_for_height,
    convert_to_standard_air_density,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_metadata import (
    AnalysisMetadata,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.subdomains.extreme_wind.value_objects.schemas import (
    FiftyYearMaxWindResultSchema,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


class Method3Calculator:
    """Calculate fifty-year maximum wind speed using Method 3 (极端风速模型法).

    For each analysis height:
    - Sustained: find avg WindSpeed sensor, observed_max = max(valid_values),
      v50 = 1.25 * observed_max
    - Extreme: find max WindSpeed sensor, observed_max = max(valid_values),
      v50 = 1.25 * observed_max
    - If no max sensor for extreme, fallback: v50 = sustained_v50 * 1.4,
      observed_max = sustained_observed_max
    - Convert to standard air density equivalent
    """

    def calculate_sustained(
        self,
        input: SingleMastAnalysisInput,
    ) -> AnalysisResult[FiftyYearMaxWindResultSchema]:
        """Calculate Method 3 sustained fifty-year max wind for all heights.

        Args:
            input: SingleMastAnalysisInput containing time series data and parameters

        Returns:
            AnalysisResult with FiftyYearMaxWindResultSchema for sustained wind
        """
        df = input.time_series.df
        sensors = input.time_series.sensors
        heights = input.parameters.heights

        air_density, reference_height = self._get_air_density_and_reference(
            input, sensors
        )

        rows: list[dict] = []
        for height in heights:
            sensor = self._find_wind_speed_sensor(sensors, height, stat_type="avg")
            if sensor is None:
                continue

            ws_col = sensor.column_name
            if ws_col not in df.columns:
                continue

            valid_series = df.filter(
                pl.col(ws_col).is_not_null()
                & (pl.col(ws_col) > 0)
                & pl.col(ws_col).is_finite()
            )[ws_col]

            if valid_series.is_empty():
                continue

            observed_max = cast(float, valid_series.max())
            v50 = 1.25 * observed_max

            interpolation_marker = sensor.detect_interpolation_marker()
            air_density_at_height = calculate_air_density_for_height(
                height=height,
                reference_density=air_density,
                reference_height=reference_height,
            )

            v50_std = convert_to_standard_air_density(v50, air_density_at_height)

            rows.append({
                "height": height,
                "interpolation_marker": interpolation_marker or None,
                "wind_speed_type": "sustained",
                "method": "method3",
                "max_wind_speed": v50,
                "standard_density_wind_speed": v50_std,
                "observed_max": observed_max,
            })

        result_df = pl.DataFrame(rows) if rows else self._create_empty_dataframe()

        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=FiftyYearMaxWindResultSchema,
            data=result_df,
            metadata=metadata,
        )

    def calculate_extreme(
        self,
        input: SingleMastAnalysisInput,
        sustained_result: AnalysisResult[FiftyYearMaxWindResultSchema] | None = None,
    ) -> AnalysisResult[FiftyYearMaxWindResultSchema]:
        """Calculate Method 3 extreme fifty-year max wind for all heights.

        Args:
            input: SingleMastAnalysisInput containing time series data and parameters
            sustained_result: Optional sustained result for fallback when max sensor missing

        Returns:
            AnalysisResult with FiftyYearMaxWindResultSchema for extreme wind
        """
        df = input.time_series.df
        sensors = input.time_series.sensors
        heights = input.parameters.heights

        air_density, reference_height = self._get_air_density_and_reference(
            input, sensors
        )

        sustained_by_height: dict[float, dict] = {}
        if sustained_result is not None:
            for row in sustained_result.data.iter_rows(named=True):
                sustained_by_height[row["height"]] = row

        rows: list[dict] = []
        for height in heights:
            sensor = self._find_wind_speed_sensor(sensors, height, stat_type="max")

            if sensor is not None and sensor.column_name in df.columns:
                ws_col = sensor.column_name
                valid_series = df.filter(
                    pl.col(ws_col).is_not_null()
                    & (pl.col(ws_col) > 0)
                    & pl.col(ws_col).is_finite()
                )[ws_col]

                if not valid_series.is_empty():
                    observed_max = cast(float, valid_series.max())
                    v50 = 1.25 * observed_max

                    interpolation_marker = sensor.detect_interpolation_marker()
                    air_density_at_height = calculate_air_density_for_height(
                        height=height,
                        reference_density=air_density,
                        reference_height=reference_height,
                    )

                    v50_std = convert_to_standard_air_density(v50, air_density_at_height)

                    rows.append({
                        "height": height,
                        "interpolation_marker": interpolation_marker or None,
                        "wind_speed_type": "extreme",
                        "method": "method3",
                        "max_wind_speed": v50,
                        "standard_density_wind_speed": v50_std,
                        "observed_max": observed_max,
                    })
                    continue

            # Fallback: use sustained result × 1.4
            sustained_row = sustained_by_height.get(height)
            if sustained_row is not None:
                v50 = sustained_row["max_wind_speed"] * 1.4
                observed_max = sustained_row["observed_max"]
                air_density_at_height = calculate_air_density_for_height(
                    height=height,
                    reference_density=air_density,
                    reference_height=reference_height,
                )
                v50_std = convert_to_standard_air_density(v50, air_density_at_height)

                rows.append({
                    "height": height,
                    "interpolation_marker": sustained_row.get("interpolation_marker"),
                    "wind_speed_type": "extreme",
                    "method": "method3",
                    "max_wind_speed": v50,
                    "standard_density_wind_speed": v50_std,
                    "observed_max": observed_max,
                })

        result_df = pl.DataFrame(rows) if rows else self._create_empty_dataframe()

        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=FiftyYearMaxWindResultSchema,
            data=result_df,
            metadata=metadata,
        )

    def _get_air_density_and_reference(
        self,
        input: SingleMastAnalysisInput,
        sensors: list[SensorColumn],
    ) -> tuple[float, float]:
        """Get air density and reference height.

        Args:
            input: Analysis input
            sensors: List of sensor metadata

        Returns:
            Tuple of (air_density, reference_height)
        """
        air_density = input.parameters.air_density

        reference_height = self._get_reference_height_from_sensors(sensors, default=10.0)
        return air_density, reference_height

    def _find_wind_speed_sensor(
        self,
        sensors: list[SensorColumn],
        height: float,
        stat_type: str,
    ) -> SensorColumn | None:
        """Find a WindSpeed sensor at the exact given height with the specified stat_type.

        Args:
            sensors: List of sensor metadata
            height: Target height in meters
            stat_type: Statistic type (e.g., "avg", "max")

        Returns:
            Matching SensorColumn or None
        """
        return next(
            (
                s
                for s in sensors
                if s.sensor_type == "WindSpeed" and s.stat_type == stat_type and s.height == height
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
        """Create an empty DataFrame with FiftyYearMaxWindResultSchema columns.

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
            "observed_max": pl.Series([], dtype=pl.Float64),
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
