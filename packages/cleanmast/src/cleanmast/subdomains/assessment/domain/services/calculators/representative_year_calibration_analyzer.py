"""Representative year calibration analyzer.

Computes climatology mean wind speed, representative year mean wind speed,
and anomaly statistics for each mast configured in representative-year.toml.

ADR-GUARDRAILS: structure-001-subdomain-layout, domain-001-sensor-access,
                data-001-symbol-columns, data-002-functional-style
Compliance: Domain Service ✓ | Sensor-based access ✓ | Functional style ✓
Description: Domain service for representative year calibration summary statistics
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

import polars as pl

from cleanmast.subdomains.configuration.value_objects.representative_year import (
    RepresentativeYearConfiguration,
    load_representative_year_config,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.infrastructure.timeseries_io import (
    load_timeseries,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


def _find_climatology_timerange(
    min_timestamp: datetime, max_timestamp: datetime
) -> tuple[datetime, datetime]:
    """Find the climatology time range using only complete years.

    Mirrors Julia's find_climatology_timerange in RepresentativeYear/Utils.jl.

    1. If min_timestamp - 1 day has the same year, start from the next year.
    2. If max_timestamp + 1 day has the same year, end at the previous year.
    3. Cap the range to at most 30 years (most recent 30 years).

    Args:
        min_timestamp: Minimum timestamp in the dataset.
        max_timestamp: Maximum timestamp in the dataset.

    Returns:
        Tuple of (climatology_start, climatology_end) datetimes.

    Raises:
        ValueError: If no complete years are found in the dataset.
    """
    min_year = min_timestamp.year
    max_year = max_timestamp.year

    start_year = min_year + 1 if (min_timestamp - timedelta(days=1)).year == min_year else min_year
    end_year = max_year - 1 if (max_timestamp + timedelta(days=1)).year == max_year else max_year

    if end_year < start_year:
        raise ValueError(
            f"No complete years found in dataset. Time range: {min_timestamp} to {max_timestamp}"
        )

    year_diff = end_year - start_year + 1
    if year_diff > 30:
        start_year = end_year - 29

    climatology_start = datetime(start_year, 1, 1, 0, 0, 0)
    climatology_end = datetime(end_year, 12, 31, 23, 59, 59)

    return climatology_start, climatology_end


def _find_highest_windspeed_sensor(sensors: list[SensorColumn]) -> SensorColumn:
    """Find the highest wind speed sensor with stat_type 'avg'.

    Args:
        sensors: List of sensor metadata.

    Returns:
        The SensorColumn with the maximum height matching the criteria.

    Raises:
        ValueError: If no WindSpeed sensor with stat_type 'avg' is found.
    """
    candidates = [s for s in sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg"]
    if not candidates:
        raise ValueError("No WindSpeed sensor with stat_type 'avg' found in meso data")
    return max(candidates, key=lambda s: s.height)


def analyze_representative_year_calibration(project_dir: Path) -> pl.DataFrame:
    """Analyze representative year calibration for all masts in a project.

    Reads the representative-year.toml configuration, loads mesoscale time series
    data for each mast, and computes climatology vs. representative year wind speed
    statistics.

    Args:
        project_dir: Path to the project directory containing representative-year.toml
            and mesoscale data files.

    Returns:
        Polars DataFrame with columns:
        - year_range: Climate period as "YYYYMM~YYYYMM"
        - mast_name: Mast identifier
        - era5_name: Mesoscale source name
        - climatology_mean_ws: Mean wind speed over the climate period
        - rep_year_mean_ws: Mean wind speed over the mast's representative year range
        - anomaly_percent: Absolute percentage anomaly (rounded to 2 decimals)
        - needs_correction: True if anomaly_percent > 2.0

    Raises:
        ValueError: If no WindSpeed avg sensor is found for a mast.
        ValueError: If meso data contains no complete years.
    """
    config_path = project_dir / "representative-year.toml"
    config: RepresentativeYearConfiguration = load_representative_year_config(str(config_path))
    rows: list[dict] = []

    for mast in config.masts:
        meso_source = next(
            (m for m in config.mesos if m.name == mast.meso_model.meso_name),
            None,
        )
        if meso_source is None:
            raise ValueError(
                f"No meso source found with name '{mast.meso_model.meso_name}' for mast '{mast.name}'"
            )

        meso_ts: TimeSeriesData = load_timeseries(meso_source.input, str(project_dir))
        sensor = _find_highest_windspeed_sensor(meso_ts.sensors)
        ws_col = sensor.column_name

        df = meso_ts.df
        min_timestamp = cast(datetime, df["timestamp"].min())
        max_timestamp = cast(datetime, df["timestamp"].max())

        if min_timestamp is None or max_timestamp is None:
            raise ValueError(f"Meso data for mast '{mast.name}' has no timestamp data")

        climatology_start, climatology_end = _find_climatology_timerange(
            min_timestamp, max_timestamp
        )

        climate_df = df.filter(
            (pl.col("timestamp") >= climatology_start)
            & (pl.col("timestamp") <= climatology_end)
        )
        climatology_mean_ws = cast(float, climate_df[ws_col].mean())

        rep_min = (
            mast.time_range.min.replace(tzinfo=None)
            if mast.time_range.min.tzinfo is not None
            else mast.time_range.min
        )
        rep_max = (
            mast.time_range.max.replace(tzinfo=None)
            if mast.time_range.max.tzinfo is not None
            else mast.time_range.max
        )

        rep_df = df.filter(
            (pl.col("timestamp") >= rep_min)
            & (pl.col("timestamp") <= rep_max)
        )
        rep_year_mean_ws = cast(float, rep_df[ws_col].mean())

        if climatology_mean_ws is None or climatology_mean_ws == 0:
            raise ValueError(
                f"Climatology mean wind speed is zero or undefined for mast '{mast.name}'"
            )

        anomaly_percent = (
            abs(climatology_mean_ws - rep_year_mean_ws) / climatology_mean_ws * 100.0
        )
        anomaly_percent = round(anomaly_percent, 2)
        needs_correction = anomaly_percent > 2.0

        year_range = (
            f"{rep_min.year}{rep_min.month:02d}"
            f"~{rep_max.year}{rep_max.month:02d}"
        )

        rows.append({
            "year_range": year_range,
            "mast_name": mast.name,
            "era5_name": meso_source.name,
            "climatology_mean_ws": climatology_mean_ws,
            "rep_year_mean_ws": rep_year_mean_ws,
            "anomaly_percent": anomaly_percent,
            "needs_correction": needs_correction,
        })

    return pl.DataFrame(rows)
