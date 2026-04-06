"""Tests for timeseries I/O functions."""

from datetime import datetime
from pathlib import Path

import polars as pl
import pytest
import yaml
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.infrastructure.timeseries_io import (
    load_timeseries,
    save_timeseries,
)
from cleanmast.subdomains.dataingestion.value_objects import SensorColumn
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)


class TestLoadTimeseries:
    """Tests for load_timeseries function."""

    def test_load_from_yaml_sensors(self, tmp_path: Path):
        """Test loading timeseries with YAML sensor metadata."""
        # Create test CSV
        csv_content = """timestamp,WindSpeed_100m_avg [m/s],WindDirection_100m_avg [deg]
2024-01-01 00:00:00,5.5,180.0
2024-01-01 00:10:00,6.0,185.0
2024-01-01 00:20:00,5.8,182.0
"""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text(csv_content)

        # Create test YAML sensors file (camelCase like Julia output)
        sensors_data = {
            "sensors": [
                {
                    "columnName": "WindSpeed_100m_avg [m/s]",
                    "sensorType": "WindSpeed",
                    "sensorDirection": "",
                    "height": 100.0,
                    "statType": "avg",
                    "unit": "m/s",
                },
                {
                    "columnName": "WindDirection_100m_avg [deg]",
                    "sensorType": "WindDirection",
                    "sensorDirection": "",
                    "height": 100.0,
                    "statType": "avg",
                    "unit": "deg",
                },
            ]
        }
        sensors_path = tmp_path / "sensors.yaml"
        with open(sensors_path, "w") as f:
            yaml.dump(sensors_data, f)

        # Load timeseries
        source = TimeSeriesSource(
            data=str(csv_path),
            sensors=str(sensors_path),
        )
        ts_data = load_timeseries(source, str(tmp_path))

        # Verify
        assert ts_data.df.shape == (3, 3)
        assert len(ts_data.sensors) == 2
        assert ts_data.sensors[0].sensor_type == "WindSpeed"
        assert ts_data.sensors[1].sensor_type == "WindDirection"

    def test_load_with_relative_paths(self, tmp_path: Path):
        """Test loading with paths relative to base_dir."""
        # Create subdirectory
        data_dir = tmp_path / "reconstruct-meso"
        data_dir.mkdir()

        # Create test files
        csv_content = "timestamp,WindSpeed_80m_avg [m/s]\n2024-01-01 00:00:00,5.5\n"
        (data_dir / "M01.csv").write_text(csv_content)

        sensors_data = {
            "sensors": [
                {
                    "columnName": "WindSpeed_80m_avg [m/s]",
                    "sensorType": "WindSpeed",
                    "sensorDirection": "",
                    "height": 80.0,
                    "statType": "avg",
                    "unit": "m/s",
                }
            ]
        }
        with open(data_dir / "M01.sensors.yaml", "w") as f:
            yaml.dump(sensors_data, f)

        # Load with relative paths
        source = TimeSeriesSource(
            data="./reconstruct-meso/M01.csv",
            sensors="./reconstruct-meso/M01.sensors.yaml",
        )
        ts_data = load_timeseries(source, str(tmp_path))

        assert ts_data.df.shape == (1, 2)
        assert ts_data.sensors[0].height == 80.0

    def test_load_from_toml_sensors(self, tmp_path: Path):
        """Test loading timeseries with TOML sensor metadata."""
        # Create test CSV
        csv_content = "timestamp,Temperature_10m_avg [C]\n2024-01-01 00:00:00,15.5\n"
        csv_path = tmp_path / "data.csv"
        csv_path.write_text(csv_content)

        # Create test TOML sensors file
        toml_content = """[[sensors]]
columnName = "Temperature_10m_avg [C]"
sensorType = "Temperature"
sensorDirection = ""
height = 10.0
statType = "avg"
unit = "C"
"""
        sensors_path = tmp_path / "sensors.toml"
        sensors_path.write_text(toml_content)

        # Load timeseries
        source = TimeSeriesSource(
            data=str(csv_path),
            sensors=str(sensors_path),
        )
        ts_data = load_timeseries(source, str(tmp_path))

        assert len(ts_data.sensors) == 1
        assert ts_data.sensors[0].sensor_type == "Temperature"

    def test_load_with_missing_values(self, tmp_path: Path):
        """Test loading CSV with missing values."""
        csv_content = """timestamp,WindSpeed_100m_avg [m/s]
2024-01-01 00:00:00,5.5
2024-01-01 00:10:00,
2024-01-01 00:20:00,6.0
"""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text(csv_content)

        sensors_data = {
            "sensors": [
                {
                    "columnName": "WindSpeed_100m_avg [m/s]",
                    "sensorType": "WindSpeed",
                    "sensorDirection": "",
                    "height": 100.0,
                    "statType": "avg",
                    "unit": "m/s",
                }
            ]
        }
        sensors_path = tmp_path / "sensors.yaml"
        with open(sensors_path, "w") as f:
            yaml.dump(sensors_data, f)

        source = TimeSeriesSource(data=str(csv_path), sensors=str(sensors_path))
        ts_data = load_timeseries(source, str(tmp_path))

        # Check that missing value is preserved
        values = ts_data.df["WindSpeed_100m_avg [m/s]"].to_list()
        assert values[0] == 5.5
        assert values[1] is None  # Polars uses None for missing
        assert values[2] == 6.0

    def test_load_nonexistent_file_raises_error(self, tmp_path: Path):
        """Test that loading nonexistent file raises error."""
        source = TimeSeriesSource(
            data="./nonexistent.csv",
            sensors="./nonexistent.yaml",
        )

        with pytest.raises(FileNotFoundError):
            load_timeseries(source, str(tmp_path))


class TestSaveTimeseries:
    """Tests for save_timeseries function."""

    def test_save_to_yaml(self, tmp_path: Path):
        """Test saving timeseries with YAML sensor metadata."""
        # Create test data
        df = pl.DataFrame(
            {
                "timestamp": [
                    datetime(2024, 1, 1, 0, 0),
                    datetime(2024, 1, 1, 0, 10),
                ],
                "WindSpeed_100m_avg [m/s]": [5.5, 6.0],
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

        # Save
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        source = TimeSeriesSource(
            data="./output/data.csv",
            sensors="./output/sensors.yaml",
        )
        save_timeseries(source, str(tmp_path), ts_data)

        # Verify files exist
        assert (tmp_path / "output" / "data.csv").exists()
        assert (tmp_path / "output" / "sensors.yaml").exists()

        # Verify CSV content
        loaded_df = pl.read_csv(tmp_path / "output" / "data.csv")
        assert loaded_df.shape == (2, 2)

        # Verify YAML content
        with open(tmp_path / "output" / "sensors.yaml") as f:
            loaded_sensors = yaml.safe_load(f)
        assert len(loaded_sensors["sensors"]) == 1
        assert loaded_sensors["sensors"][0]["columnName"] == "WindSpeed_100m_avg [m/s]"

    def test_save_creates_directories(self, tmp_path: Path):
        """Test that save creates parent directories if needed."""
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2024, 1, 1)],
                "WindSpeed_80m_avg [m/s]": [5.0],
            }
        )
        sensors = [
            SensorColumn(
                column_name="WindSpeed_80m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            )
        ]
        ts_data = TimeSeriesData(df=df, sensors=sensors)

        # Save to nested directory that doesn't exist
        source = TimeSeriesSource(
            data="./deep/nested/dir/data.csv",
            sensors="./deep/nested/dir/sensors.yaml",
        )
        save_timeseries(source, str(tmp_path), ts_data)

        assert (tmp_path / "deep" / "nested" / "dir" / "data.csv").exists()
        assert (tmp_path / "deep" / "nested" / "dir" / "sensors.yaml").exists()

    def test_roundtrip_load_save_load(self, tmp_path: Path):
        """Test that save then load preserves data."""
        # Create original data
        df = pl.DataFrame(
            {
                "timestamp": [
                    datetime(2024, 1, 1, 0, 0),
                    datetime(2024, 1, 1, 0, 10),
                    datetime(2024, 1, 1, 0, 20),
                ],
                "WindSpeed_100m_avg [m/s]": [5.5, 6.0, 5.8],
                "WindDirection_100m_avg [deg]": [180.0, 185.0, 182.0],
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
        original = TimeSeriesData(df=df, sensors=sensors)

        # Save
        source = TimeSeriesSource(data="./data.csv", sensors="./sensors.yaml")
        save_timeseries(source, str(tmp_path), original)

        # Load back
        loaded = load_timeseries(source, str(tmp_path))

        # Verify data matches
        assert loaded.df.shape == original.df.shape
        assert len(loaded.sensors) == len(original.sensors)
        assert loaded.sensors[0].sensor_type == original.sensors[0].sensor_type
        assert loaded.sensors[0].height == original.sensors[0].height

        # Verify values
        orig_ws = original.df["WindSpeed_100m_avg [m/s]"].to_list()
        load_ws = loaded.df["WindSpeed_100m_avg [m/s]"].to_list()
        assert orig_ws == load_ws
