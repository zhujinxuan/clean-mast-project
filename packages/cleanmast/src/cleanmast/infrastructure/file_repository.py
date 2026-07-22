"""File-based time series repository — infrastructure realization of TimeSeriesRepository.

Lives in ``cleanmast.infrastructure``: this is the only module that knows how
TimeSeriesSource paths map to files on disk. Constructed once by
``cleanmast.bootstrap`` (the composition root) and injected into application
usecases as the ``TimeSeriesRepository`` protocol.

Dispatches on TimeSeriesSource.data suffix: .parquet → embedded metadata;
.csv → sidecar metadata file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import polars as pl
import pyarrow.parquet as pq
import tomli
import tomli_w
import yaml

from cleanmast.shared.timeseries.io.validation import validate_timeseries
from cleanmast.shared.timeseries.sensor_column import SensorColumn
from cleanmast.shared.timeseries.time_series_data import TimeSeriesData
from cleanmast.shared.timeseries.time_series_source import (
    TimeSeriesSource,
)

# ---------------------------------------------------------------------------
# Private helpers — single copy, merged from the two prior implementations.
# Audit confirmed zero behavioral drift between them.
# ---------------------------------------------------------------------------


def _detect_format(path: Path) -> Literal["csv", "parquet"]:
    """Detect file format from extension (case-insensitive)."""
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return "parquet"
    elif suffix in (".csv",):
        return "csv"
    else:
        raise ValueError(
            f"Unsupported data file format: {suffix}. Expected .csv or .parquet"
        )


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
        with open(filepath, encoding="utf-8") as f:
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
    """
    pf = pq.ParquetFile(filepath)
    file_meta = pf.metadata.metadata  # Dict[bytes, bytes]

    if b"cleanmast_sensors" not in file_meta:
        raise ValueError(f"No sensor metadata in {filepath}")

    sensors_json = json.loads(file_meta[b"cleanmast_sensors"].decode("utf-8"))

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
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)

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

    table = df.to_arrow()

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

    filepath.parent.mkdir(parents=True, exist_ok=True)

    if suffix in (".yaml", ".yml"):
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(sensors_data, f, default_flow_style=False, sort_keys=False)
    elif suffix == ".toml":
        with open(filepath, "wb") as f:
            tomli_w.dump(sensors_data, f)
    else:
        raise ValueError(f"Unsupported sensor file format: {suffix}")


# ---------------------------------------------------------------------------
# Format-specific load/save — module-level (backward-compatible public API)
# ---------------------------------------------------------------------------

def load_timeseries_parquet(
    source: TimeSeriesSource, base_dir: str
) -> TimeSeriesData:
    """Load time series data from Parquet file with embedded sensor metadata.

    Reads sensor metadata from the Parquet file's embedded metadata section.
    This is the preferred format for CleanMast as it preserves type information
    and maintains consistency with the Julia implementation.
    """
    data_path = _resolve_path(source.data, base_dir)

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

    df = pl.read_parquet(data_path)

    if "timestamp" in df.columns:
        if df["timestamp"].dtype != pl.Datetime:
            df = df.with_columns(
                pl.col("timestamp").str.to_datetime().alias("timestamp")
            )

    mast_name = data_path.stem
    df = validate_timeseries(df, sensors, mast_name)

    return TimeSeriesData(df=df, sensors=sensors)


def save_timeseries_parquet(
    source: TimeSeriesSource, base_dir: str, data: TimeSeriesData
) -> None:
    """Save time series data to Parquet with embedded sensor metadata.

    Embeds sensor metadata in the Parquet file's schema metadata for
    interoperability with the Julia implementation.
    """
    data_path = _resolve_path(source.data, base_dir)

    _write_parquet_with_metadata(data.df, data_path, data.sensors)

    # Optionally save sensors file if specified (for backward compatibility)
    if source.sensors:
        sensors_path = _resolve_path(source.sensors, base_dir)
        _save_sensors_to_file(sensors_path, data.sensors)


# ---------------------------------------------------------------------------
# FileTimeSeriesRepository — the realization
# ---------------------------------------------------------------------------

class FileTimeSeriesRepository:
    """Repository implementation using file storage with automatic format detection.

    Dispatches on TimeSeriesSource.data extension:
    - .parquet → embedded sensor metadata (file-level JSON)
    - .csv → sidecar metadata file (YAML/TOML)

    Features:
        - Automatic format detection (.csv vs .parquet)
        - Embedded sensor metadata in Parquet files
        - Julia-compatible camelCase serialization
        - Schema validation on load

    Example:
        repo = FileTimeSeriesRepository()
        data = repo.load(source, base_dir)
        repo.save(source, base_dir, data)
    """

    def load(self, source: TimeSeriesSource, base_dir: str) -> TimeSeriesData:
        """Load time series data from CSV or Parquet with sensor metadata."""
        data_path = _resolve_path(source.data, base_dir)
        fmt = _detect_format(data_path)

        if fmt == "parquet":
            return self._load_parquet(source, base_dir)
        else:
            return self._load_csv(source, base_dir)

    def save(
        self, source: TimeSeriesSource, base_dir: str, data: TimeSeriesData
    ) -> None:
        """Save time series data to CSV or Parquet with sensor metadata."""
        data_path = _resolve_path(source.data, base_dir)
        fmt = _detect_format(data_path)

        if fmt == "parquet":
            self._save_parquet(source, base_dir, data)
        else:
            self._save_csv(source, base_dir, data)

    def _load_parquet(
        self, source: TimeSeriesSource, base_dir: str
    ) -> TimeSeriesData:
        data_path = _resolve_path(source.data, base_dir)

        if not data_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")

        try:
            sensors = _extract_sensors_from_parquet(data_path)
        except ValueError as e:
            raise ValueError(
                f"No sensor metadata in Parquet file: {data_path}. "
                f"Parquet files must have embedded column-level metadata. "
                f"Original error: {e}"
            ) from e

        df = pl.read_parquet(data_path)

        if "timestamp" in df.columns:
            if df["timestamp"].dtype != pl.Datetime:
                df = df.with_columns(
                    pl.col("timestamp").str.to_datetime().alias("timestamp")
                )

        mast_name = data_path.stem
        df = validate_timeseries(df, sensors, mast_name)

        return TimeSeriesData(df=df, sensors=sensors)

    def _save_parquet(
        self, source: TimeSeriesSource, base_dir: str, data: TimeSeriesData
    ) -> None:
        data_path = _resolve_path(source.data, base_dir)

        _write_parquet_with_metadata(data.df, data_path, data.sensors)

        if source.sensors:
            sensors_path = _resolve_path(source.sensors, base_dir)
            _save_sensors_to_file(sensors_path, data.sensors)

    def _load_csv(
        self, source: TimeSeriesSource, base_dir: str
    ) -> TimeSeriesData:
        data_path = _resolve_path(source.data, base_dir)

        # Pinned quirk: this branch is unreachable because TimeSeriesSource's
        # validator catches the null-sensors case first. Preserved as-is.
        if source.sensors is None:
            raise FileNotFoundError(
                "Sensors file not specified. CSV format requires sensors file."
            )
        sensors_path = _resolve_path(source.sensors, base_dir)

        if not data_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")
        if not sensors_path.exists():
            raise FileNotFoundError(f"Sensors file not found: {sensors_path}")

        sensors = _load_sensors_from_file(sensors_path)

        df = pl.read_csv(
            data_path,
            try_parse_dates=True,
            null_values=["", "NA", "NaN", "null"],
        )

        if "timestamp" in df.columns:
            if df["timestamp"].dtype != pl.Datetime:
                df = df.with_columns(
                    pl.col("timestamp").str.to_datetime().alias("timestamp")
                )

        mast_name = data_path.stem
        df = validate_timeseries(df, sensors, mast_name)

        return TimeSeriesData(df=df, sensors=sensors)

    def _save_csv(
        self, source: TimeSeriesSource, base_dir: str, data: TimeSeriesData
    ) -> None:
        data_path = _resolve_path(source.data, base_dir)

        if source.sensors is None:
            raise FileNotFoundError(
                "Sensors file not specified. CSV format requires sensors file."
            )
        sensors_path = _resolve_path(source.sensors, base_dir)

        data_path.parent.mkdir(parents=True, exist_ok=True)

        data.df.write_csv(data_path)

        _save_sensors_to_file(sensors_path, data.sensors)

