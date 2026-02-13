"""Tests for TimeSeriesSource, TimeRange, and TimeSeriesData models."""

from datetime import datetime

import polars as pl
import pytest

from cleanmast.models.sensor import SensorColumn
from cleanmast.models.timeseries import TimeRange, TimeSeriesData, TimeSeriesSource


class TestTimeSeriesSource:
    """Tests for TimeSeriesSource Pydantic model."""

    def test_create_with_relative_paths(self):
        """Test creating TimeSeriesSource with relative paths."""
        source = TimeSeriesSource(
            data="./reconstruct-meso/M01.csv",
            sensors="./reconstruct-meso/M01.sensors.yaml",
        )

        assert source.data == "./reconstruct-meso/M01.csv"
        assert source.sensors == "./reconstruct-meso/M01.sensors.yaml"

    def test_create_from_dict(self):
        """Test creating TimeSeriesSource from dict (like TOML input)."""
        data = {
            "data": "./clean/M01.csv",
            "sensors": "./clean/M01.sensors.toml",
        }

        source = TimeSeriesSource(**data)

        assert source.data == "./clean/M01.csv"
        assert source.sensors == "./clean/M01.sensors.toml"

    def test_serialize_to_dict(self):
        """Test serialization to dict."""
        source = TimeSeriesSource(
            data="./output/data.csv",
            sensors="./output/sensors.yaml",
        )

        data = source.model_dump()

        assert data["data"] == "./output/data.csv"
        assert data["sensors"] == "./output/sensors.yaml"


class TestTimeRange:
    """Tests for TimeRange Pydantic model."""

    def test_create_with_datetime_objects(self):
        """Test creating TimeRange with datetime objects."""
        time_range = TimeRange(
            min=datetime(2024, 1, 1, 0, 0, 0),
            max=datetime(2024, 12, 31, 23, 59, 59),
        )

        assert time_range.min == datetime(2024, 1, 1, 0, 0, 0)
        assert time_range.max == datetime(2024, 12, 31, 23, 59, 59)

    def test_create_from_iso_string(self):
        """Test creating TimeRange from ISO format strings (like TOML input)."""
        data = {
            "min": "2024-01-01T00:00:00",
            "max": "2024-12-31T23:59:59",
        }

        time_range = TimeRange(**data)

        assert time_range.min.year == 2024
        assert time_range.min.month == 1
        assert time_range.max.month == 12

    def test_serialize_time_range(self):
        """Test serialization of TimeRange."""
        time_range = TimeRange(
            min=datetime(2024, 1, 1),
            max=datetime(2024, 12, 31),
        )

        data = time_range.model_dump()

        assert "min" in data
        assert "max" in data


class TestTimeSeriesData:
    """Tests for TimeSeriesData class."""

    def test_create_with_dataframe_and_sensors(self):
        """Test creating TimeSeriesData with DataFrame and sensor list."""
        df = pl.DataFrame(
            {
                "timestamp": [
                    datetime(2024, 1, 1, 0, 0),
                    datetime(2024, 1, 1, 0, 10),
                ],
                "WindSpeed_100m_avg [m/s]": [5.5, 6.0],
                "WindDirection_100m_avg [deg]": [180.0, 185.0],
            }
        )

        sensors = [
            SensorColumn(
                column_name="WindSpeed_100m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WindDirection_100m_avg [deg]",
                sensor_type="WindDirection",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        ts_data = TimeSeriesData(df=df, sensors=sensors)

        assert ts_data.df.shape == (2, 3)
        assert len(ts_data.sensors) == 2
        assert ts_data.sensors[0].sensor_type == "WindSpeed"

    def test_access_dataframe(self):
        """Test accessing the DataFrame."""
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2024, 1, 1)],
                "WindSpeed_100m_avg [m/s]": [5.5],
            }
        )
        sensors = [
            SensorColumn(
                column_name="WindSpeed_100m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            )
        ]

        ts_data = TimeSeriesData(df=df, sensors=sensors)

        # Access column by name
        wind_speeds = ts_data.df["WindSpeed_100m_avg [m/s]"].to_list()
        assert wind_speeds == [5.5]

    def test_filter_sensors_by_type(self):
        """Test filtering sensors by type."""
        df = pl.DataFrame({"timestamp": [datetime(2024, 1, 1)]})
        sensors = [
            SensorColumn(
                column_name="WindSpeed_100m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WindDirection_100m_avg [deg]",
                sensor_type="WindDirection",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="deg",
            ),
            SensorColumn(
                column_name="Temperature_10m_avg [C]",
                sensor_type="Temperature",
                sensor_direction="",
                height=10.0,
                stat_type="avg",
                unit="C",
            ),
        ]

        ts_data = TimeSeriesData(df=df, sensors=sensors)

        wind_speed_sensors = [
            s for s in ts_data.sensors if s.sensor_type == "WindSpeed"
        ]
        assert len(wind_speed_sensors) == 1
        assert wind_speed_sensors[0].height == 100.0

    def test_get_sensor_heights(self):
        """Test getting unique sensor heights."""
        df = pl.DataFrame({"timestamp": [datetime(2024, 1, 1)]})
        sensors = [
            SensorColumn(
                column_name="WindSpeed_80m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WindSpeed_100m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WindDirection_100m_avg [deg]",
                sensor_type="WindDirection",
                sensor_direction="",
                height=100.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        ts_data = TimeSeriesData(df=df, sensors=sensors)

        # Get unique heights for WindSpeed sensors
        wind_speed_heights = sorted(
            set(s.height for s in ts_data.sensors if s.sensor_type == "WindSpeed")
        )
        assert wind_speed_heights == [80.0, 100.0]
