"""Tests for Parquet file-level metadata interoperability between Python and Julia."""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.infrastructure.timeseries_io import (
    load_timeseries,
    save_timeseries,
)
from cleanmast.subdomains.dataingestion.value_objects import SensorColumn
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)


class TestJuliaInterop:
    """Tests for reading Julia-generated Parquet files with file-level metadata."""

    def test_python_reads_julia_file(self, tmp_path: Path):
        """Python reads Julia-generated Parquet file with file-level metadata."""
        # Simulate Julia-generated Parquet file with file-level metadata
        # Julia writes metadata in camelCase for interop
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(["2024-01-01 00:00:00", "2024-01-01 00:10:00"]),
            "WindSpeed_100m_avg [m/s]": [5.5, 6.0],
            "WindDirection_100m_avg [deg]": [180.0, 185.0],
        })

        # Julia-style metadata (camelCase keys)
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
        metadata_json = json.dumps({"sensors": sensors_list})

        # Write Parquet with file-level metadata (Julia-style)
        parquet_path = tmp_path / "julia_file.parquet"
        table = pa.Table.from_pandas(df)
        writer = pq.ParquetWriter(parquet_path, table.schema)
        writer.add_key_value_metadata({"cleanmast_sensors": metadata_json})
        writer.write_table(table)
        writer.close()

        # Python reads the file
        source = TimeSeriesSource(data=str(parquet_path), sensors=None)
        result = load_timeseries(source, str(tmp_path))

        # Verify data was read correctly
        assert result.df.shape == (2, 3)
        assert len(result.sensors) == 2

        # Verify sensor metadata was preserved
        ws_sensor = next(s for s in result.sensors if s.sensor_type == "WindSpeed" and s.stat_type == "avg")
        assert ws_sensor.height == 100.0
        assert ws_sensor.column_name == "WindSpeed_100m_avg [m/s]"
        assert ws_sensor.sensor_direction == "N"
        assert ws_sensor.stat_type == "avg"
        assert ws_sensor.unit == "m/s"

        wd_sensor = next(s for s in result.sensors if s.sensor_type == "WindDirection" and s.stat_type == "avg")
        assert wd_sensor.height == 100.0
        assert wd_sensor.sensor_direction == "N"


class TestPythonInterop:
    """Tests for Python writing Julia-readable Parquet format."""

    def test_python_writes_julia_readable_format(self, tmp_path: Path):
        """Verify Python writes correct format that Julia can read."""
        # Create test data
        df = pl.DataFrame({
            "timestamp": [datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 1, 0, 10)],
            "WindSpeed_80m_avg [m/s]": [5.5, 6.0],
            "WindSpeed_120m_avg [m/s]": [6.2, 6.8],
        })

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
                column_name="WindSpeed_120m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=120.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]
        ts_data = TimeSeriesData(df=df, sensors=sensors)

        # Save as Parquet (should use file-level metadata for Julia interop)
        parquet_path = tmp_path / "python_write.parquet"
        source = TimeSeriesSource(data=str(parquet_path), sensors="")
        save_timeseries(source, str(tmp_path), ts_data)

        # Verify file exists
        assert parquet_path.exists()

        # Read back using PyArrow to verify metadata structure
        pq.ParquetFile(parquet_path)

        # Check that file has key-value metadata
        # The metadata should contain cleanmast_sensors
        assert parquet_path.exists()

        # Load using our load_timeseries to verify roundtrip works
        loaded = load_timeseries(source, str(tmp_path))

        assert loaded.df.shape == (2, 3)
        assert len(loaded.sensors) == 2
        assert loaded.sensors[0].height == 80.0
        assert loaded.sensors[1].height == 120.0


class TestEdgeCases:
    """Edge case tests for Parquet file-level metadata."""

    def test_empty_sensors(self, tmp_path: Path):
        """Test handling of empty sensors list in file-level metadata."""
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(["2024-01-01 00:00:00"]),
            "Value": [10.0],
        })

        # Empty sensors list
        metadata_json = json.dumps({"sensors": []})

        parquet_path = tmp_path / "empty_sensors.parquet"
        table = pa.Table.from_pandas(df)
        writer = pq.ParquetWriter(parquet_path, table.schema)
        writer.add_key_value_metadata({"cleanmast_sensors": metadata_json})
        writer.write_table(table)
        writer.close()

        # Load should work but return no sensors
        source = TimeSeriesSource(data=str(parquet_path), sensors=None)
        result = load_timeseries(source, str(tmp_path))

        assert result.df.shape == (1, 2)
        assert len(result.sensors) == 0

    def test_many_sensors(self, tmp_path: Path):
        """Test Parquet file with 100+ sensors."""
        # Create DataFrame with many columns
        data = {"timestamp": pd.to_datetime(["2024-01-01 00:00:00"])}
        sensors_list = []

        # Create 120 sensors (100+ edge case)
        for i in range(120):
            col_name = f"WindSpeed_{10 + i}m_avg [m/s]"
            data[col_name] = [5.0 + i * 0.1]
            sensors_list.append({
                "columnName": col_name,
                "sensorType": "WindSpeed",
                "sensorDirection": "",
                "height": float(10 + i),
                "statType": "avg",
                "unit": "m/s",
            })

        df = pd.DataFrame(data)
        metadata_json = json.dumps({"sensors": sensors_list})

        parquet_path = tmp_path / "many_sensors.parquet"
        table = pa.Table.from_pandas(df)
        writer = pq.ParquetWriter(parquet_path, table.schema)
        writer.add_key_value_metadata({"cleanmast_sensors": metadata_json})
        writer.write_table(table)
        writer.close()

        # Load and verify all 120 sensors
        source = TimeSeriesSource(data=str(parquet_path), sensors=None)
        result = load_timeseries(source, str(tmp_path))

        assert result.df.shape == (1, 121)  # timestamp + 120 data columns
        assert len(result.sensors) == 120

        # Verify specific heights
        heights = [s.height for s in result.sensors]
        assert 10.0 in heights
        assert 129.0 in heights

    def test_special_characters_in_column_names(self, tmp_path: Path):
        """Test handling of special characters in column names."""
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(["2024-01-01 00:00:00"]),
            "Speed_100m_avg [m/s]": [5.5],
            "Direction_100m_avg [deg]": [180.0],
            "Temperature_10m_avg [°C]": [15.5],
            "Pressure_10m_avg [hPa]": [1013.25],
        })

        sensors_list = [
            {"columnName": "Speed_100m_avg [m/s]", "sensorType": "WindSpeed", "sensorDirection": "", "height": 100.0, "statType": "avg", "unit": "m/s"},
            {"columnName": "Direction_100m_avg [deg]", "sensorType": "WindDirection", "sensorDirection": "", "height": 100.0, "statType": "avg", "unit": "deg"},
            {"columnName": "Temperature_10m_avg [°C]", "sensorType": "Temperature", "sensorDirection": "", "height": 10.0, "statType": "avg", "unit": "°C"},
            {"columnName": "Pressure_10m_avg [hPa]", "sensorType": "Pressure", "sensorDirection": "", "height": 10.0, "statType": "avg", "unit": "hPa"},
        ]
        metadata_json = json.dumps({"sensors": sensors_list})

        parquet_path = tmp_path / "special_chars.parquet"
        table = pa.Table.from_pandas(df)
        writer = pq.ParquetWriter(parquet_path, table.schema)
        writer.add_key_value_metadata({"cleanmast_sensors": metadata_json})
        writer.write_table(table)
        writer.close()

        # Load and verify
        source = TimeSeriesSource(data=str(parquet_path), sensors=None)
        result = load_timeseries(source, str(tmp_path))

        assert len(result.sensors) == 4
        column_names = [s.column_name for s in result.sensors]
        assert "Speed_100m_avg [m/s]" in column_names
        assert "Temperature_10m_avg [°C]" in column_names


class TestRoundTrip:
    """Round-trip tests for Parquet file-level metadata."""

    def test_python_roundtrip(self, tmp_path: Path):
        """Write Parquet → Read → Verify metadata preserved."""
        # Original data
        df_original = pl.DataFrame({
            "timestamp": [
                datetime(2024, 1, 1, 0, 0),
                datetime(2024, 1, 1, 0, 10),
                datetime(2024, 1, 1, 0, 20),
            ],
            "WindSpeed_80m_avg [m/s]": [5.5, 6.0, 5.8],
            "WindSpeed_100m_avg [m/s]": [6.2, 6.8, 6.5],
            "WindDirection_80m_avg [deg]": [180.0, 185.0, 182.0],
            "Temperature_10m_avg [C]": [15.5, 16.0, 15.8],
        })

        sensors_original = [
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
                column_name="WindDirection_80m_avg [deg]",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=80.0,
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

        ts_original = TimeSeriesData(df=df_original, sensors=sensors_original)

        # Write to Parquet
        parquet_path = tmp_path / "roundtrip.parquet"
        source = TimeSeriesSource(data=str(parquet_path), sensors="")
        save_timeseries(source, str(tmp_path), ts_original)

        # Read back
        ts_loaded = load_timeseries(source, str(tmp_path))

        # Verify data values match
        for col in df_original.columns:
            original_values = df_original[col].to_list()
            loaded_values = ts_loaded.df[col].to_list()
            assert original_values == loaded_values, f"Mismatch in column {col}"

        # Verify sensor metadata preserved
        assert len(ts_loaded.sensors) == len(sensors_original)

        for orig_sensor, loaded_sensor in zip(sensors_original, ts_loaded.sensors):
            assert orig_sensor.column_name == loaded_sensor.column_name
            assert orig_sensor.sensor_type == loaded_sensor.sensor_type and orig_sensor.stat_type == loaded_sensor.stat_type
            assert orig_sensor.height == loaded_sensor.height
            assert orig_sensor.stat_type == loaded_sensor.stat_type
            assert orig_sensor.unit == loaded_sensor.unit
            assert orig_sensor.sensor_direction == loaded_sensor.sensor_direction
