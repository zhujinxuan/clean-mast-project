"""Monthly statistics calculator service.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Domain service for calculating monthly wind statistics from time series data
"""

from datetime import datetime

import polars as pl

from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_metadata import (
    AnalysisMetadata,
)
from cleanmast.subdomains.assessment.domain.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.domain.value_objects.schemas import MonthlyWindSchema
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


class MonthlyStatsCalculator:
    """Calculate monthly wind statistics from time series data.

    This is a domain service that encapsulates the calculation logic for
    monthly wind speed statistics across different heights.
    """

    def calculate(self, input: SingleMastAnalysisInput) -> AnalysisResult[MonthlyWindSchema]:
        """Calculate monthly wind statistics from input data.

        Args:
            input: SingleMastAnalysisInput containing time series data and parameters

        Returns:
            AnalysisResult with MonthlyWindSchema containing monthly statistics
        """
        df = input.time_series.df
        sensors = input.time_series.sensors

        ws_avg_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]

        result_df = self._process_monthly_wind_data(df, ws_avg_sensors)

        # Create metadata
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=MonthlyWindSchema,
            data=result_df,
            metadata=metadata,
        )

    def _process_monthly_wind_data(
        self,
        df: pl.DataFrame,
        sensors: list[SensorColumn],
    ) -> pl.DataFrame:
        """Process data into monthly wind statistics (long format).

        For each height, calculate monthly mean/max/min wind speed.

        Args:
            df: DataFrame with timestamp and WS_* columns
            sensors: List of SensorColumn objects for wind speed sensors

        Returns:
            DataFrame with columns: month, height, interpolation_marker,
            wind_speed_mean, wind_speed_max, wind_speed_min
        """
        # Add month column
        df = df.with_columns(pl.col("timestamp").dt.month().alias("month"))

        # Process each height
        rows: list[dict] = []
        for sensor in sensors:
            height = sensor.height
            ws_col = sensor.column_name

            # Get interpolation marker from sensor
            marker = sensor.detect_interpolation_marker()

            # Calculate monthly statistics for this height
            monthly_stats = df.group_by("month").agg([
                pl.col(ws_col).mean().alias("wind_speed_mean"),
                pl.col(ws_col).max().alias("wind_speed_max"),
                pl.col(ws_col).min().alias("wind_speed_min"),
            ]).sort("month")

            # Convert to rows
            for row in monthly_stats.iter_rows(named=True):
                rows.append({
                    "month": row["month"],
                    "height": height,
                    "interpolation_marker": marker,
                    "wind_speed_mean": row["wind_speed_mean"],
                    "wind_speed_max": row["wind_speed_max"],
                    "wind_speed_min": row["wind_speed_min"],
                })

        return pl.DataFrame(rows)

    def _get_time_range(self, df: pl.DataFrame) -> str:
        """Get time range string from DataFrame.

        Args:
            df: DataFrame with timestamp column

        Returns:
            String representation of time range
        """
        min_ts = df["timestamp"].min()
        max_ts = df["timestamp"].max()
        return f"{min_ts} to {max_ts}"
