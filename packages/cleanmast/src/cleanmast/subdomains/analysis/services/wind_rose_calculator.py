"""Wind rose calculator service.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓
Description: Domain service for calculating wind rose statistics from time series data
"""

from datetime import datetime
from typing import Any

import polars as pl

from cleanmast.subdomains.analysis.value_objects.air_density import calculate_air_density
from cleanmast.subdomains.analysis.value_objects.analysis_input import SingleMastAnalysisInput
from cleanmast.subdomains.analysis.value_objects.analysis_metadata import AnalysisMetadata
from cleanmast.subdomains.analysis.value_objects.analysis_result import AnalysisResult
from cleanmast.subdomains.analysis.value_objects.column_utils import detect_interpolation_marker
from cleanmast.subdomains.analysis.value_objects.schemas import WindRoseSchema
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
        ws_sensors = [s for s in sensors if s.sensor_type == "WindSpeed"]
        wd_sensors = [s for s in sensors if s.sensor_type == "WindDirection"]

        # Create mapping from height to WD column
        wd_col_map: dict[float, str] = {s.height: s.column_name for s in wd_sensors}

        # Build heights_info list
        heights_info: list[tuple[float, str]] = [
            (s.height, s.column_name) for s in ws_sensors
        ]

        # Calculate wind rose data
        result_df = self._process_wind_rose_data(df, heights_info, wd_col_map, air_density)

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
        heights_info: list[tuple[float, str]],
        wd_col_map: dict[float, str],
        air_density: float,
    ) -> pl.DataFrame:
        """Process data into wind rose statistics (long format).

        For each height, calculate sector frequencies and power densities.

        Args:
            df: DataFrame with timestamp, WS_*, and WD_* columns
            heights_info: List of (height, ws_column_name) tuples
            wd_col_map: Dict mapping height to WD column name
            air_density: Air density in kg/m³

        Returns:
            DataFrame with columns: sector, sector_name, height, interpolation_marker,
            frequency, wind_power_density
        """
        rows: list[dict] = []

        for height, ws_col in heights_info:
            # Get corresponding WD column for this height
            wd_col = wd_col_map.get(height)
            if wd_col is None:
                continue

            # Get interpolation marker from column name
            marker = detect_interpolation_marker(ws_col)

            # Filter out null wind direction values before processing
            valid_df = df.filter(pl.col(wd_col).is_not_null())

            # Calculate sector (0-15) from wind direction
            df_with_sector = valid_df.with_columns(
                ((pl.col(wd_col) / 22.5).round().cast(pl.Int64) % 16).alias("sector")
            )

            # Group by sector and calculate statistics
            sector_stats = df_with_sector.group_by("sector").agg([
                pl.len().alias("count"),
                (0.5 * air_density * pl.col(ws_col) ** 3).mean().alias("wind_power_density"),
            ]).sort("sector")

            # Calculate frequency based on valid (non-null) rows
            valid_row_count = len(valid_df)

            # Convert to rows with frequency and sector names
            for row in sector_stats.iter_rows(named=True):
                sector = int(row["sector"])
                frequency = row["count"] / valid_row_count
                power_density = row["wind_power_density"]

                rows.append({
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
