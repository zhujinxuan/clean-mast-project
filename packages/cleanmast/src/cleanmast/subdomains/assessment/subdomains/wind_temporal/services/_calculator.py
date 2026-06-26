"""Wind temporal analyzer service.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Domain service for analyzing temporal patterns in wind data
"""

from datetime import datetime

import polars as pl

from cleanmast.subdomains.assessment.shared.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_metadata import (
    AnalysisMetadata,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.value_objects.schemas import (
    TemporalPatternSchema,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


class WindTemporalAnalyzer:
    """Analyze temporal patterns in wind data.

    This is a domain service that encapsulates the calculation logic for
    temporal wind patterns including daily, monthly, and combined patterns.
    """

    def analyze_daily_pattern(
        self,
        input: SingleMastAnalysisInput,
    ) -> AnalysisResult[TemporalPatternSchema]:
        """Analyze daily 24-hour wind pattern.

        Aggregates data by hour (0-23) to show typical daily wind patterns.

        Args:
            input: SingleMastAnalysisInput containing time series data and parameters

        Returns:
            AnalysisResult with TemporalPatternSchema containing 24 hourly data points
        """
        df = input.time_series.df
        sensors = input.time_series.sensors

        # Get air density for power calculations
        air_density = input.parameters.air_density

        # Filter sensors to only wind speed sensors
        ws_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]

        if not ws_sensors:
            return self._create_empty_result(input, "No wind speed sensors found")

        # Calculate daily pattern for all heights
        result_df = self._process_daily_pattern(df, ws_sensors, air_density)

        # Create metadata
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=TemporalPatternSchema,
            data=result_df,
            metadata=metadata,
        )

    def analyze_monthly_pattern(
        self,
        input: SingleMastAnalysisInput,
    ) -> AnalysisResult[TemporalPatternSchema]:
        """Analyze monthly wind pattern.

        Aggregates data by month (1-12) to show seasonal wind patterns.

        Args:
            input: SingleMastAnalysisInput containing time series data and parameters

        Returns:
            AnalysisResult with TemporalPatternSchema containing 12 monthly data points
        """
        df = input.time_series.df
        sensors = input.time_series.sensors

        # Get air density for power calculations
        air_density = input.parameters.air_density

        # Filter sensors to only wind speed sensors
        ws_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]

        if not ws_sensors:
            return self._create_empty_result(input, "No wind speed sensors found")

        # Calculate monthly pattern for all heights
        result_df = self._process_monthly_pattern(df, ws_sensors, air_density)

        # Create metadata
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=TemporalPatternSchema,
            data=result_df,
            metadata=metadata,
        )

    def analyze_monthly_daily(
        self,
        input: SingleMastAnalysisInput,
    ) -> AnalysisResult[TemporalPatternSchema]:
        """Analyze combined monthly-daily wind pattern.

        Aggregates data by hour x month (24 hours x 12 months = 288 combinations)
        for faceted grid visualizations showing how daily patterns vary by season.

        Args:
            input: SingleMastAnalysisInput containing time series data and parameters

        Returns:
            AnalysisResult with TemporalPatternSchema containing hourly x monthly data
        """
        df = input.time_series.df
        sensors = input.time_series.sensors

        # Get air density for power calculations
        air_density = input.parameters.air_density

        # Filter sensors to only wind speed sensors
        ws_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]

        if not ws_sensors:
            return self._create_empty_result(input, "No wind speed sensors found")

        # Calculate monthly-daily pattern for all heights
        result_df = self._process_monthly_daily_pattern(df, ws_sensors, air_density)

        # Create metadata
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=TemporalPatternSchema,
            data=result_df,
            metadata=metadata,
        )

    def _process_daily_pattern(
        self,
        df: pl.DataFrame,
        sensors: list[SensorColumn],
        air_density: float,
    ) -> pl.DataFrame:
        """Process data into daily 24-hour pattern (long format).

        For each height, calculate mean wind speed and power for each hour (0-23).

        Args:
            df: DataFrame with timestamp and WS_* columns
            sensors: List of SensorColumn objects for wind speed sensors
            air_density: Air density in kg/m³ for power calculations

        Returns:
            DataFrame with columns matching TemporalPatternSchema
        """
        # Add hour column
        df_with_hour = df.with_columns(pl.col("timestamp").dt.hour().alias("hour"))

        rows: list[dict] = []

        for sensor in sensors:
            height = sensor.height
            ws_col = sensor.column_name

            # Skip if column doesn't exist
            if ws_col not in df.columns:
                continue

            # Calculate hourly statistics for this height
            hourly_stats = (
                df_with_hour.group_by("hour")
                .agg([
                    pl.col(ws_col).mean().alias("mean_speed"),
                    (0.5 * air_density * pl.col(ws_col).pow(3)).mean().alias("mean_power"),
                ])
                .sort("hour")
            )

            # Get first timestamp as reference for each hour
            hour_timestamps = (
                df_with_hour.group_by("hour")
                .agg([pl.col("timestamp").first().alias("timestamp")])
                .sort("hour")
            )

            # Join to get timestamps
            hourly_stats = hourly_stats.join(hour_timestamps, on="hour")

            # Convert to rows
            for row in hourly_stats.iter_rows(named=True):
                rows.append({
                    "timestamp": row["timestamp"],
                    "hour": row["hour"],
                    "month": row["timestamp"].month if hasattr(row["timestamp"], "month") else 1,
                    "wind_speed": None,
                    "wind_power": None,
                    "height": height,
                    "mean_speed": row["mean_speed"],
                    "mean_power": row["mean_power"],
                    "interpolation_marker": sensor.detect_interpolation_marker(),
                })

        return pl.DataFrame(rows) if rows else self._create_empty_dataframe()

    def _process_monthly_pattern(
        self,
        df: pl.DataFrame,
        sensors: list[SensorColumn],
        air_density: float,
    ) -> pl.DataFrame:
        """Process data into monthly pattern (long format).

        For each height, calculate mean wind speed and power for each month (1-12).

        Args:
            df: DataFrame with timestamp and WS_* columns
            sensors: List of SensorColumn objects for wind speed sensors
            air_density: Air density in kg/m³ for power calculations

        Returns:
            DataFrame with columns matching TemporalPatternSchema
        """
        # Add month column
        df_with_month = df.with_columns(pl.col("timestamp").dt.month().alias("month"))

        rows: list[dict] = []

        for sensor in sensors:
            height = sensor.height
            ws_col = sensor.column_name

            # Skip if column doesn't exist
            if ws_col not in df.columns:
                continue

            # Calculate monthly statistics for this height
            monthly_stats = (
                df_with_month.group_by("month")
                .agg([
                    pl.col(ws_col).mean().alias("mean_speed"),
                    (0.5 * air_density * pl.col(ws_col).pow(3)).mean().alias("mean_power"),
                ])
                .sort("month")
            )

            # Get first timestamp as reference for each month
            month_timestamps = (
                df_with_month.group_by("month")
                .agg([pl.col("timestamp").first().alias("timestamp")])
                .sort("month")
            )

            # Join to get timestamps
            monthly_stats = monthly_stats.join(month_timestamps, on="month")

            # Convert to rows
            for row in monthly_stats.iter_rows(named=True):
                rows.append({
                    "timestamp": row["timestamp"],
                    "hour": row["timestamp"].hour if hasattr(row["timestamp"], "hour") else 0,
                    "month": row["month"],
                    "wind_speed": None,
                    "wind_power": None,
                    "height": height,
                    "mean_speed": row["mean_speed"],
                    "mean_power": row["mean_power"],
                    "interpolation_marker": sensor.detect_interpolation_marker(),
                })

        return pl.DataFrame(rows) if rows else self._create_empty_dataframe()

    def _process_monthly_daily_pattern(
        self,
        df: pl.DataFrame,
        sensors: list[SensorColumn],
        air_density: float,
    ) -> pl.DataFrame:
        """Process data into monthly-daily combined pattern (long format).

        For each height, calculate mean wind speed and power for each
        hour x month combination (24 hours x 12 months).

        Args:
            df: DataFrame with timestamp and WS_* columns
            sensors: List of SensorColumn objects for wind speed sensors
            air_density: Air density in kg/m³ for power calculations

        Returns:
            DataFrame with columns matching TemporalPatternSchema
        """
        # Add hour and month columns
        df_with_time = df.with_columns([
            pl.col("timestamp").dt.hour().alias("hour"),
            pl.col("timestamp").dt.month().alias("month"),
        ])

        rows: list[dict] = []

        for sensor in sensors:
            height = sensor.height
            ws_col = sensor.column_name

            # Skip if column doesn't exist
            if ws_col not in df.columns:
                continue

            # Calculate hourly x monthly statistics for this height
            combined_stats = (
                df_with_time.group_by(["hour", "month"])
                .agg([
                    pl.col(ws_col).mean().alias("mean_speed"),
                    (0.5 * air_density * pl.col(ws_col).pow(3)).mean().alias("mean_power"),
                    pl.col("timestamp").first().alias("timestamp"),
                ])
                .sort(["month", "hour"])
            )

            # Convert to rows
            for row in combined_stats.iter_rows(named=True):
                rows.append({
                    "timestamp": row["timestamp"],
                    "hour": row["hour"],
                    "month": row["month"],
                    "wind_speed": None,
                    "wind_power": None,
                    "height": height,
                    "mean_speed": row["mean_speed"],
                    "mean_power": row["mean_power"],
                    "interpolation_marker": sensor.detect_interpolation_marker(),
                })

        return pl.DataFrame(rows) if rows else self._create_empty_dataframe()

    def _create_empty_result(
        self,
        input: SingleMastAnalysisInput,
        message: str,
    ) -> AnalysisResult[TemporalPatternSchema]:
        """Create an empty result when no data is available.

        Args:
            input: The analysis input
            message: Error or info message

        Returns:
            AnalysisResult with empty data
        """
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=message,
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=TemporalPatternSchema,
            data=self._create_empty_dataframe(),
            metadata=metadata,
        )

    def _create_empty_dataframe(self) -> pl.DataFrame:
        """Create an empty DataFrame with the correct schema.

        Returns:
            Empty DataFrame with TemporalPatternSchema columns
        """
        return pl.DataFrame({
            "timestamp": [],
            "hour": [],
            "month": [],
            "wind_speed": [],
            "wind_power": [],
            "height": [],
            "mean_speed": [],
            "mean_power": [],
            "interpolation_marker": [],
        })

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
