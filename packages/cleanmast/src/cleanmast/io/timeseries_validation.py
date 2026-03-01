"""Timeseries validation utilities using dataframely.

This module provides schema validation for timeseries DataFrames against
sensor metadata. It creates dynamic dataframely schemas based on the
SensorColumn definitions to ensure data integrity at load time.

Functions:
    create_wind_schema: Dynamically create a dataframely Schema from sensors
    validate_timeseries: Validate a DataFrame against sensor metadata
"""

import hashlib
from pathlib import Path

import dataframely as dy
import polars as pl

from ..models.sensor import SensorColumn


def _hash_sensors(sensors: list[SensorColumn]) -> str:
    """Generate 6-char hash from sensor metadata for unique schema naming.
    
    Creates a deterministic hash from sorted sensor column names.
    Used when no mast name is provided.
    
    Args:
        sensors: List of SensorColumn metadata
        
    Returns:
        6-character hexadecimal hash string
    """
    sensor_str = ",".join(sorted(s.column_name for s in sensors))
    return hashlib.sha256(sensor_str.encode()).hexdigest()[:6]


def create_wind_schema(
    sensors: list[SensorColumn],
    mast_name: str | None = None
) -> type[dy.Schema]:
    """Dynamically create a dataframely Schema from sensor metadata.
    
    Creates a schema with:
    - timestamp: Required, non-nullable Datetime column
    - Sensor columns: All nullable Float64 (data may be missing)
    
    The schema name includes mast_name or a sensor hash for uniqueness,
    making debugging easier when working with multiple masts.
    
    Args:
        sensors: List of SensorColumn defining expected columns
        mast_name: Optional mast name for schema naming (e.g., "TGL1")
                  If not provided, uses hash of sensor column names
                  
    Returns:
        A dataframely Schema class (subclass of dy.Schema)
        
    Example:
        >>> sensors = [SensorColumn(column_name="WS_80m", ...)]
        >>> WindSchema = create_wind_schema(sensors, "TGL1")
        >>> validated_df = WindSchema.validate(df, cast=True)
    """
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
    """Validate timeseries DataFrame against sensor metadata.
    
    Creates a dynamic schema from the sensor metadata and validates
    the DataFrame against it. Raises if validation fails.
    
    Only validates columns defined in the schema (timestamp + sensors).
    Extra columns in the DataFrame are preserved but not validated.
    
    Args:
        df: Input DataFrame to validate
        sensors: List of SensorColumn defining expected columns
        mast_name: Optional mast name for schema naming
        
    Returns:
        Validated DataFrame (may be cast to match schema types)
        
    Raises:
        dataframely.ValidationError: If DataFrame doesn't match schema
        
    Example:
        >>> df = pl.read_parquet("TGL1.parquet")
        >>> sensors = extract_sensors_from_metadata(...)
        >>> df = validate_timeseries(df, sensors, "TGL1")
    """
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
