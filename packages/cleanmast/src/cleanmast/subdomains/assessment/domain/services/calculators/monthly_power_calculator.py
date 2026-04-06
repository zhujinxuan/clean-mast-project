"""Monthly wind power calculator service.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Domain service for calculating monthly wind power density from time series data
"""

from datetime import datetime

import polars as pl

from cleanmast.subdomains.assessment.domain.value_objects.air_density import (
    calculate_air_density,
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
from cleanmast.subdomains.assessment.domain.value_objects.schemas import (
    MonthlyWindPowerSchema,
)
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

        ws_avg_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]

        # Calculate monthly power density
        result_df = self._process_monthly_wind_power_data(df, ws_avg_sensors, air_density)

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
        sensors: list[SensorColumn],
        air_density: float,
    ) -> pl.DataFrame:
        """Process data into monthly wind power density statistics (long format).

        For each height, calculate monthly wind power density using 0.5 * ρ * WS³.

        Args:
            df: DataFrame with timestamp and WS_* columns
            sensors: List of SensorColumn objects for wind speed sensors
            air_density: Air density in kg/m³

        Returns:
            DataFrame with columns: month, height, interpolation_marker,
            wind_power_density, air_density_used
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
