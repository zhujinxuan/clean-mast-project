"""Wind rose calculator service.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Domain service for calculating wind rose statistics from time series data
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
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    WindRoseSchema,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn

# Sector definitions for wind rose (16 sectors, 22.5° each)
SECTOR_NAMES = [
    "N", "NNE", "NE", "ENE",
    "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW",
    "W", "WNW", "NW", "NNW",
]


class WindRoseCalculator:
    """Calculate wind rose diagrams from wind direction data.

    This is a domain service that encapsulates the calculation logic for
    wind rose statistics across different heights.
    """

    def calculate(self, input: SingleMastAnalysisInput) -> AnalysisResult[WindRoseSchema]:
        """Calculate wind rose statistics from input data.

        Args:
            input: SingleMastAnalysisInput containing time series data and parameters

        Returns:
            AnalysisResult with WindRoseSchema containing wind rose statistics
        """
        df = input.time_series.df
        sensors = input.time_series.sensors

        # Get air density from parameters or calculate
        air_density = input.parameters.air_density
        if air_density is None:
            air_density = calculate_air_density(input.time_series)

        # Filter sensors to wind speed and wind direction sensors
        ws_avg_sensors = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]
        wd_avg_sensors = [s for s in sensors if s.sensor_type == "WindDirection" and s.stat_type == "avg"]

        wd_col_map: dict[float, str] = {s.height: s.column_name for s in wd_avg_sensors}

        # Calculate wind rose data
        result_df = self._process_wind_rose_data(df, ws_avg_sensors, wd_col_map, air_density)

        # Create metadata
        metadata = AnalysisMetadata(
            mast_name=input.mast_name,
            time_range=self._get_time_range(df),
            created_at=datetime.now(),
        )

        return AnalysisResult.create(
            schema=WindRoseSchema,
            data=result_df,
            metadata=metadata,
        )

    def _process_wind_rose_data(
        self,
        df: pl.DataFrame,
        sensors: list[SensorColumn],
        wd_col_map: dict[float, str],
        air_density: float,
    ) -> pl.DataFrame:
        """Process data into wind rose statistics (long format).

        For each height and month, calculate sector frequencies and power densities.

        Args:
            df: DataFrame with timestamp, WS_*, and WD_* columns
            sensors: List of SensorColumn objects for wind speed sensors
            wd_col_map: Dict mapping height to WD column name
            air_density: Air density in kg/m³

        Returns:
            DataFrame with columns: month, month_name, sector, sector_name, height,
            interpolation_marker, frequency, wind_power_density
        """
        rows: list[dict] = []

        for sensor in sensors:
            height = sensor.height
            ws_col = sensor.column_name

            # Get corresponding WD column for this height
            wd_col = wd_col_map.get(height)
            if wd_col is None:
                continue

            # Get interpolation marker from sensor
            marker = sensor.detect_interpolation_marker()

            # Filter out null wind direction values before processing
            valid_df = df.filter(pl.col(wd_col).is_not_null())

            # Calculate sector (0-15) from wind direction and extract month
            df_with_sector_month = valid_df.with_columns(
                ((pl.col(wd_col) / 22.5).round().cast(pl.Int64) % 16).alias("sector"),
                pl.col("timestamp").dt.month().alias("month"),
            )

            # Group by month and sector, calculate statistics
            month_sector_stats = df_with_sector_month.group_by(["month", "sector"]).agg([
                pl.len().alias("count"),
                (0.5 * air_density * pl.col(ws_col) ** 3).mean().alias("wind_power_density"),
            ]).sort(["month", "sector"])

            # Calculate frequency per month based on valid (non-null) rows per month
            month_counts = df_with_sector_month.group_by("month").agg(
                pl.len().alias("month_total")
            )
            month_sector_stats = month_sector_stats.join(month_counts, on="month")

            # Convert to rows with frequency and sector/month names
            for row in month_sector_stats.iter_rows(named=True):
                month = int(row["month"])
                sector = int(row["sector"])
                frequency = row["count"] / row["month_total"]
                power_density = row["wind_power_density"]

                rows.append({
                    "month": month,
                    "month_name": f"{month}月",
                    "sector": sector,
                    "sector_name": SECTOR_NAMES[sector],
                    "height": height,
                    "interpolation_marker": marker,
                    "frequency": frequency,
                    "wind_power_density": power_density,
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
