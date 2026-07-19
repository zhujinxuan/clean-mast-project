"""Timeseries validation utilities using dataframely.

ADR-GUARDRAILS: structure-001-subdomain-layout, types-001-type-annotations
Compliance: Subdomain layout ✓ | Repository pattern ✓ | Data validation ✓
Description: Schema validation for timeseries DataFrames against sensor metadata
"""

import hashlib

import dataframely as dy
import polars as pl

from cleanmast.shared.timeseries.sensor_column import SensorColumn


def _hash_sensors(sensors: list[SensorColumn]) -> str:
    """Generate 6-char hash from sensor metadata for unique schema naming."""
    sensor_str = ",".join(sorted(s.column_name for s in sensors))
    return hashlib.sha256(sensor_str.encode()).hexdigest()[:6]


def create_wind_schema(
    sensors: list[SensorColumn],
    mast_name: str | None = None
) -> type[dy.Schema]:
    """Dynamically create a dataframely Schema from sensor metadata."""
    fields: dict[str, dy.Column] = {"timestamp": dy.Datetime(nullable=False)}

    for sensor in sensors:
        fields[sensor.column_name] = dy.Float64(nullable=True)

    # Create unique schema name for debugging
    if mast_name:
        schema_name = f"WindSchema_{mast_name}"
    else:
        token = _hash_sensors(sensors)
        schema_name = f"WindSchema_{token}"

    return type(schema_name, (dy.Schema,), fields)


def validate_timeseries(
    df: pl.DataFrame,
    sensors: list[SensorColumn],
    mast_name: str | None = None
) -> pl.DataFrame:
    """Validate timeseries DataFrame against sensor metadata."""
    schema_class = create_wind_schema(sensors, mast_name)

    # Get columns to validate: timestamp + all sensor columns
    schema_columns = ["timestamp"] + [s.column_name for s in sensors]

    # Select only schema columns for validation (ignore extra columns)
    df_to_validate = df.select(schema_columns)

    # Validate and cast
    validated = schema_class.validate(df_to_validate, cast=True)

    # If there are extra columns not in schema, join them back
    extra_columns = [c for c in df.columns if c not in schema_columns]
    if extra_columns:
        extra_df = df.select(["timestamp"] + extra_columns)
        validated = validated.join(extra_df, on="timestamp", how="left")

    return validated
