"""Time series I/O operations.

Functions for loading and saving time series data with sensor metadata.
"""

from pathlib import Path

import polars as pl
import tomli
import tomli_w
import yaml

from ..models.sensor import SensorColumn
from ..models.timeseries import TimeSeriesData, TimeSeriesSource


def _resolve_path(path: str, base_dir: str) -> Path:
    """Resolve a path relative to base_dir if not absolute."""
    p = Path(path)
    if p.is_absolute():
        return p
    return Path(base_dir) / path


def _load_sensors_from_file(filepath: Path) -> list[SensorColumn]:
    """Load sensor metadata from YAML or TOML file."""
    suffix = filepath.suffix.lower()

    if suffix in (".yaml", ".yml"):
        with open(filepath) as f:
            data = yaml.safe_load(f)
    elif suffix == ".toml":
        with open(filepath, "rb") as f:
            data = tomli.load(f)
    else:
        raise ValueError(f"Unsupported sensor file format: {suffix}")

    sensors = []
    for sensor_dict in data.get("sensors", []):
        sensors.append(SensorColumn(**sensor_dict))

    return sensors


def _save_sensors_to_file(filepath: Path, sensors: list[SensorColumn]) -> None:
    """Save sensor metadata to YAML or TOML file."""
    suffix = filepath.suffix.lower()

    # Convert sensors to dicts with camelCase keys (for Julia compatibility)
    sensors_data = {
        "sensors": [sensor.model_dump(by_alias=True) for sensor in sensors]
    }

    # Ensure parent directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if suffix in (".yaml", ".yml"):
        with open(filepath, "w") as f:
            yaml.dump(sensors_data, f, default_flow_style=False, sort_keys=False)
    elif suffix == ".toml":
        with open(filepath, "wb") as f:
            tomli_w.dump(sensors_data, f)
    else:
        raise ValueError(f"Unsupported sensor file format: {suffix}")


def load_timeseries(source: TimeSeriesSource, base_dir: str) -> TimeSeriesData:
    """Load time series data from CSV and sensor metadata files.

    Args:
        source: TimeSeriesSource with paths to data and sensors files
        base_dir: Base directory for resolving relative paths

    Returns:
        TimeSeriesData with DataFrame and sensor metadata

    Raises:
        FileNotFoundError: If data or sensors file doesn't exist
    """
    data_path = _resolve_path(source.data, base_dir)
    sensors_path = _resolve_path(source.sensors, base_dir)

    # Check files exist
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    if not sensors_path.exists():
        raise FileNotFoundError(f"Sensors file not found: {sensors_path}")

    # Load sensors metadata
    sensors = _load_sensors_from_file(sensors_path)

    # Build column types dict for CSV loading
    # timestamp is parsed as datetime, sensor columns as float (nullable)
    sensor_columns = [s.column_name for s in sensors]

    # Load CSV with polars
    df = pl.read_csv(
        data_path,
        try_parse_dates=True,
        null_values=["", "NA", "NaN", "null"],
    )

    # Ensure timestamp column is datetime
    if "timestamp" in df.columns:
        if df["timestamp"].dtype != pl.Datetime:
            df = df.with_columns(
                pl.col("timestamp").str.to_datetime().alias("timestamp")
            )

    return TimeSeriesData(df=df, sensors=sensors)


def save_timeseries(
    source: TimeSeriesSource, base_dir: str, data: TimeSeriesData
) -> None:
    """Save time series data to CSV and sensor metadata files.

    Args:
        source: TimeSeriesSource with paths to data and sensors files
        base_dir: Base directory for resolving relative paths
        data: TimeSeriesData to save
    """
    data_path = _resolve_path(source.data, base_dir)
    sensors_path = _resolve_path(source.sensors, base_dir)

    # Ensure parent directories exist
    data_path.parent.mkdir(parents=True, exist_ok=True)

    # Save CSV
    data.df.write_csv(data_path)

    # Save sensors metadata
    _save_sensors_to_file(sensors_path, data.sensors)
