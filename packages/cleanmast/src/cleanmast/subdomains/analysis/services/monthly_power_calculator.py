"""Monthly wind power calculator service.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Domain service for calculating monthly wind power density from time series data
"""

from datetime import datetime

import polars as pl

from cleanmast.subdomains.analysis.value_objects.air_density import calculate_air_density
from cleanmast.subdomains.analysis.value_objects.analysis_input import SingleMastAnalysisInput
from cleanmast.subdomains.analysis.value_objects.analysis_metadata import AnalysisMetadata
from cleanmast.subdomains.analysis.value_objects.analysis_result import AnalysisResult
from cleanmast.subdomains.analysis.value_objects.column_utils import detect_interpolation_marker
from cleanmast.subdomains.analysis.value_objects.schemas import MonthlyWindPowerSchema
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


class MonthlyPowerCalculator:
    """Calculate monthly wind power density from time series data.

    This is a domain service that encapsulates the calculation logic for
    monthly wind power density across different heights.
    """

    def calculate(self, input: SingleMastAnalysisInput) -> AnalysisResult[MonthlyWindPowerSchema]:
        """Calculate monthly wind power density from input data.

        Args:
            input: SingleMastAnalysisInput containing time series data and parameters

        Returns:
            AnalysisResult with MonthlyWindPowerSchema containing monthly power density
        """
        df = input.time_series.df
        sensors = input.time_series.sensors

        # Get air density from parameters or calculate
        air_density = input.parameters.air_density
        if air_density is None:
            air_density = calculate_air_density(input.time_series)

        # Filter sensors to only wind speed sensors
        ws_sensors = [s for s in sensors if s.sensor_type == "WindSpeed"]

        # Build heights_info for processing
        heights_info: list[tuple[float, str]] = [
            (s.height, s.column_name) for s in ws_sensors
        ]

        # Calculate monthly power density
        result_df = self._process_monthly_wind_power_data(df, heights_info, air_density)

        # Create metadata
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=MonthlyWindPowerSchema,
            data=result_df,
            metadata=metadata,
        )

    def _process_monthly_wind_power_data(
        self,
        df: pl.DataFrame,
        heights_info: list[tuple[float, str]],
        air_density: float,
    ) -> pl.DataFrame:
        """Process data into monthly wind power density statistics (long format).

        For each height, calculate monthly wind power density using 0.5 * ρ * WS³.

        Args:
            df: DataFrame with timestamp and WS_* columns
            heights_info: List of (height, column_name) tuples
            air_density: Air density in kg/m³

        Returns:
            DataFrame with columns: month, height, interpolation_marker,
            wind_power_density, air_density_used
        """
        # Add month column
        df = df.with_columns(pl.col("timestamp").dt.month().alias("month"))

        # Process each height
        rows: list[dict] = []
        for height, ws_col in heights_info:
            # Get interpolation marker from column name
            marker = detect_interpolation_marker(ws_col)

            # Calculate monthly power density for this height
            # Power density = 0.5 * ρ * WS³
            monthly_stats = df.group_by("month").agg([
                (0.5 * air_density * pl.col(ws_col) ** 3).mean().alias("wind_power_density"),
            ]).sort("month")

            # Convert to rows
            for row in monthly_stats.iter_rows(named=True):
                rows.append({
                    "month": row["month"],
                    "height": height,
                    "interpolation_marker": marker,
                    "wind_power_density": row["wind_power_density"],
                    "air_density_used": air_density,
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
