"""Vertical profile analyzer for power law fitting and wind shear analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Domain service for vertical wind profile analysis including power law
             fitting and wind shear calculations between height levels.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np
import polars as pl
from scipy.stats import linregress

from cleanmast.subdomains.assessment.domain.value_objects.analysis_metadata import (
    AnalysisMetadata,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.domain.value_objects.schemas import (
    VerticalProfileSchema,
    WindShearSchema,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn

if TYPE_CHECKING:
    from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import (
        SingleMastAnalysisInput,
    )


@dataclass(frozen=True)
class VerticalProfileConstants:
    """Constants for vertical profile analysis."""

    # Minimum number of heights required for power law fitting
    MIN_HEIGHTS_FOR_FIT: int = 2

    # Minimum number of samples required per height for analysis
    MIN_SAMPLES: int = 10

    # Minimum R² value for valid power law fit
    MIN_R_SQUARED: float = 0.5

    # Reference height for power law calculations (m)
    DEFAULT_REF_HEIGHT: float = 10.0


class VerticalProfileAnalyzer:
    """Analyze vertical wind profiles using power law and shear calculations.

    This is a domain service that encapsulates the calculation logic for:
    - Power law fitting: v = v_ref * (h/h_ref)^α
    - Wind shear exponent calculation between height pairs
    - Shear matrix generation for all height combinations

    Key formulas:
        Power Law: v = v_ref * (h/h_ref)^α
        Log-linear fit: ln(v) = ln(v_ref) - α*ln(h_ref) + α*ln(h)
        Shear between heights: α = ln(v2/v1) / ln(h2/h1)

    Typical Alpha Values:
        - Smooth (water): 0.10-0.12
        - Open (grassland): 0.12-0.16
        - Rough (suburban): 0.16-0.25
        - Very rough (urban): 0.25-0.40
    """

    def __init__(self) -> None:
        """Initialize the vertical profile analyzer with constants."""
        self.constants = VerticalProfileConstants()

    def analyze_vertical_profile(
        self,
        input: "SingleMastAnalysisInput",
    ) -> AnalysisResult[VerticalProfileSchema]:
        """Analyze vertical wind profile for all heights.

        For each height, calculate mean wind speed, standard deviation, and
        fit power law to estimate shear exponent (alpha) and R².

        Args:
            input: SingleMastAnalysisInput containing time series data and parameters

        Returns:
            AnalysisResult with VerticalProfileSchema containing profile data
        """
        df = input.time_series.df
        sensors = input.time_series.sensors

        # Filter sensors to only wind speed sensors
        ws_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]

        if not ws_sensors:
            return self._create_empty_profile_result(input, "No wind speed sensors found")

        # Calculate vertical profile for all heights
        result_df = self._process_vertical_profile(df, ws_sensors)

        # Create metadata
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=VerticalProfileSchema,
            data=result_df,
            metadata=metadata,
        )

    def fit_power_law(
        self,
        heights: list[float],
        wind_speeds: list[float],
    ) -> tuple[float | None, float | None]:
        """Fit power law to height-speed data using log-linear regression.

        Power law: v = v_ref * (h/h_ref)^α
        Linearized: ln(v) = ln(v_ref) + α*ln(h) - α*ln(h_ref)

        Performs log-linear regression: ln(v) vs ln(h)
        Slope = α (shear exponent)

        Args:
            heights: List of heights in meters (must be > 0)
            wind_speeds: List of wind speeds in m/s (must be > 0)

        Returns:
            Tuple of (alpha, r_squared) or (None, None) if fitting fails
        """
        if len(heights) < self.constants.MIN_HEIGHTS_FOR_FIT:
            return None, None

        if len(heights) != len(wind_speeds):
            return None, None

        # Filter out invalid values (<= 0)
        valid_pairs = [
            (h, v) for h, v in zip(heights, wind_speeds) if h > 0 and v > 0
        ]

        if len(valid_pairs) < self.constants.MIN_HEIGHTS_FOR_FIT:
            return None, None

        valid_heights = [p[0] for p in valid_pairs]
        valid_speeds = [p[1] for p in valid_pairs]

        # Log-transform for linear regression
        log_h = np.log(valid_heights)
        log_v = np.log(valid_speeds)

        # Perform linear regression
        result = linregress(log_h, log_v)

        alpha = result.slope
        r_squared = result.rvalue**2

        # Validate results
        if not np.isfinite(alpha) or not np.isfinite(r_squared):
            return None, None

        return float(alpha), float(r_squared)

    def calculate_wind_shear(
        self,
        height1: float,
        speed1: float,
        height2: float,
        speed2: float,
    ) -> float | None:
        """Calculate wind shear exponent between two height levels.

        Formula: α = ln(v2/v1) / ln(h2/h1)

        Args:
            height1: Lower height in meters (must be > 0 and != height2)
            speed1: Wind speed at height1 in m/s (must be > 0)
            height2: Upper height in meters (must be > 0 and != height2)
            speed2: Wind speed at height2 in m/s (must be > 0)

        Returns:
            Shear exponent alpha, or None if calculation fails
        """
        # Validate inputs
        if height1 <= 0 or height2 <= 0:
            return None

        if speed1 <= 0 or speed2 <= 0:
            return None

        if height1 == height2:
            return None

        # Calculate shear using logarithmic formula
        try:
            alpha = np.log(speed2 / speed1) / np.log(height2 / height1)

            if not np.isfinite(alpha):
                return None

            return float(alpha)
        except (ValueError, ZeroDivisionError):
            return None

    def calculate_shear_matrix(
        self,
        heights: list[float],
        wind_speeds: list[float],
    ) -> list[list[float | None]]:
        """Calculate NxN shear exponent matrix for all height pairs.

        For N heights, creates an NxN matrix where element [i][j] is the
        shear exponent between height i and height j.

        Properties:
        - Diagonal: None (same height, no shear defined)
        - Symmetric: α_ij = α_ji
        - Formula: α_ij = ln(v_j/v_i) / ln(h_j/h_i)

        Args:
            heights: List of N heights in meters
            wind_speeds: List of N wind speeds in m/s

        Returns:
            NxN matrix of shear exponents (None on diagonal or if invalid)
        """
        n = len(heights)

        if n == 0 or len(wind_speeds) != n:
            return []

        # Initialize NxN matrix with None
        matrix: list[list[float | None]] = [[None] * n for _ in range(n)]

        # Calculate shear for all pairs
        for i in range(n):
            for j in range(n):
                if i == j:
                    # Diagonal: no shear defined
                    matrix[i][j] = None
                else:
                    alpha = self.calculate_wind_shear(
                        heights[i], wind_speeds[i],
                        heights[j], wind_speeds[j]
                    )
                    matrix[i][j] = alpha

        return matrix

    def _process_vertical_profile(
        self,
        df: pl.DataFrame,
        sensors: list[SensorColumn],
    ) -> pl.DataFrame:
        """Process data into vertical wind profile.

        For each height, calculate mean wind speed, standard deviation,
        and perform power law fitting.

        Args:
            df: DataFrame with timestamp and WS_* columns
            sensors: List of SensorColumn objects for wind speed sensors

        Returns:
            DataFrame with columns matching VerticalProfileSchema
        """
        rows: list[dict] = []

        # Collect height-speed statistics
        height_stats: list[tuple[float, float, float, str]] = []

        for sensor in sensors:
            height = sensor.height
            ws_col = sensor.column_name

            # Skip if column doesn't exist
            if ws_col not in df.columns:
                continue

            # Get interpolation marker from sensor
            interpolation_marker = sensor.detect_interpolation_marker()

            # Get wind speed values (filter out nulls and non-positive)
            ws_series = df.filter(
                (pl.col(ws_col).is_not_null()) & (pl.col(ws_col) > 0)
            )[ws_col]
            wind_speeds = ws_series.to_list()

            if len(wind_speeds) < self.constants.MIN_SAMPLES:
                continue

            # Calculate statistics
            mean_speed = float(np.mean(wind_speeds))
            std_speed = float(np.std(wind_speeds))

            height_stats.append((height, mean_speed, std_speed, interpolation_marker))

        # Sort by height for consistent ordering
        height_stats.sort(key=lambda x: x[0])

        # If we have enough heights, fit power law
        alpha_fit: float | None = None
        r_squared_fit: float | None = None

        if len(height_stats) >= self.constants.MIN_HEIGHTS_FOR_FIT:
            heights_for_fit = [h for h, _, _, _ in height_stats]
            speeds_for_fit = [s for _, s, _, _ in height_stats]
            alpha_fit, r_squared_fit = self.fit_power_law(
                heights_for_fit, speeds_for_fit
            )

        # Create rows for each height
        for height, mean_speed, std_speed, marker in height_stats:
            rows.append({
                "height": height,
                "interpolation_marker": marker,
                "wind_speed_mean": mean_speed,
                "wind_speed_std": std_speed,
                "alpha": alpha_fit,
                "r_squared": r_squared_fit,
            })

        return pl.DataFrame(rows) if rows else self._create_empty_profile_dataframe()

    def _create_empty_profile_result(
        self,
        input: "SingleMastAnalysisInput",
        message: str,
    ) -> AnalysisResult[VerticalProfileSchema]:
        """Create an empty vertical profile result with metadata.

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
            schema=VerticalProfileSchema,
            data=self._create_empty_profile_dataframe(),
            metadata=metadata,
        )

    def _create_empty_profile_dataframe(self) -> pl.DataFrame:
        """Create an empty DataFrame with VerticalProfileSchema columns.

        Returns:
            Empty polars DataFrame with correct schema
        """
        return pl.DataFrame({
            "height": pl.Series([], dtype=pl.Float64),
            "interpolation_marker": pl.Series([], dtype=pl.String),
            "wind_speed_mean": pl.Series([], dtype=pl.Float64),
            "wind_speed_std": pl.Series([], dtype=pl.Float64),
            "alpha": pl.Series([], dtype=pl.Float64),
            "r_squared": pl.Series([], dtype=pl.Float64),
        })

    def calculate_wind_shear_analysis(
        self,
        input: "SingleMastAnalysisInput",
    ) -> AnalysisResult[WindShearSchema]:
        """Calculate wind shear between all height pairs.

        For each pair of heights, calculate shear statistics (mean, std, min, max)
        based on time series data.

        Args:
            input: SingleMastAnalysisInput containing time series data

        Returns:
            AnalysisResult with WindShearSchema containing shear data
        """
        df = input.time_series.df
        sensors = input.time_series.sensors

        # Filter sensors to only wind speed sensors
        ws_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]

        if len(ws_sensors) < 2:
            return self._create_empty_shear_result(
                input, "Need at least 2 wind speed sensors for shear analysis"
            )

        # Calculate shear for all height pairs
        result_df = self._process_shear_analysis(df, ws_sensors)

        # Create metadata
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=WindShearSchema,
            data=result_df,
            metadata=metadata,
        )

    def _process_shear_analysis(
        self,
        df: pl.DataFrame,
        sensors: list[SensorColumn],
    ) -> pl.DataFrame:
        """Process shear analysis for all height pairs.

        For each pair of heights (h1, h2 where h2 > h1), calculate shear
        statistics from time series data.

        Args:
            df: DataFrame with timestamp and WS_* columns
            sensors: List of SensorColumn objects for wind speed sensors

        Returns:
            DataFrame with columns matching WindShearSchema
        """
        rows: list[dict] = []

        # Filter to sensors with valid data
        valid_sensors: list[tuple[float, str]] = []
        for sensor in sensors:
            ws_col = sensor.column_name
            if ws_col not in df.columns:
                continue

            # Check if we have enough valid data
            valid_count = df.filter(
                (pl.col(ws_col).is_not_null()) & (pl.col(ws_col) > 0)
            ).height

            if valid_count is not None and valid_count >= self.constants.MIN_SAMPLES:
                valid_sensors.append((sensor.height, ws_col))

        # Sort by height
        valid_sensors.sort(key=lambda x: x[0])

        # Calculate shear for all pairs (i < j)
        for i in range(len(valid_sensors)):
            for j in range(i + 1, len(valid_sensors)):
                h1, col1 = valid_sensors[i]
                h2, col2 = valid_sensors[j]

                # Calculate shear for this pair
                shear_values = self._calculate_shear_series(df, col1, col2, h1, h2)

                if shear_values:
                    rows.append({
                        "from_height": h1,
                        "to_height": h2,
                        "alpha_mean": float(np.mean(shear_values)),
                        "alpha_std": float(np.std(shear_values)),
                        "alpha_min": float(np.min(shear_values)),
                        "alpha_max": float(np.max(shear_values)),
                    })

        return pl.DataFrame(rows) if rows else self._create_empty_shear_dataframe()

    def _calculate_shear_series(
        self,
        df: pl.DataFrame,
        col1: str,
        col2: str,
        h1: float,
        h2: float,
    ) -> list[float]:
        """Calculate shear values for a time series between two heights.

        Args:
            df: DataFrame with sensor columns
            col1: Column name for lower height
            col2: Column name for upper height
            h1: Lower height in meters
            h2: Upper height in meters

        Returns:
            List of valid shear values
        """
        shear_values: list[float] = []

        # Get both series
        filtered = df.filter(
            (pl.col(col1).is_not_null()) & (pl.col(col1) > 0) &
            (pl.col(col2).is_not_null()) & (pl.col(col2) > 0)
        )

        if filtered.is_empty():
            return shear_values

        s1 = filtered[col1].to_numpy()
        s2 = filtered[col2].to_numpy()

        # Calculate shear for each time step
        for v1, v2 in zip(s1, s2):
            alpha = self.calculate_wind_shear(h1, float(v1), h2, float(v2))
            if alpha is not None:
                shear_values.append(alpha)

        return shear_values

    def _create_empty_shear_result(
        self,
        input: "SingleMastAnalysisInput",
        message: str,
    ) -> AnalysisResult[WindShearSchema]:
        """Create an empty shear result with metadata.

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
            schema=WindShearSchema,
            data=self._create_empty_shear_dataframe(),
            metadata=metadata,
        )

    def _create_empty_shear_dataframe(self) -> pl.DataFrame:
        """Create an empty DataFrame with WindShearSchema columns.

        Returns:
            Empty polars DataFrame with correct schema
        """
        return pl.DataFrame({
            "from_height": pl.Series([], dtype=pl.Float64),
            "to_height": pl.Series([], dtype=pl.Float64),
            "alpha_mean": pl.Series([], dtype=pl.Float64),
            "alpha_std": pl.Series([], dtype=pl.Float64),
            "alpha_min": pl.Series([], dtype=pl.Float64),
            "alpha_max": pl.Series([], dtype=pl.Float64),
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
