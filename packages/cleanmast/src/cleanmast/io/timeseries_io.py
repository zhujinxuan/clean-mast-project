"""Time series I/O operations.

Functions for loading and saving time series data with sensor metadata.
Supports both CSV and Parquet formats with automatic format detection.
"""

from pathlib import Path
from typing import Literal

import json

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import tomli
import tomli_w
import yaml

from ..models.sensor import SensorColumn
from ..models.timeseries import TimeSeriesData, TimeSeriesSource


def _detect_format(path: Path) -> Literal["csv", "parquet"]:
    """Detect file format from extension (case-insensitive)."""
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return "parquet"
    elif suffix in (".csv",):
        return "csv"
    else:
        raise ValueError(f"Unsupported data file format: {suffix}. Expected .csv or .parquet")


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


def _extract_sensors_from_parquet(filepath: Path) -> list[SensorColumn]:
    """Extract sensor metadata from Parquet file metadata.

    Reads the serialized sensors from the Parquet file's metadata section.

    Args:
        filepath: Path to Parquet file with embedded sensor metadata

    Returns:
        List of SensorColumn objects
    """
    # Read Parquet metadata from schema's custom metadata
    table = pq.read_table(filepath)
    metadata = table.schema.metadata

    # Check if our custom metadata exists
    if metadata is None or b"cleanmast_sensors" not in metadata:
        raise ValueError("No sensor metadata found in Parquet file")

    # Extract sensors from metadata (stored as JSON bytes)
    sensors_bytes = metadata[b"cleanmast_sensors"]
    sensors_data = json.loads(sensors_bytes.decode("utf-8"))

    # Convert to SensorColumn objects
    sensors = []
    for sensor_dict in sensors_data.get("sensors", []):
        sensors.append(SensorColumn(**sensor_dict))

    return sensors


def _write_parquet_with_metadata(
    df: pl.DataFrame, filepath: Path, sensors: list[SensorColumn]
) -> None:
    """Write DataFrame to Parquet with embedded sensor metadata.

    Embeds sensor metadata in the Parquet file's schema metadata for
    interoperability with the Julia implementation.

    Args:
        df: Polars DataFrame to write
        filepath: Output Parquet file path
        sensors: List of SensorColumn metadata to embed
    """
    # Ensure parent directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Convert sensors to dicts with camelCase keys
    sensors_data = {
        "sensors": [sensor.model_dump(by_alias=True) for sensor in sensors]
    }

    # Create PyArrow table from Polars DataFrame
    table = df.to_arrow()

    # Update schema metadata with sensor information
    metadata = table.schema.metadata or {}
    metadata[b"cleanmast_sensors"] = json.dumps(sensors_data).encode("utf-8")
    table = table.replace_schema_metadata(metadata)

    # Write Parquet file
    pq.write_table(table, filepath)


def load_timeseries_parquet(source: TimeSeriesSource, base_dir: str) -> TimeSeriesData:
    """Load time series data from Parquet file with embedded sensor metadata.

    Reads sensor metadata from the Parquet file's embedded metadata section.
    This is the preferred format for CleanMast as it preserves type information
    and maintains consistency with the Julia implementation.

    Args:
        source: TimeSeriesSource with paths to data and sensors files
                (sensors path is optional for Parquet - metadata is embedded)
        base_dir: Base directory for resolving relative paths

    Returns:
        TimeSeriesData with DataFrame and sensor metadata

    Raises:
        FileNotFoundError: If data file doesn't exist
        ValueError: If sensor metadata cannot be extracted from Parquet
    """
    data_path = _resolve_path(source.data, base_dir)

    # Check file exists
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    # Try to load sensors from embedded metadata first
    try:
        sensors = _extract_sensors_from_parquet(data_path)
    except Exception:
        # Fall back to sensors file if embedded metadata fails
        sensors_path = _resolve_path(source.sensors, base_dir)
        if not sensors_path.exists():
            raise FileNotFoundError(f"Sensors file not found: {sensors_path}")
        sensors = _load_sensors_from_file(sensors_path)

    # Load Parquet with polars
    df = pl.read_parquet(data_path)

    # Ensure timestamp column is datetime
    if "timestamp" in df.columns:
        if df["timestamp"].dtype != pl.Datetime:
            df = df.with_columns(
                pl.col("timestamp").str.to_datetime().alias("timestamp")
            )

    return TimeSeriesData(df=df, sensors=sensors)


def save_timeseries_parquet(
    source: TimeSeriesSource, base_dir: str, data: TimeSeriesData
) -> None:
    """Save time series data to Parquet with embedded sensor metadata.

    Embeds sensor metadata in the Parquet file's schema metadata for
    interoperability with the Julia implementation.

    Args:
        source: TimeSeriesSource with paths to data and sensors files
                (sensors file is optional - metadata is embedded in Parquet)
        base_dir: Base directory for resolving relative paths
        data: TimeSeriesData to save
    """
    data_path = _resolve_path(source.data, base_dir)

    # Write Parquet with embedded metadata
    _write_parquet_with_metadata(data.df, data_path, data.sensors)

    # Optionally save sensors file if specified (for backward compatibility)
    if source.sensors:
        sensors_path = _resolve_path(source.sensors, base_dir)
        _save_sensors_to_file(sensors_path, data.sensors)


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
    """Load time series data from CSV or Parquet with sensor metadata.

    Automatically detects format from file extension (.csv or .parquet).
    For Parquet files, sensor metadata is read from embedded metadata.

    Args:
        source: TimeSeriesSource with paths to data and sensors files
        base_dir: Base directory for resolving relative paths

    Returns:
        TimeSeriesData with DataFrame and sensor metadata

    Raises:
        FileNotFoundError: If data or sensors file doesn't exist
        ValueError: If unsupported file format
    """
    data_path = _resolve_path(source.data, base_dir)

    # Detect format from file extension
    format = _detect_format(data_path)

    if format == "parquet":
        return load_timeseries_parquet(source, base_dir)
    else:
        # CSV format
        sensors_path = _resolve_path(source.sensors, base_dir)

        # Check files exist
        if not data_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")
        if not sensors_path.exists():
            raise FileNotFoundError(f"Sensors file not found: {sensors_path}")

        # Load sensors metadata
        sensors = _load_sensors_from_file(sensors_path)

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
    """Save time series data to CSV or Parquet with sensor metadata.

    Automatically detects format from file extension (.csv or .parquet).
    For Parquet files, sensor metadata is embedded in the file.

    Args:
        source: TimeSeriesSource with paths to data and sensors files
        base_dir: Base directory for resolving relative paths
        data: TimeSeriesData to save
    """
    data_path = _resolve_path(source.data, base_dir)

    # Detect format from file extension
    format = _detect_format(data_path)

    if format == "parquet":
        save_timeseries_parquet(source, base_dir, data)
    else:
        # CSV format
        sensors_path = _resolve_path(source.sensors, base_dir)

        # Ensure parent directories exist
        data_path.parent.mkdir(parents=True, exist_ok=True)

        # Save CSV
        data.df.write_csv(data_path)

        # Save sensors metadata
        _save_sensors_to_file(sensors_path, data.sensors)
