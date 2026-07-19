"""Tests for timeseries validation module.

Tests the dataframely-based validation of timeseries DataFrames against
sensor metadata.
"""

from datetime import datetime

import polars as pl
import pytest
from cleanmast.shared.timeseries import SensorColumn
from cleanmast.shared.timeseries.io.validation import (
    _hash_sensors,
    create_wind_schema,
    validate_timeseries,
)


class TestHashSensors:
    """Tests for _hash_sensors function."""

    def test_hash_is_deterministic(self):
        """Same sensors should produce same hash."""
        sensors = [
            SensorColumn(
                column_name="WS_80m",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_80m",
                sensor_type="WindDirection",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        hash1 = _hash_sensors(sensors)
        hash2 = _hash_sensors(sensors)

        assert hash1 == hash2
        assert len(hash1) == 6

    def test_hash_changes_with_different_sensors(self):
        """Different sensors should produce different hashes."""
        sensors1 = [
            SensorColumn(
                column_name="WS_80m",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]
        sensors2 = [
            SensorColumn(
                column_name="WS_100m",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        hash1 = _hash_sensors(sensors1)
        hash2 = _hash_sensors(sensors2)

        assert hash1 != hash2


class TestCreateWindSchema:
    """Tests for create_wind_schema function."""

    def test_schema_has_timestamp_column(self):
        """Schema should have required timestamp column."""
        sensors = []
        schema_class = create_wind_schema(sensors, "TGL1")

        # Check by validating a DataFrame with timestamp
        df = pl.DataFrame({"timestamp": [datetime(2023, 1, 1)]})
        result = schema_class.validate(df, cast=True)
        assert "timestamp" in result.columns

    def test_schema_has_sensor_columns(self):
        """Schema should include all sensor columns."""
        sensors = [
            SensorColumn(
                column_name="WS_80m",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_80m",
                sensor_type="WindDirection",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="deg",
            ),
        ]
        schema_class = create_wind_schema(sensors, "TGL1")

        # Check by validating a DataFrame with all columns
        df = pl.DataFrame({
            "timestamp": [datetime(2023, 1, 1)],
            "WS_80m": [10.0],
            "WD_80m": [180.0],
        })
        result = schema_class.validate(df, cast=True)
        assert "WS_80m" in result.columns
        assert "WD_80m" in result.columns

    def test_schema_name_with_mast_name(self):
        """Schema name should include mast name when provided."""
        sensors = []
        schema_class = create_wind_schema(sensors, "TGL1")

        assert schema_class.__name__ == "WindSchema_TGL1"

    def test_schema_name_without_mast_name(self):
        """Schema name should use hash when mast name not provided."""
        sensors = [
            SensorColumn(
                column_name="WS_80m",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]
        schema_class = create_wind_schema(sensors)

        assert schema_class.__name__.startswith("WindSchema_")
        assert len(schema_class.__name__) == len("WindSchema_") + 6  # + hash


class TestValidateTimeseries:
    """Tests for validate_timeseries function."""

    def test_valid_data_passes(self):
        """Valid data should pass validation."""
        df = pl.DataFrame({
            "timestamp": [datetime(2023, 1, 1), datetime(2023, 1, 2)],
            "WS_80m": [10.0, 15.0],
            "WD_80m": [180.0, 200.0],
        })
        sensors = [
            SensorColumn(
                column_name="WS_80m",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_80m",
                sensor_type="WindDirection",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        result = validate_timeseries(df, sensors, "TGL1")

        assert result is not None
        assert "timestamp" in result.columns
        assert "WS_80m" in result.columns
        assert "WD_80m" in result.columns

    def test_missing_timestamp_raises(self):
        """Data without timestamp should raise error."""
        df = pl.DataFrame({
            "WS_80m": [10.0, 15.0],
        })
        sensors = [
            SensorColumn(
                column_name="WS_80m",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        with pytest.raises(Exception):  # dataframely.ValidationError
            validate_timeseries(df, sensors)

    def test_missing_sensor_column_raises(self):
        """Data missing a sensor column should raise error."""
        df = pl.DataFrame({
            "timestamp": [datetime(2023, 1, 1)],
            "WS_80m": [10.0],
            # Missing WD_80m
        })
        sensors = [
            SensorColumn(
                column_name="WS_80m",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_80m",
                sensor_type="WindDirection",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        with pytest.raises(Exception):  # dataframely.ValidationError
            validate_timeseries(df, sensors)

    def test_nullable_sensor_data_passes(self):
        """Sensor data with nulls should pass (nullable=True)."""
        df = pl.DataFrame({
            "timestamp": [datetime(2023, 1, 1), datetime(2023, 1, 2)],
            "WS_80m": [10.0, None],  # Null is allowed
        })
        sensors = [
            SensorColumn(
                column_name="WS_80m",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        result = validate_timeseries(df, sensors)

        assert result is not None
        assert result["WS_80m"][1] is None

    def test_non_nullable_timestamp_raises(self):
        """Null timestamp should raise error (nullable=False)."""
        df = pl.DataFrame({
            "timestamp": [datetime(2023, 1, 1), None],  # Null not allowed
            "WS_80m": [10.0, 15.0],
        })
        sensors = [
            SensorColumn(
                column_name="WS_80m",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

        with pytest.raises(Exception):  # dataframely.ValidationError
            validate_timeseries(df, sensors)
