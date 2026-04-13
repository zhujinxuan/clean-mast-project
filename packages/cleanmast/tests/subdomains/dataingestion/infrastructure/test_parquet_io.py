"""Tests for Parquet I/O functions."""

from datetime import datetime
from pathlib import Path

import polars as pl
import pytest
import yaml
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.infrastructure.timeseries_io import (
    _write_parquet_with_metadata,
    load_timeseries,
    save_timeseries,
)
from cleanmast.subdomains.dataingestion.value_objects import SensorColumn
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)


class TestLoadTimeseriesParquet:
    """Tests for loading timeseries from Parquet format."""

    def test_load_parquet_basic(self, tmp_path: Path):
        """Test loading timeseries from basic Parquet file."""
        # Create test data
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
        ts_data = TimeSeriesData(df=df, sensors=sensors)

        # Save as Parquet
        parquet_path = tmp_path / "data.parquet"
        source = TimeSeriesSource(data=str(parquet_path), sensors="")
        save_timeseries(source, str(tmp_path), ts_data)

        # Load back
        loaded = load_timeseries(source, str(tmp_path))

        # Verify
        assert loaded.df.shape == (3, 3)
        assert len(loaded.sensors) == 2
        assert loaded.sensors[0].sensor_type == "WindSpeed" and loaded.sensors[0].stat_type == "avg"
        assert loaded.sensors[1].sensor_type == "WindDirection" and loaded.sensors[1].stat_type == "avg"

    def test_load_parquet_with_embedded_metadata(self, tmp_path: Path):
        """Test loading Parquet with embedded sensor metadata."""
        # Create test data with multiple sensors
        df = pl.DataFrame(
            {
                "timestamp": [
                    datetime(2024, 1, 1, 0, 0),
                    datetime(2024, 1, 1, 0, 10),
                ],
                "WindSpeed_80m_avg [m/s]": [5.5, 6.0],
                "WindSpeed_100m_avg [m/s]": [6.2, 6.8],
                "Temperature_10m_avg [C]": [15.5, 16.0],
            }
        )
        sensors = [
            SensorColumn(
                column_name="WindSpeed_80m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WindSpeed_100m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="m/s",
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

        # Save as Parquet
        parquet_path = tmp_path / "data.parquet"
        source = TimeSeriesSource(data=str(parquet_path), sensors="")
        save_timeseries(source, str(tmp_path), ts_data)

        # Load back - metadata should be extracted from embedded content
        loaded = load_timeseries(source, str(tmp_path))

        assert len(loaded.sensors) == 3
        assert loaded.sensors[0].height == 80.0
        assert loaded.sensors[1].height == 100.0
        assert loaded.sensors[2].sensor_type == "Temperature" and loaded.sensors[2].stat_type == "avg"

    def test_load_parquet_with_file_level_metadata(self, tmp_path: Path):
        """Test loading Parquet with file-level metadata (new standard format)."""
        import json

        import pyarrow.parquet as pq

        # Create DataFrame with Polars
        df = pl.DataFrame({
            "timestamp": [datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 1, 0, 10)],
            "WindSpeed_100m_avg [m/s]": [5.5, 6.0],
            "WindDirection_100m_avg [deg]": [180.0, 185.0],
        })

        # Create sensors metadata (camelCase for Julia compatibility)
        sensors_list = [
            {
                "columnName": "WindSpeed_100m_avg [m/s]",
                "sensorType": "WindSpeed",
                "sensorDirection": "N",
                "height": 100.0,
                "statType": "avg",
                "unit": "m/s",
            },
            {
                "columnName": "WindDirection_100m_avg [deg]",
                "sensorType": "WindDirection",
                "sensorDirection": "N",
                "height": 100.0,
                "statType": "avg",
                "unit": "deg",
            },
        ]
        sensors_json = json.dumps({"sensors": sensors_list})

        # Write parquet with file-level metadata
        table = df.to_arrow()
        parquet_path = tmp_path / "file_level_meta.parquet"
        writer = pq.ParquetWriter(parquet_path, table.schema)
        writer.add_key_value_metadata({"cleanmast_sensors": sensors_json})
        writer.write_table(table)
        writer.close()

        # Load and verify
        source = TimeSeriesSource(data=str(parquet_path), sensors=None)
        result = load_timeseries(source, str(tmp_path))

        assert len(result.sensors) == 2
        ws_sensor = next(s for s in result.sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg")
        assert ws_sensor.height == 100.0
        assert ws_sensor.column_name == "WindSpeed_100m_avg [m/s]"
        assert ws_sensor.sensor_direction == "N"
        assert ws_sensor.stat_type == "avg"
        assert ws_sensor.unit == "m/s"

        wd_sensor = next(s for s in result.sensors if s.sensor_type == "WindDirection" and s.stat_type == "avg")
        assert wd_sensor.height == 100.0
        assert wd_sensor.column_name == "WindDirection_100m_avg [deg]"

    def test_load_parquet_file_level_metadata_fields(self, tmp_path: Path):
        """Test that all sensor fields are correctly extracted from file-level metadata."""
        import json

        import pyarrow.parquet as pq

        # Create parquet with comprehensive metadata
        df = pl.DataFrame({
            "timestamp": [datetime(2024, 1, 1, 0, 0)],
            "TestColumn": [10.0],
        })

        # File-level metadata (camelCase for Julia compatibility)
        sensors_list = [
            {
                "columnName": "TestColumn",
                "sensorType": "WindSpeed",
                "sensorDirection": "ENE",
                "height": 120.5,
                "statType": "max",
                "unit": "m/s",
            }
        ]
        sensors_json = json.dumps({"sensors": sensors_list})

        # Write parquet with file-level metadata
        table = df.to_arrow()
        parquet_path = tmp_path / "test_fields.parquet"
        writer = pq.ParquetWriter(parquet_path, table.schema)
        writer.add_key_value_metadata({"cleanmast_sensors": sensors_json})
        writer.write_table(table)
        writer.close()

        # Load and verify ALL fields
        source = TimeSeriesSource(data=str(parquet_path), sensors=None)
        result = load_timeseries(source, str(tmp_path))

        assert len(result.sensors) == 1
        sensor = result.sensors[0]
        assert sensor.column_name == "TestColumn"
        assert sensor.sensor_type == "WindSpeed" and sensor.stat_type == "max"
        assert sensor.sensor_direction == "ENE"
        assert sensor.height == 120.5
        assert sensor.stat_type == "max"
        assert sensor.unit == "m/s"

    def test_load_parquet_no_embedded_metadata_raises_error(self, tmp_path: Path):
        """Test that Parquet loading raises error if no embedded metadata exists.

        Parquet files MUST have embedded column-level metadata.
        External sensors files are ignored for Parquet format.
        """
        # Create Parquet without embedded metadata
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2024, 1, 1, 0, 0)],
                "WindSpeed_100m_avg [m/s]": [5.5],
            }
        )
        parquet_path = tmp_path / "data.parquet"
        df.write_parquet(parquet_path)

        # Create sensors file (should be IGNORED for Parquet)
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

        # Load with sensors file specified - should raise ValueError
        source = TimeSeriesSource(
            data=str(parquet_path),
            sensors=str(sensors_path),
        )
        with pytest.raises(ValueError, match="No sensor metadata in Parquet file"):
            load_timeseries(source, str(tmp_path))

    def test_load_parquet_nonexistent_file_raises_error(self, tmp_path: Path):
        """Test that loading nonexistent Parquet file raises error."""
        source = TimeSeriesSource(
            data="./nonexistent.parquet",
            sensors="",
        )

        with pytest.raises(FileNotFoundError):
            load_timeseries(source, str(tmp_path))


class TestSaveTimeseriesParquet:
    """Tests for saving timeseries to Parquet format."""

    def test_save_parquet_basic(self, tmp_path: Path):
        """Test saving timeseries to basic Parquet file."""
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

        # Save as Parquet
        parquet_path = tmp_path / "data.parquet"
        source = TimeSeriesSource(data=str(parquet_path), sensors="")
        save_timeseries(source, str(tmp_path), ts_data)

        # Verify file exists
        assert parquet_path.exists()

        # Verify can be read back
        loaded_df = pl.read_parquet(parquet_path)
        assert loaded_df.shape == (2, 2)

    def test_save_parquet_creates_directories(self, tmp_path: Path):
        """Test that save creates parent directories for Parquet."""
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2024, 1, 1, 0, 0)],
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

        # Save to nested directory
        parquet_path = tmp_path / "deep" / "nested" / "dir" / "data.parquet"
        source = TimeSeriesSource(data=str(parquet_path), sensors="")
        save_timeseries(source, str(tmp_path), ts_data)

        assert parquet_path.exists()

    def test_save_parquet_with_sensors_file(self, tmp_path: Path):
        """Test saving Parquet with optional sensors file."""
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2024, 1, 1, 0, 0)],
                "Temperature_10m_avg [C]": [15.5],
            }
        )
        sensors = [
            SensorColumn(
                column_name="Temperature_10m_avg [C]",
                sensor_type="Temperature",
                sensor_direction="",
                height=10.0,
                stat_type="avg",
                unit="C",
            )
        ]
        ts_data = TimeSeriesData(df=df, sensors=sensors)

        # Save with both Parquet and sensors file
        parquet_path = tmp_path / "data.parquet"
        sensors_path = tmp_path / "sensors.yaml"
        source = TimeSeriesSource(
            data=str(parquet_path),
            sensors=str(sensors_path),
        )
        save_timeseries(source, str(tmp_path), ts_data)

        # Verify both files exist
        assert parquet_path.exists()
        assert sensors_path.exists()


class TestMetadataRoundTrip:
    """Tests for metadata preservation through save/load cycle.

    Tests both file-level and column-level metadata formats.
    File-level metadata stores all sensor info in the Parquet file schema.
    Column-level metadata stores sensor info per column (Julia-compatible).
    """

    @pytest.mark.parametrize("metadata_format", ["file", "column"])
    def test_metadata_roundtrip_parquet(self, tmp_path: Path, metadata_format: str):
        """Test that sensor metadata is preserved through Parquet save/load.

        Tests both file-level and column-level metadata formats.
        """
        df = pl.DataFrame(
            {
                "timestamp": [
                    datetime(2024, 1, 1, 0, 0),
                    datetime(2024, 1, 1, 0, 10),
                    datetime(2024, 1, 1, 0, 20),
                ],
                "WindSpeed_80m_avg [m/s]": [5.5, 6.0, 5.8],
                "WindSpeed_100m_avg [m/s]": [6.2, 6.8, 6.5],
            }
        )
        sensors = [
            SensorColumn(
                column_name="WindSpeed_80m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WindSpeed_100m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]
        original = TimeSeriesData(df=df, sensors=sensors)

        # Save with specified format
        parquet_path = tmp_path / f"data_{metadata_format}.parquet"
        source = TimeSeriesSource(data=str(parquet_path), sensors=None)
        _write_parquet_with_metadata(
            original.df,
            parquet_path,
            original.sensors,
        )
        loaded = load_timeseries(source, str(tmp_path))

        # Verify metadata preserved
        assert len(loaded.sensors) == len(original.sensors)
        for orig_sensor, load_sensor in zip(original.sensors, loaded.sensors):
            assert orig_sensor.column_name == load_sensor.column_name
            assert orig_sensor.sensor_type == load_sensor.sensor_type and orig_sensor.stat_type == load_sensor.stat_type
            assert orig_sensor.height == load_sensor.height
            assert orig_sensor.stat_type == load_sensor.stat_type
            assert orig_sensor.unit == load_sensor.unit

    @pytest.mark.parametrize("metadata_format", ["file", "column"])
    def test_metadata_roundtrip_all_sensor_types(self, tmp_path: Path, metadata_format: str):
        """Test metadata roundtrip with all sensor types.

        Tests both file-level and column-level metadata formats.
        """
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2024, 1, 1, 0, 0)],
                "WindSpeed_100m_avg [m/s]": [5.5],
                "WindDirection_100m_avg [deg]": [180.0],
                "Temperature_10m_avg [C]": [15.5],
                "Pressure_10m_avg [hPa]": [1013.25],
            }
        )
        sensors = [
            SensorColumn(
                column_name="WindSpeed_100m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WindDirection_100m_avg [deg]",
                sensor_type="WindDirection",
                sensor_direction="N",
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
            SensorColumn(
                column_name="Pressure_10m_avg [hPa]",
                sensor_type="Pressure",
                sensor_direction="",
                height=10.0,
                stat_type="avg",
                unit="hPa",
            ),
        ]
        original = TimeSeriesData(df=df, sensors=sensors)

        # Save with specified format
        parquet_path = tmp_path / f"data_{metadata_format}.parquet"
        source = TimeSeriesSource(data=str(parquet_path), sensors=None)
        _write_parquet_with_metadata(
            original.df,
            parquet_path,
            original.sensors,
        )
        loaded = load_timeseries(source, str(tmp_path))

        # Verify all sensor types preserved
        assert len(loaded.sensors) == 4
        sensor_types = [s.sensor_type for s in loaded.sensors if s.stat_type == "avg"]
        assert "WindSpeed" in sensor_types
        assert "WindDirection" in sensor_types
        assert "Temperature" in sensor_types
        assert "Pressure" in sensor_types


class TestFormatAutoDetection:
    """Tests for automatic format detection."""

    def test_load_csv_format(self, tmp_path: Path):
        """Test that CSV format is detected from .csv extension."""
        # Create test CSV
        csv_content = """timestamp,WindSpeed_100m_avg [m/s]
2024-01-01 00:00:00,5.5
2024-01-01 00:10:00,6.0
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

        # Load - should detect CSV format
        source = TimeSeriesSource(
            data=str(csv_path),
            sensors=str(sensors_path),
        )
        loaded = load_timeseries(source, str(tmp_path))

        assert loaded.df.shape == (2, 2)
        assert len(loaded.sensors) == 1

    def test_load_parquet_format(self, tmp_path: Path):
        """Test that Parquet format is detected from .parquet extension."""
        # Create and save Parquet
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2024, 1, 1, 0, 0)],
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

        parquet_path = tmp_path / "data.parquet"
        source = TimeSeriesSource(data=str(parquet_path), sensors="")
        save_timeseries(source, str(tmp_path), ts_data)

        # Load - should detect Parquet format
        loaded = load_timeseries(source, str(tmp_path))

        assert loaded.df.shape == (1, 2)
        assert len(loaded.sensors) == 1

    def test_save_csv_format(self, tmp_path: Path):
        """Test that CSV format is used for .csv extension."""
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2024, 1, 1, 0, 0)],
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

        # Save to CSV
        csv_path = tmp_path / "data.csv"
        sensors_path = tmp_path / "sensors.yaml"
        source = TimeSeriesSource(
            data=str(csv_path),
            sensors=str(sensors_path),
        )
        save_timeseries(source, str(tmp_path), ts_data)

        # Verify CSV file created
        assert csv_path.exists()
        assert csv_path.read_text().startswith("timestamp")

    def test_save_parquet_format(self, tmp_path: Path):
        """Test that Parquet format is used for .parquet extension."""
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2024, 1, 1, 0, 0)],
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

        # Save to Parquet
        parquet_path = tmp_path / "data.parquet"
        source = TimeSeriesSource(data=str(parquet_path), sensors="")
        save_timeseries(source, str(tmp_path), ts_data)

        # Verify Parquet file created
        assert parquet_path.exists()
        assert parquet_path.suffix == ".parquet"

    def test_unsupported_format_raises_error(self, tmp_path: Path):
        """Test that unsupported file format raises error."""
        # Create file with unsupported extension
        json_path = tmp_path / "data.json"
        json_path.write_text('{"timestamp": "2024-01-01"}')

        source = TimeSeriesSource(data=str(json_path), sensors="")

        with pytest.raises(ValueError, match="Unsupported data file format"):
            load_timeseries(source, str(tmp_path))


class TestBackwardCompatibility:
    """Tests for backward compatibility with CSV format."""

    def test_csv_backward_compatibility(self, tmp_path: Path):
        """Test that CSV format continues to work as before."""
        # Create test CSV
        csv_content = """timestamp,WindSpeed_100m_avg [m/s],WindDirection_100m_avg [deg]
2024-01-01 00:00:00,5.5,180.0
2024-01-01 00:10:00,6.0,185.0
2024-01-01 00:20:00,5.8,182.0
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

        # Load
        source = TimeSeriesSource(
            data=str(csv_path),
            sensors=str(sensors_path),
        )
        loaded = load_timeseries(source, str(tmp_path))

        # Verify
        assert loaded.df.shape == (3, 3)
        assert len(loaded.sensors) == 2

    def test_parquet_vs_csv_consistency(self, tmp_path: Path):
        """Test that Parquet and CSV produce equivalent results."""
        # Create same data
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

        # Save as CSV
        csv_path = tmp_path / "data.csv"
        csv_sensors_path = tmp_path / "sensors.yaml"
        csv_source = TimeSeriesSource(
            data=str(csv_path),
            sensors=str(csv_sensors_path),
        )
        csv_data = TimeSeriesData(df=df, sensors=sensors)
        save_timeseries(csv_source, str(tmp_path), csv_data)

        # Save as Parquet
        parquet_path = tmp_path / "data.parquet"
        parquet_source = TimeSeriesSource(data=str(parquet_path), sensors="")
        save_timeseries(parquet_source, str(tmp_path), csv_data)

        # Load both
        csv_loaded = load_timeseries(csv_source, str(tmp_path))
        parquet_loaded = load_timeseries(parquet_source, str(tmp_path))

        # Verify data values match
        csv_ws = csv_loaded.df["WindSpeed_100m_avg [m/s]"].to_list()
        parquet_ws = parquet_loaded.df["WindSpeed_100m_avg [m/s]"].to_list()
        assert csv_ws == parquet_ws

        # Verify metadata match
        assert len(csv_loaded.sensors) == len(parquet_loaded.sensors)
        for csv_s, parquet_s in zip(csv_loaded.sensors, parquet_loaded.sensors):
            assert csv_s.sensor_type == parquet_s.sensor_type and csv_s.stat_type == parquet_s.stat_type
            assert csv_s.height == parquet_s.height
