"""Parquet-based time series repository implementation.

ADR-GUARDRAILS: structure-001-subdomain-layout, persistence-001-parquet-storage
Compliance: Subdomain layout ✓ | Repository Pattern ✓ | Julia-compatible metadata ✓
Description: Repository implementation using Parquet format with embedded sensor metadata
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

from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import TimeSeriesSource
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn


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
    """Extract sensor metadata from Parquet file-level metadata.

    Reads sensor metadata from file-level metadata in Parquet files.
    Uses JSON format under key "cleanmast_sensors".

    Args:
        filepath: Path to Parquet file with embedded sensor metadata

    Returns:
        List of SensorColumn objects

    Raises:
        ValueError: If no sensor metadata found in file-level metadata
    """
    pf = pq.ParquetFile(filepath)
    file_meta = pf.metadata.metadata  # Dict[bytes, bytes]

    if b"cleanmast_sensors" not in file_meta:
        raise ValueError(f"No sensor metadata in {filepath}")

    # Parse JSON
    sensors_json = json.loads(file_meta[b"cleanmast_sensors"].decode("utf-8"))

    # Convert to SensorColumn objects
    sensors = []
    for s in sensors_json["sensors"]:
        sensor = SensorColumn(
            column_name=s["columnName"],  # camelCase from JSON
            sensor_type=s["sensorType"],
            sensor_direction=s["sensorDirection"],
            height=s["height"],
            stat_type=s["statType"],
            unit=s["unit"],
        )
        sensors.append(sensor)

    return sensors


def _write_parquet_with_metadata(
    df: pl.DataFrame,
    filepath: Path,
    sensors: list[SensorColumn],
) -> None:
    """Write DataFrame with sensor metadata to Parquet (file-level).

    Embeds sensor metadata at the file level using JSON format.
    Both Python and Julia can read this metadata format.

    Args:
        df: Polars DataFrame to write
        filepath: Output Parquet file path
        sensors: List of SensorColumn metadata to embed
    """
    import json

    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Serialize sensors to JSON (camelCase keys)
    sensors_list = [
        {
            "columnName": s.column_name,
            "sensorType": s.sensor_type,
            "sensorDirection": s.sensor_direction,
            "height": s.height,
            "statType": s.stat_type,
            "unit": s.unit,
        }
        for s in sensors
    ]
    sensors_json = json.dumps({"sensors": sensors_list})

    # Write DataFrame
    table = df.to_arrow()

    # Use ParquetWriter to add file-level metadata
    writer = pq.ParquetWriter(filepath, table.schema)
    writer.add_key_value_metadata({"cleanmast_sensors": sensors_json})
    writer.write_table(table)
    writer.close()


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


class ParquetRepository:
    """Repository implementation using Parquet with embedded sensor metadata.

    This repository implementation uses Parquet files with embedded sensor
    metadata for storage. The metadata is stored at the file level using
    JSON format with camelCase keys for Julia compatibility.

    Features:
        - Automatic format detection (.csv vs .parquet)
        - Embedded sensor metadata in Parquet files
        - Julia-compatible camelCase serialization
        - Schema validation on load

    Example:
        repo = ParquetRepository()
        data = repo.load("./data/mast.parquet")
        repo.save("./output/mast.parquet", data)
    """

    def load(self, source: TimeSeriesSource, base_dir: str) -> TimeSeriesData:
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
            return self._load_parquet(source, base_dir)
        else:
            return self._load_csv(source, base_dir)

    def save(self, source: TimeSeriesSource, base_dir: str, data: TimeSeriesData) -> None:
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
            self._save_parquet(source, base_dir, data)
        else:
            self._save_csv(source, base_dir, data)

    def _load_parquet(self, source: TimeSeriesSource, base_dir: str) -> TimeSeriesData:
        """Load time series data from Parquet file with embedded sensor metadata."""
        data_path = _resolve_path(source.data, base_dir)

        # Check file exists
        if not data_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")

        # Parquet reads sensors ONLY from column metadata (NO external sensor files)
        try:
            sensors = _extract_sensors_from_parquet(data_path)
        except ValueError as e:
            raise ValueError(
                f"No sensor metadata in Parquet file: {data_path}. "
                f"Parquet files must have embedded column-level metadata. "
                f"Original error: {e}"
            ) from e

        # Load Parquet with polars
        df = pl.read_parquet(data_path)

        # Ensure timestamp column is datetime
        if "timestamp" in df.columns:
            if df["timestamp"].dtype != pl.Datetime:
                df = df.with_columns(
                    pl.col("timestamp").str.to_datetime().alias("timestamp")
                )

        # Validate DataFrame against sensor metadata
        from cleanmast.subdomains.dataingestion.repositories.timeseries_validation import validate_timeseries
        mast_name = data_path.stem  # e.g., "TGL1" from "TGL1.parquet"
        df = validate_timeseries(df, sensors, mast_name)

        return TimeSeriesData(df=df, sensors=sensors)

    def _save_parquet(self, source: TimeSeriesSource, base_dir: str, data: TimeSeriesData) -> None:
        """Save time series data to Parquet with embedded sensor metadata."""
        data_path = _resolve_path(source.data, base_dir)

        # Write Parquet with embedded metadata
        _write_parquet_with_metadata(data.df, data_path, data.sensors)

        # Optionally save sensors file if specified (for backward compatibility)
        if source.sensors:
            sensors_path = _resolve_path(source.sensors, base_dir)
            _save_sensors_to_file(sensors_path, data.sensors)

    def _load_csv(self, source: TimeSeriesSource, base_dir: str) -> TimeSeriesData:
        """Load time series data from CSV file with separate sensor metadata."""
        data_path = _resolve_path(source.data, base_dir)

        if source.sensors is None:
            raise FileNotFoundError(
                "Sensors file not specified. CSV format requires sensors file."
            )
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

        # Validate DataFrame against sensor metadata
        from cleanmast.subdomains.dataingestion.repositories.timeseries_validation import validate_timeseries
        mast_name = data_path.stem  # e.g., "TGL1" from "TGL1.csv"
        df = validate_timeseries(df, sensors, mast_name)

        return TimeSeriesData(df=df, sensors=sensors)

    def _save_csv(self, source: TimeSeriesSource, base_dir: str, data: TimeSeriesData) -> None:
        """Save time series data to CSV with separate sensor metadata file."""
        data_path = _resolve_path(source.data, base_dir)

        if source.sensors is None:
            raise FileNotFoundError(
                "Sensors file not specified. CSV format requires sensors file."
            )
        sensors_path = _resolve_path(source.sensors, base_dir)

        # Ensure parent directories exist
        data_path.parent.mkdir(parents=True, exist_ok=True)

        # Save CSV
        data.df.write_csv(data_path)

        # Save sensors metadata
        _save_sensors_to_file(sensors_path, data.sensors)


def load_timeseries(source: TimeSeriesSource, base_dir: str) -> TimeSeriesData:
    """Load time series data from CSV or Parquet with sensor metadata.

    Convenience function using ParquetRepository.
    Maintained for backward compatibility.

    Args:
        source: TimeSeriesSource with paths to data and sensors files
        base_dir: Base directory for resolving relative paths

    Returns:
        TimeSeriesData with DataFrame and sensor metadata
    """
    repo = ParquetRepository()
    return repo.load(source, base_dir)


def save_timeseries(source: TimeSeriesSource, base_dir: str, data: TimeSeriesData) -> None:
    """Save time series data to CSV or Parquet with sensor metadata.

    Convenience function using ParquetRepository.
    Maintained for backward compatibility.

    Args:
        source: TimeSeriesSource with paths to data and sensors files
        base_dir: Base directory for resolving relative paths
        data: TimeSeriesData to save
    """
    repo = ParquetRepository()
    return repo.save(source, base_dir, data)
