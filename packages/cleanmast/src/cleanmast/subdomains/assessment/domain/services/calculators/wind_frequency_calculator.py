"""Wind frequency calculator service for wind speed distribution analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Domain service for calculating wind frequency distributions by speed bins
"""

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
    WindFrequencySchema,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn

if TYPE_CHECKING:
    from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import (
        SingleMastAnalysisInput,
    )


@dataclass(frozen=True)
class WindFrequencyConstants:
    """Constants for wind frequency calculations."""

    # Bin size for wind speed histogram (m/s)
    BIN_SIZE: float = 1.0

    # Maximum bin value (m/s) - bins go from 0 to MAX_BIN, then [MAX_BIN, ∞)
    MAX_BIN: float = 28.0

    # Hours per year (used for occurrence calculations)
    HOURS_PER_YEAR: float = 8760.0

    # Productive wind speed range for wind turbines (m/s)
    PRODUCTIVE_RANGE: tuple[float, float] = (3.0, 25.0)

    # Minimum number of samples required for analysis
    MIN_SAMPLES: int = 10

    # Standard air density (kg/m³)
    AIR_DENSITY: float = 1.225


class WindFrequencyCalculator:
    """Calculate wind frequency distributions and power frequency analysis.

    This is a domain service that encapsulates the calculation logic for:
    - Wind speed histogram (frequency by 1 m/s bins)
    - Power frequency distribution (energy contribution by bin)
    - Productive range statistics (3-25 m/s)

    Key formulas:
        P = 0.5 * ρ * v³ (wind power density, W/m²)
        frequency = count_bin / total_count
        power_frequency = sum(power_in_bin) / total_power
        occurrence_hours = frequency * 8760
        power_hours = power_frequency * 8760
    """

    def __init__(self) -> None:
        """Initialize the wind frequency calculator with constants."""
        self.constants = WindFrequencyConstants()

    def analyze_by_height(
        self,
        input: "SingleMastAnalysisInput",
    ) -> AnalysisResult[WindFrequencySchema]:
        """Analyze wind frequency distribution for all heights.

        For each height, calculate wind speed frequency distribution using 1 m/s bins
        from 0 to 28 m/s, and calculate power frequency distribution.

        Args:
            input: SingleMastAnalysisInput containing time series data and parameters

        Returns:
            AnalysisResult with WindFrequencySchema containing frequency by speed bin
        """
        df = input.time_series.df
        sensors = input.time_series.sensors

        ws_avg_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]

        if not ws_avg_sensors:
            return self._create_empty_result(input, "No wind speed sensors found")

        result_df = self._process_frequency_analysis(df, ws_avg_sensors)

        # Create metadata
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=WindFrequencySchema,
            data=result_df,
            metadata=metadata,
        )

    def calculate_histogram(
        self,
        wind_speeds: list[float],
    ) -> dict[int, int]:
        """Create wind speed histogram with 1 m/s bins.

        Bins are: [0,1), [1,2), ..., [27,28), [28,∞)

        Args:
            wind_speeds: List of wind speed measurements in m/s

        Returns:
            Dictionary mapping bin index to count
            Bin 0 = [0,1), Bin 1 = [1,2), ..., Bin 28 = [28,∞)
        """
        if not wind_speeds:
            return {}

        # Convert to numpy array for efficient processing
        ws_array = np.array(wind_speeds, dtype=np.float64)

        # Calculate bin indices (floor of wind speed, capped at MAX_BIN)
        bin_indices = np.floor(ws_array).astype(np.int64)
        bin_indices = np.clip(bin_indices, 0, int(self.constants.MAX_BIN))

        # Count occurrences in each bin
        histogram: dict[int, int] = {}
        for bin_idx in range(int(self.constants.MAX_BIN) + 1):
            count = int(np.sum(bin_indices == bin_idx))
            if count > 0:
                histogram[bin_idx] = count

        return histogram

    def calculate_power_frequency(
        self,
        wind_speeds: list[float],
        air_density: float | None = None,
    ) -> dict[int, float]:
        """Calculate power frequency distribution by wind speed bin.

        Power frequency is the proportion of total energy in each bin.
        Formula: power_frequency_bin = sum(power_in_bin) / total_power

        Args:
            wind_speeds: List of wind speed measurements in m/s
            air_density: Air density in kg/m³ (default: 1.225)

        Returns:
            Dictionary mapping bin index to power frequency
        """
        if not wind_speeds:
            return {}

        rho = air_density if air_density is not None else self.constants.AIR_DENSITY

        # Convert to numpy array
        ws_array = np.array(wind_speeds, dtype=np.float64)

        # Calculate power for each measurement: P = 0.5 * ρ * v³
        power = 0.5 * rho * ws_array**3

        # Calculate total power
        total_power = np.sum(power)
        if total_power == 0:
            return {}

        # Calculate bin indices
        bin_indices = np.floor(ws_array).astype(np.int64)
        bin_indices = np.clip(bin_indices, 0, int(self.constants.MAX_BIN))

        # Calculate power sum for each bin
        power_freq: dict[int, float] = {}
        for bin_idx in range(int(self.constants.MAX_BIN) + 1):
            mask = bin_indices == bin_idx
            bin_power_sum = np.sum(power[mask])
            power_freq[bin_idx] = float(bin_power_sum / total_power)

        return power_freq

    def calculate_range_summary(
        self,
        wind_speeds: list[float],
        min_speed: float | None = None,
        max_speed: float | None = None,
    ) -> dict[str, float]:
        """Calculate summary statistics for a wind speed range.

        Default range is the productive range for wind turbines: 3-25 m/s.

        Args:
            wind_speeds: List of wind speed measurements in m/s
            min_speed: Minimum speed for range (default: PRODUCTIVE_RANGE[0])
            max_speed: Maximum speed for range (default: PRODUCTIVE_RANGE[1])

        Returns:
            Dictionary with statistics:
                - count: Number of measurements in range
                - frequency: Proportion of total measurements
                - mean_speed: Mean wind speed in range
                - mean_power: Mean power density in range (W/m²)
                - occurrence_hours: Estimated hours per year in range
        """
        if not wind_speeds:
            return {
                "count": 0.0,
                "frequency": 0.0,
                "mean_speed": 0.0,
                "mean_power": 0.0,
                "occurrence_hours": 0.0,
            }

        # Use default productive range if not specified
        min_val = min_speed if min_speed is not None else self.constants.PRODUCTIVE_RANGE[0]
        max_val = max_speed if max_speed is not None else self.constants.PRODUCTIVE_RANGE[1]

        # Convert to numpy array
        ws_array = np.array(wind_speeds, dtype=np.float64)

        # Filter to range
        mask = (ws_array >= min_val) & (ws_array < max_val)
        range_ws = ws_array[mask]

        total_count = len(ws_array)
        range_count = len(range_ws)

        if range_count == 0:
            return {
                "count": 0.0,
                "frequency": 0.0,
                "mean_speed": 0.0,
                "mean_power": 0.0,
                "occurrence_hours": 0.0,
            }

        # Calculate statistics
        frequency = range_count / total_count if total_count > 0 else 0.0
        mean_speed = float(np.mean(range_ws))

        # Calculate mean power density: P = 0.5 * ρ * v³
        rho = self.constants.AIR_DENSITY
        mean_power = float(0.5 * rho * np.mean(range_ws**3))

        # Calculate occurrence hours
        occurrence_hours = frequency * self.constants.HOURS_PER_YEAR

        return {
            "count": float(range_count),
            "frequency": frequency,
            "mean_speed": mean_speed,
            "mean_power": mean_power,
            "occurrence_hours": occurrence_hours,
        }

    def _process_frequency_analysis(
        self,
        df: pl.DataFrame,
        sensors: list[SensorColumn],
    ) -> pl.DataFrame:
        """Process data into wind frequency by speed bins (long format).

        For each height, calculate wind speed frequency and power frequency
        for 1 m/s bins from 0 to 28 m/s.

        Args:
            df: DataFrame with timestamp and WS_* columns
            sensors: List of SensorColumn objects for wind speed sensors

        Returns:
            DataFrame with columns matching WindFrequencySchema
        """
        rows: list[dict] = []

        for sensor in sensors:
            height = sensor.height
            ws_col = sensor.column_name

            # Skip if column doesn't exist
            if ws_col not in df.columns:
                continue

            # Get interpolation marker from sensor
            interpolation_marker = sensor.detect_interpolation_marker()

            # Get wind speed values (filter out nulls)
            ws_series = df.filter(pl.col(ws_col).is_not_null())[ws_col]
            wind_speeds = ws_series.to_list()

            if len(wind_speeds) < self.constants.MIN_SAMPLES:
                continue

            # Calculate histogram (frequency by bin)
            histogram = self.calculate_histogram(wind_speeds)
            total_count = sum(histogram.values())

            if total_count == 0:
                continue

            # Calculate power frequency by bin
            power_freq = self.calculate_power_frequency(wind_speeds)

            # Create rows for each bin
            for bin_idx in range(int(self.constants.MAX_BIN) + 1):
                bin_start = float(bin_idx)
                bin_end = float(bin_idx + 1) if bin_idx < self.constants.MAX_BIN else float("inf")
                bin_center = bin_start + 0.5

                # Get count for this bin
                count = histogram.get(bin_idx, 0)
                frequency = count / total_count if total_count > 0 else 0.0

                # Calculate occurrence hours
                occurrence_hours = frequency * self.constants.HOURS_PER_YEAR

                # Get power frequency for this bin
                p_freq = power_freq.get(bin_idx, 0.0)
                power_hours = p_freq * self.constants.HOURS_PER_YEAR

                rows.append({
                    "height": height,
                    "interpolation_marker": interpolation_marker,
                    "bin_start": bin_start,
                    "bin_end": bin_end if bin_idx < self.constants.MAX_BIN else 100.0,  # Cap at 100 for last bin
                    "bin_center": bin_center,
                    "frequency": frequency,
                    "occurrence_hours": occurrence_hours,
                    "power_frequency": p_freq,
                    "power_hours": power_hours,
                })

        return pl.DataFrame(rows) if rows else self._create_empty_dataframe()

    def _create_empty_result(
        self,
        input: "SingleMastAnalysisInput",
        message: str,
    ) -> AnalysisResult[WindFrequencySchema]:
        """Create an empty wind frequency result with metadata.

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
            schema=WindFrequencySchema,
            data=self._create_empty_dataframe(),
            metadata=metadata,
        )

    def _create_empty_dataframe(self) -> pl.DataFrame:
        """Create an empty DataFrame with WindFrequencySchema columns.

        Returns:
            Empty polars DataFrame with correct schema
        """
        return pl.DataFrame({
            "height": pl.Series([], dtype=pl.Float64),
            "interpolation_marker": pl.Series([], dtype=pl.String),
            "bin_start": pl.Series([], dtype=pl.Float64),
            "bin_end": pl.Series([], dtype=pl.Float64),
            "bin_center": pl.Series([], dtype=pl.Float64),
            "frequency": pl.Series([], dtype=pl.Float64),
            "occurrence_hours": pl.Series([], dtype=pl.Float64),
            "power_frequency": pl.Series([], dtype=pl.Float64),
            "power_hours": pl.Series([], dtype=pl.Float64),
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
