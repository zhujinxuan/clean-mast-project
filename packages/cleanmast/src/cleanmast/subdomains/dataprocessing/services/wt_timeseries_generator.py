"""WT TimeSeries generator service.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-t-004-domain-services
Compliance: Subdomain layout ✓ | Domain Service ✓

This module provides the domain service for generating WT TimeSeries CSV files
for Meteodyn WT software. It processes mast data to create standardized
CSV files with wind speed and direction at specified heights.
"""

import logging
from pathlib import Path

import polars as pl

from cleanmast.subdomains.dataingestion.repositories.parquet_repository import ParquetRepository
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
from cleanmast.subdomains.configuration.value_objects.wt_timeseries_config import WtTimeSeriesConfiguration, WtTimeSeriesMast

logger = logging.getLogger(__name__)


def process_wt_timeseries(config: WtTimeSeriesConfiguration, project_dir: Path) -> None:
    """Process all masts in the configuration.

    Iterates through each mast configuration and generates a CSV file with
    wind speed and direction data at the specified heights.

    Args:
        config: WtTimeSeriesConfiguration with mast configurations
        project_dir: Project directory for resolving relative paths

    Example:
        >>> config = load_wt_timeseries_config("config.toml")
        >>> process_wt_timeseries(config, Path("./my-project"))
    """
    for mast in config.masts:
        process_single_mast_csv(mast, project_dir)


def _find_nearest_sensor(
    sensors: list[SensorColumn],
    target_height: float,
    sensor_type: str,
    stat_type: str,
) -> SensorColumn | None:
    """Find the sensor closest to the target height.

    Filters sensors by type and stat_type, then returns the one with
    the smallest absolute height difference from target_height.

    Args:
        sensors: List of available sensors
        target_height: Target height in meters
        sensor_type: Sensor type to filter by (e.g., "WindSpeed")
        stat_type: Statistic type to filter by (e.g., "avg")

    Returns:
        Closest matching sensor or None if no match found
    """
    matching_sensors = [
        s
        for s in sensors
        if s.sensor_type == sensor_type and s.stat_type == stat_type
    ]

    if not matching_sensors:
        return None

    return min(matching_sensors, key=lambda s: abs(s.height - target_height))


def _filter_sensors_by_height(
    csv_heights: list[float],
    sensors: list[SensorColumn],
    mast_name: str,
) -> list[tuple[float, SensorColumn, SensorColumn]]:
    """Filter heights to only those with both WS and WD sensors.

    For each height >= 100m, finds the nearest WindSpeed avg and WindDirection
    avg sensors. Returns only heights where both sensors are available.

    Args:
        csv_heights: List of target heights from configuration
        sensors: List of available sensors
        mast_name: Mast name for logging warnings

    Returns:
        List of tuples (height, ws_sensor, wd_sensor) for valid heights
    """
    valid_heights: list[tuple[float, SensorColumn, SensorColumn]] = []

    for height in csv_heights:
        # Find nearest WS avg sensor
        ws_sensor = _find_nearest_sensor(sensors, height, "WindSpeed", "avg")
        if ws_sensor is None:
            logger.warning(
                f"Mast '{mast_name}': No WindSpeed avg sensor found for height {height}m, "
                "skipping this height"
            )
            continue

        # Find nearest WD avg sensor
        wd_sensor = _find_nearest_sensor(sensors, height, "WindDirection", "avg")
        if wd_sensor is None:
            logger.warning(
                f"Mast '{mast_name}': No WindDirection avg sensor found for height {height}m, "
                "skipping this height"
            )
            continue

        valid_heights.append((height, ws_sensor, wd_sensor))

    return valid_heights


def process_single_mast_csv(mast: WtTimeSeriesMast, project_dir: Path) -> None:
    """Generate single CSV file for a mast with all heights.

    Loads the input parquet file, finds WindSpeed and WindDirection sensors
    for each configured height, and writes a CSV file with timestamp and
    all sensor columns. Uses original parquet column names.

    Args:
        mast: WtTimeSeriesMast configuration
        project_dir: Project directory for output path resolution

    Raises:
        FileNotFoundError: If input parquet file doesn't exist
        ValueError: If no valid heights found for the mast

    Example:
        >>> mast = WtTimeSeriesMast(
        ...     name="TGL1",
        ...     input=TimeSeriesSource(data="./data.parquet"),
        ...     csv_heights=[100.0, 120.0],
        ...     turbulence_heights=[80.0, 100.0],
        ... )
        >>> process_single_mast_csv(mast, Path("./my-project"))
    """
    # 1. Load parquet with sensor metadata
    repo = ParquetRepository()
    ts_data = repo.load(mast.input, str(project_dir))
    df = ts_data.df
    sensors = ts_data.sensors

    # 2. Filter heights to only those with both WS avg and WD avg sensors
    valid_heights = _filter_sensors_by_height(
        mast.csv_heights, sensors, mast.name
    )

    if not valid_heights:
        logger.warning(
            f"Mast '{mast.name}': No valid heights found with both WindSpeed and "
            "WindDirection sensors, skipping CSV generation"
        )
        return

    # 3. Create output DataFrame with timestamp column
    # Select timestamp and all sensor columns we need
    columns_to_select = ["timestamp"]
    for _, ws_sensor, wd_sensor in valid_heights:
        columns_to_select.append(ws_sensor.column_name)
        columns_to_select.append(wd_sensor.column_name)

    # Use Polars expression to select columns
    output_df = df.select([pl.col(col) for col in columns_to_select])

    # 4. Ensure timestamp is in ISO format (it should already be datetime)
    # Cast timestamp to string in ISO format
    output_df = output_df.with_columns(
        pl.col("timestamp").dt.to_string("%Y-%m-%dT%H:%M:%S").alias("timestamp")
    )

    # 5. Create output directory and save CSV
    output_dir = project_dir / "wt-timeseries"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{mast.name}.csv"
    output_df.write_csv(output_path)

    logger.info(
        f"Mast '{mast.name}': Generated CSV with {len(valid_heights)} height(s) "
        f"at {output_path}"
    )
