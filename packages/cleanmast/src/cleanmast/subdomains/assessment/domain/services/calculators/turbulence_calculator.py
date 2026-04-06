"""Turbulence calculator service for wind turbulence intensity analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Domain service for calculating turbulence intensity statistics and IEC category classification
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np
import polars as pl

from cleanmast.subdomains.assessment.domain.value_objects.analysis_metadata import (
    AnalysisMetadata,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TurbulenceSchema,
    TurbulenceSectorSchema,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn

if TYPE_CHECKING:
    from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import (
        SingleMastAnalysisInput,
    )


@dataclass(frozen=True)
class TurbulenceConstants:
    """Constants for turbulence intensity calculations."""

    # Minimum number of samples required for analysis
    MIN_SAMPLES: int = 10

    # Z-score for P90 representative TI (90th percentile)
    TI_REP_Z: float = 1.28

    # Minimum wind speed for TI calculation (avoid division by small numbers)
    MIN_WIND_SPEED: float = 1.0

    # Number of direction sectors (16: N, NNE, NE, ..., NNW)
    NUM_SECTORS: int = 16

    # Sector width in degrees
    SECTOR_WIDTH: float = 22.5


# Sector names for 16-sector wind rose
SECTOR_NAMES = [
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
]


class TurbulenceCalculator:
    """Calculate turbulence intensity statistics and IEC category classification.

    This is a domain service that encapsulates the calculation logic for:
    - Turbulence intensity time series calculation
    - Representative turbulence intensity (P90)
    - IEC category classification
    - Analysis by wind speed bins and direction sectors

    Key formulas:
        TI = σ / max(μ, 1.0)
        TI_rep = mean(TI) + 1.28 * std(TI)  # P90
        TI_IEC = I_ref * (0.75 + 5.6/V)
    """

    def __init__(self) -> None:
        """Initialize the turbulence calculator with constants."""
        self.constants = TurbulenceConstants()
        self.iec_categories = {"A+": 0.18, "A": 0.16, "B": 0.14, "C": 0.12}

    def analyze_by_wind_speed(
        self,
        input: "SingleMastAnalysisInput",
    ) -> AnalysisResult[TurbulenceSchema]:
        """Analyze turbulence intensity by wind speed bins.

        For each height, calculate TI statistics grouped by wind speed bins.
        Uses TI = σ / max(mean, 1.0) for individual points, then aggregates.

        Args:
            input: SingleMastAnalysisInput containing time series data and parameters

        Returns:
            AnalysisResult with TurbulenceSchema containing TI by wind speed bin
        """
        df = input.time_series.df
        sensors = input.time_series.sensors

        ws_avg_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]

        if not ws_avg_sensors:
            return self._create_empty_turbulence_result(
                input, "No wind speed sensors found"
            )

        result_df = self._process_wind_speed_analysis(df, ws_avg_sensors)

        # Create metadata
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=TurbulenceSchema,
            data=result_df,
            metadata=metadata,
        )

    def analyze_by_sector(
        self,
        input: "SingleMastAnalysisInput",
    ) -> AnalysisResult[TurbulenceSectorSchema]:
        """Analyze turbulence intensity by direction sectors.

        For each height, calculate TI statistics grouped by 16 direction sectors.
        Requires wind direction sensors to be present.

        Args:
            input: SingleMastAnalysisInput containing time series data and parameters

        Returns:
            AnalysisResult with TurbulenceSectorSchema containing TI by sector
        """
        df = input.time_series.df
        sensors = input.time_series.sensors

        # Filter sensors
        ws_avg_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]
        wd_avg_sensors = [s for s in sensors if s.sensor_type == "WindDirection" and s.stat_type == "avg"]

        if not ws_avg_sensors:
            return self._create_empty_sector_result(
                input, "No wind speed sensors found"
            )

        if not wd_avg_sensors:
            return self._create_empty_sector_result(
                input, "No wind direction sensors found"
            )

        result_df = self._process_sector_analysis(df, ws_avg_sensors, wd_avg_sensors)

        # Create metadata
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=TurbulenceSectorSchema,
            data=result_df,
            metadata=metadata,
        )

    def calculate_ti_series(
        self,
        wind_speeds: list[float],
        rolling_window: int = 600,  # 10 minutes at 1Hz = 600 samples
    ) -> list[float]:
        """Calculate turbulence intensity time series.

        TI is calculated as the ratio of standard deviation to mean wind speed
        over a rolling window. Mean wind speed is clamped to a minimum of 1.0 m/s
        to avoid division by small numbers.

        Formula: TI = σ / max(μ, 1.0)

        Args:
            wind_speeds: List of wind speed measurements in m/s
            rolling_window: Number of samples for rolling window (default 600 for 10 min)

        Returns:
            List of TI values, with None for positions where window is insufficient
        """
        if len(wind_speeds) < rolling_window:
            return [None] * len(wind_speeds)  # type: ignore

        # Convert to numpy for efficient calculation
        ws_array = np.array(wind_speeds)

        # Calculate rolling statistics using convolution for efficiency
        kernel = np.ones(rolling_window) / rolling_window
        mean_values = np.convolve(ws_array, kernel, mode="same")

        # Calculate rolling standard deviation
        # Var = E[X²] - E[X]²
        mean_sq_values = np.convolve(ws_array**2, kernel, mode="same")
        variance = mean_sq_values - mean_values**2
        variance = np.maximum(variance, 0)  # Handle numerical errors
        std_values = np.sqrt(variance)

        # Calculate TI with minimum wind speed clamping
        ti_values = std_values / np.maximum(mean_values, self.constants.MIN_WIND_SPEED)

        # Set None for edge values where window is incomplete
        half_window = rolling_window // 2
        ti_list = ti_values.tolist()
        for i in range(half_window):
            ti_list[i] = None
            ti_list[-(i + 1)] = None

        return ti_list

    def calculate_representative_ti(
        self,
        ti_values: list[float | None],
    ) -> float | None:
        """Calculate representative turbulence intensity (P90).

        Uses the formula: TI_rep = mean(TI) + 1.28 * std(TI)
        This approximates the 90th percentile of the TI distribution.

        Args:
            ti_values: List of TI values (may contain None)

        Returns:
            Representative TI value or None if insufficient data
        """
        # Filter out None values
        valid_ti = [ti for ti in ti_values if ti is not None]

        if len(valid_ti) < self.constants.MIN_SAMPLES:
            return None

        mean_ti = float(np.mean(valid_ti))
        std_ti = float(np.std(valid_ti, ddof=1))

        return mean_ti + self.constants.TI_REP_Z * std_ti

    def calculate_iec_ti(
        self,
        wind_speed: float,
        i_ref: float,
    ) -> float | None:
        """Calculate IEC reference turbulence intensity.

        Formula: TI_IEC = I_ref * (0.75 + 5.6/V)
        where V is the wind speed in m/s.

        Args:
            wind_speed: Mean wind speed in m/s
            i_ref: Reference turbulence intensity for IEC category

        Returns:
            IEC reference TI or None if wind_speed <= 0
        """
        if wind_speed <= 0:
            return None

        return i_ref * (0.75 + 5.6 / wind_speed)

    def classify_iec_category(
        self,
        ti_values: Sequence[float | None],
        wind_speeds: Sequence[float],
    ) -> str:
        """Classify IEC turbulence category based on measured TI vs IEC reference.

        Compares measured representative TI against IEC reference TI for each
        wind speed bin, then determines the most appropriate IEC category.

        Args:
            ti_values: List of measured TI values
            wind_speeds: List of corresponding wind speeds

        Returns:
            IEC category ("A+", "A", "B", or "C")
        """
        # Filter valid pairs
        valid_pairs = [
            (ti, ws)
            for ti, ws in zip(ti_values, wind_speeds)
            if ti is not None and ws > 0
        ]

        if len(valid_pairs) < self.constants.MIN_SAMPLES:
            return "C"  # Default to lowest turbulence if insufficient data

        # Calculate representative TI
        ti_list = [pair[0] for pair in valid_pairs]
        rep_ti = self.calculate_representative_ti(ti_list)

        if rep_ti is None:
            return "C"

        # Calculate mean wind speed
        mean_ws = float(np.mean([pair[1] for pair in valid_pairs]))

        # Compare against each IEC category
        best_category = "C"
        min_difference = float("inf")

        for category, i_ref in self.iec_categories.items():
            iec_ti = self.calculate_iec_ti(mean_ws, i_ref)
            if iec_ti is not None:
                difference = abs(rep_ti - iec_ti)
                if difference < min_difference:
                    min_difference = difference
                    best_category = category

        return best_category

    def _find_matching_sd_sensor(
        self,
        avg_sensor: SensorColumn,
        sensors: list[SensorColumn],
    ) -> SensorColumn | None:
        """Find the SD sensor at the same height as the avg sensor.

        Args:
            avg_sensor: WindSpeed avg sensor
            sensors: List of available sensors

        Returns:
            Matching SD sensor or None if not found
        """
        height = avg_sensor.height
        sd_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "sd"]

        if not sd_sensors:
            return None

        # Find closest by height (exact match preferred)
        closest = min(sd_sensors, key=lambda s: abs(s.height - height))

        # Only return if within reasonable tolerance (e.g., 5m)
        if abs(closest.height - height) <= 5.0:
            return closest

        return None

    def _process_wind_speed_analysis(
        self,
        df: pl.DataFrame,
        sensors: list[SensorColumn],
    ) -> pl.DataFrame:
        """Process data into TI by wind speed bins (long format).

        For each height, calculate mean TI, std TI, representative TI,
        and IEC category for wind speed bins using paired avg and sd sensors.

        Args:
            df: DataFrame with timestamp and WS_* columns
            sensors: List of SensorColumn objects for wind speed sensors (avg sensors)

        Returns:
            DataFrame with columns matching TurbulenceSchema
        """
        rows: list[dict] = []

        for sensor in sensors:
            height = sensor.height
            avg_col = sensor.column_name

            # Find matching sd sensor for this height
            sd_sensor = self._find_matching_sd_sensor(sensor, sensors)
            if sd_sensor is None:
                continue
            sd_col = sd_sensor.column_name

            # Skip if either column doesn't exist
            if avg_col not in df.columns or sd_col not in df.columns:
                continue

            # Get interpolation marker from avg sensor
            interpolation_marker = sensor.detect_interpolation_marker()

            # Filter valid data (both avg and sd must be non-null and positive)
            valid_df = df.filter(
                (pl.col(avg_col).is_not_null()) &
                (pl.col(avg_col) > 0) &
                (pl.col(sd_col).is_not_null()) &
                (pl.col(sd_col) > 0)
            )

            if valid_df.is_empty():
                continue

            # Calculate TI for each row: TI = sd / max(avg, 1.0)
            ti_expr = (pl.col(sd_col) / pl.max_horizontal(pl.col(avg_col), pl.lit(1.0))).clip(upper_bound=1.0)

            # Add wind speed bin (based on avg wind speed)
            df_with_ti = valid_df.with_columns([
                ti_expr.alias("ti"),
                pl.col(avg_col).floor().cast(pl.Int64).alias("ws_bin"),
            ])

            # Group by wind speed bin and calculate TI statistics
            bin_stats = (
                df_with_ti.group_by("ws_bin")
                .agg([
                    pl.col("ti").mean().alias("mean_ti"),
                    pl.col("ti").std().alias("std_ti"),
                    pl.col("ti").count().alias("count"),
                ])
                .sort("ws_bin")
            )

            # Calculate TI statistics for each bin
            for row in bin_stats.iter_rows(named=True):
                ws_bin = row["ws_bin"]
                mean_ti = row["mean_ti"]
                std_ti = row["std_ti"] if row["std_ti"] is not None else 0.0
                count = row["count"]

                # Skip bins with insufficient samples
                if count < self.constants.MIN_SAMPLES:
                    continue

                # Calculate representative TI (P90)
                rep_ti = mean_ti + self.constants.TI_REP_Z * std_ti

                # Classify IEC category
                # Create synthetic TI list for classification
                ti_values = [mean_ti] * int(count)
                wind_speeds = [float(ws_bin)] * int(count)
                iec_category = self.classify_iec_category(ti_values, wind_speeds)

                rows.append({
                    "wind_speed_bin": ws_bin,
                    "height": height,
                    "interpolation_marker": interpolation_marker,
                    "mean_ti": mean_ti,
                    "std_ti": std_ti,
                    "representative_ti": rep_ti,
                    "iec_category": iec_category,
                })

        return pl.DataFrame(rows) if rows else self._create_empty_turbulence_dataframe()

    def _process_sector_analysis(
        self,
        df: pl.DataFrame,
        ws_sensors: list[SensorColumn],
        wd_sensors: list[SensorColumn],
    ) -> pl.DataFrame:
        """Process data into TI by direction sectors (long format).

        For each height, calculate mean TI and representative TI by 16 direction sectors
        using paired avg and sd sensors.

        Args:
            df: DataFrame with timestamp, WS_*, and WD_* columns
            ws_sensors: List of SensorColumn objects for wind speed sensors (avg sensors)
            wd_sensors: List of SensorColumn objects for wind direction sensors

        Returns:
            DataFrame with columns matching TurbulenceSectorSchema
        """
        rows: list[dict] = []

        # Match wind speed sensors with direction sensors at similar heights
        for ws_sensor in ws_sensors:
            height = ws_sensor.height
            avg_col = ws_sensor.column_name

            # Find matching sd sensor for this height
            sd_sensor = self._find_matching_sd_sensor(ws_sensor, ws_sensors)
            if sd_sensor is None:
                continue
            sd_col = sd_sensor.column_name

            # Find matching direction sensor (closest height)
            wd_sensor = self._find_matching_direction_sensor(height, wd_sensors)
            if wd_sensor is None:
                continue
            wd_col = wd_sensor.column_name

            # Skip if columns don't exist
            if avg_col not in df.columns or sd_col not in df.columns or wd_col not in df.columns:
                continue

            # Get interpolation marker from sensor
            interpolation_marker = ws_sensor.detect_interpolation_marker()

            # Filter valid data (all three must be non-null)
            valid_df = df.filter(
                (pl.col(avg_col).is_not_null()) &
                (pl.col(avg_col) > 0) &
                (pl.col(sd_col).is_not_null()) &
                (pl.col(sd_col) > 0) &
                (pl.col(wd_col).is_not_null())
            )

            if valid_df.is_empty():
                continue

            # Calculate TI for each row
            ti_expr = (pl.col(sd_col) / pl.max_horizontal(pl.col(avg_col), pl.lit(1.0))).clip(upper_bound=1.0)

            # Calculate sector for each row
            sector_expr = ((pl.col(wd_col) / self.constants.SECTOR_WIDTH).floor() % self.constants.NUM_SECTORS).cast(pl.Int64)

            df_with_ti = valid_df.with_columns([
                ti_expr.alias("ti"),
                sector_expr.alias("sector"),
            ])

            # Group by sector and calculate TI statistics
            sector_stats = (
                df_with_ti.group_by("sector")
                .agg([
                    pl.col("ti").mean().alias("mean_ti"),
                    pl.col("ti").std().alias("std_ti"),
                    pl.col("ti").count().alias("count"),
                ])
                .sort("sector")
            )

            for row in sector_stats.iter_rows(named=True):
                sector = int(row["sector"])
                mean_ti = row["mean_ti"]
                std_ti = row["std_ti"] if row["std_ti"] is not None else 0.0
                count = row["count"]

                # Skip sectors with insufficient samples
                if count < self.constants.MIN_SAMPLES:
                    continue

                # Calculate representative TI (P90)
                rep_ti = mean_ti + self.constants.TI_REP_Z * std_ti

                # Classify IEC category
                ti_values = [mean_ti] * int(count)
                wind_speeds = [float(sector)] * int(count)
                iec_category = self.classify_iec_category(ti_values, wind_speeds)

                rows.append({
                    "sector": sector,
                    "sector_name": SECTOR_NAMES[sector],
                    "height": height,
                    "interpolation_marker": interpolation_marker,
                    "mean_ti": mean_ti,
                    "representative_ti": rep_ti,
                    "iec_category": iec_category,
                })

        return pl.DataFrame(rows) if rows else self._create_empty_sector_dataframe()

    def _find_matching_direction_sensor(
        self,
        height: float,
        wd_sensors: list[SensorColumn],
    ) -> SensorColumn | None:
        """Find the direction sensor closest to the given height.

        Args:
            height: Target height in meters
            wd_sensors: List of available wind direction sensors

        Returns:
            Closest matching sensor or None if no sensors available
        """
        if not wd_sensors:
            return None

        # Find sensor with minimum height difference
        closest = min(wd_sensors, key=lambda s: abs(s.height - height))

        # Only return if within reasonable tolerance (e.g., 20m)
        if abs(closest.height - height) <= 20.0:
            return closest

        return None

    def _create_empty_turbulence_result(
        self,
        input: "SingleMastAnalysisInput",
        message: str,
    ) -> AnalysisResult[TurbulenceSchema]:
        """Create an empty turbulence result with metadata.

        Args:
            input: Input specification
            message: Error/message string

        Returns:
            Empty AnalysisResult with proper schema
        """
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(input.time_series.df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=TurbulenceSchema,
            data=self._create_empty_turbulence_dataframe(),
            metadata=metadata,
        )

    def _create_empty_sector_result(
        self,
        input: "SingleMastAnalysisInput",
        message: str,
    ) -> AnalysisResult[TurbulenceSectorSchema]:
        """Create an empty sector result with metadata.

        Args:
            input: Input specification
            message: Error/message string

        Returns:
            Empty AnalysisResult with proper schema
        """
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(input.time_series.df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=TurbulenceSectorSchema,
            data=self._create_empty_sector_dataframe(),
            metadata=metadata,
        )

    def _create_empty_turbulence_dataframe(self) -> pl.DataFrame:
        """Create an empty DataFrame with TurbulenceSchema columns.

        Returns:
            Empty polars DataFrame with correct schema
        """
        return pl.DataFrame({
            "wind_speed_bin": pl.Series([], dtype=pl.Int64),
            "height": pl.Series([], dtype=pl.Float64),
            "interpolation_marker": pl.Series([], dtype=pl.String),
            "mean_ti": pl.Series([], dtype=pl.Float64),
            "std_ti": pl.Series([], dtype=pl.Float64),
            "representative_ti": pl.Series([], dtype=pl.Float64),
            "iec_category": pl.Series([], dtype=pl.String),
        })

    def _create_empty_sector_dataframe(self) -> pl.DataFrame:
        """Create an empty DataFrame with TurbulenceSectorSchema columns.

        Returns:
            Empty polars DataFrame with correct schema
        """
        return pl.DataFrame({
            "sector": pl.Series([], dtype=pl.Int64),
            "sector_name": pl.Series([], dtype=pl.String),
            "height": pl.Series([], dtype=pl.Float64),
            "interpolation_marker": pl.Series([], dtype=pl.String),
            "mean_ti": pl.Series([], dtype=pl.Float64),
            "representative_ti": pl.Series([], dtype=pl.Float64),
            "iec_category": pl.Series([], dtype=pl.String),
        })

    def _get_time_range(self, df: pl.DataFrame) -> str:
        """Extract time range from DataFrame as formatted string.

        Args:
            df: DataFrame with timestamp column

        Returns:
            Time range string (e.g., "2023-01-01 to 2023-12-31") or "Unknown"
        """
        if "timestamp" not in df.columns or df.is_empty():
            return "Unknown"

        timestamps = df["timestamp"]
        start = timestamps.min()
        end = timestamps.max()

        if start is None or end is None:
            return "Unknown"

        # Handle both datetime objects and strings
        start_str = str(start)[:10]
        end_str = str(end)[:10]

        return f"{start_str} to {end_str}"
