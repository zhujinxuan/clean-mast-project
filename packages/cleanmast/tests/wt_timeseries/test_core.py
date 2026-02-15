"""Tests for wt_timeseries core module."""

import json
from datetime import datetime

import numpy as np
import polars as pl
import pyarrow.parquet as pq
import pytest

from cleanmast.models.sensor import SensorColumn
from cleanmast.models.timeseries import TimeSeriesSource
from cleanmast.wt_timeseries.config import WtTimeSeriesMast
from cleanmast.wt_timeseries.core import (
    _filter_sensors_by_height,
    _find_nearest_sensor,
    process_single_mast_csv,
    process_wt_timeseries,
)


class TestFindNearestSensor:
    """Tests for _find_nearest_sensor function."""

    @pytest.fixture
    def sample_sensors(self):
        """Create sample sensors for testing."""
        return [
            SensorColumn(
                column_name="WS_80m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WS_120m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=120.0,
                stat_type="avg",
                unit="m/s",
            ),
        ]

    def test_find_exact_match(self, sample_sensors):
        """Test finding sensor at exact height."""
        sensor = _find_nearest_sensor(sample_sensors, 100.0, "WindSpeed", "avg")
        assert sensor is not None
        assert sensor.height == 100.0
        assert sensor.column_name == "WS_100m_avg"

    def test_find_nearest_sensor(self, sample_sensors):
        """Test finding nearest sensor when exact match doesn't exist."""
        sensor = _find_nearest_sensor(sample_sensors, 110.0, "WindSpeed", "avg")
        assert sensor is not None
        assert sensor.height == 100.0  # Closest to 110

    def test_no_matching_sensor_type(self, sample_sensors):
        """Test returns None when no matching sensor type."""
        sensor = _find_nearest_sensor(sample_sensors, 100.0, "WindDirection", "avg")
        assert sensor is None

    def test_no_matching_stat_type(self, sample_sensors):
        """Test returns None when no matching stat type."""
        sensor = _find_nearest_sensor(sample_sensors, 100.0, "WindSpeed", "sd")
        assert sensor is None

    def test_empty_sensors_list(self):
        """Test returns None with empty sensors list."""
        sensor = _find_nearest_sensor([], 100.0, "WindSpeed", "avg")
        assert sensor is None


class TestFilterSensorsByHeight:
    """Tests for _filter_sensors_by_height function."""

    @pytest.fixture
    def complete_sensor_set(self):
        """Create complete sensor set with WS and WD at multiple heights."""
        return [
            SensorColumn(
                column_name="WS_80m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WS_120m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=120.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_80m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="deg",
            ),
            SensorColumn(
                column_name="WD_100m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="deg",
            ),
            SensorColumn(
                column_name="WD_120m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=120.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

    def test_filter_valid_heights(self, complete_sensor_set):
        """Test filtering heights with both WS and WD sensors."""
        csv_heights = [80.0, 100.0, 120.0]
        result = _filter_sensors_by_height(csv_heights, complete_sensor_set, "TGL1")

        assert len(result) == 3
        for height, ws_sensor, wd_sensor in result:
            assert ws_sensor.sensor_type == "WindSpeed"
            assert wd_sensor.sensor_type == "WindDirection"
            assert ws_sensor.height == height
            assert wd_sensor.height == height

    def test_filter_finds_nearest_ws_sensor(self, complete_sensor_set):
        """Test filtering finds nearest WS sensor when exact match missing."""
        # Remove WS at 100m - function should find nearest (80m)
        sensors_without_100m_ws = [
            s for s in complete_sensor_set if not (s.height == 100.0 and s.sensor_type == "WindSpeed")
        ]

        csv_heights = [80.0, 100.0, 120.0]
        result = _filter_sensors_by_height(csv_heights, sensors_without_100m_ws, "TGL1")

        # All three heights should still work (nearest sensor logic)
        assert len(result) == 3
        # For 100m, it should use the nearest WS sensor (80m)
        height_100_result = next((r for r in result if r[0] == 100.0), None)
        assert height_100_result is not None
        assert height_100_result[1].height == 80.0  # Nearest WS sensor

    def test_filter_finds_nearest_wd_sensor(self, complete_sensor_set):
        """Test filtering finds nearest WD sensor when exact match missing."""
        # Remove WD at 80m - function should find nearest (100m)
        sensors_without_80m_wd = [
            s for s in complete_sensor_set if not (s.height == 80.0 and s.sensor_type == "WindDirection")
        ]

        csv_heights = [80.0, 100.0, 120.0]
        result = _filter_sensors_by_height(csv_heights, sensors_without_80m_wd, "TGL1")

        # All three heights should still work (nearest sensor logic)
        assert len(result) == 3
        # For 80m, it should use the nearest WD sensor (100m)
        height_80_result = next((r for r in result if r[0] == 80.0), None)
        assert height_80_result is not None
        assert height_80_result[2].height == 100.0  # Nearest WD sensor

    def test_filter_no_valid_heights_when_no_sensors(self):
        """Test returns empty list when no sensors available."""
        csv_heights = [200.0]  # No sensors at this height
        result = _filter_sensors_by_height(csv_heights, [], "TGL1")

        assert len(result) == 0

    def test_filter_finds_nearest_for_distant_height(self, complete_sensor_set):
        """Test filtering finds nearest sensors for distant target height."""
        csv_heights = [200.0]  # No sensors at this height, but should find nearest
        result = _filter_sensors_by_height(csv_heights, complete_sensor_set, "TGL1")

        # Should find sensors (nearest ones at 120m)
        assert len(result) == 1
        assert result[0][0] == 200.0  # Target height
        assert result[0][1].height == 120.0  # Nearest WS
        assert result[0][2].height == 120.0  # Nearest WD


class TestProcessSingleMastCsv:
    """Tests for process_single_mast_csv function."""

    def create_test_parquet(self, project_dir, mast_name, sensors, data):
        """Helper to create a test parquet file with metadata."""
        filled_dir = project_dir / "representative-year" / "filled"
        filled_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = filled_dir / f"{mast_name}.parquet"

        # Ensure timestamp is properly formatted
        if "timestamp" in data:
            timestamps = data["timestamp"]
            if isinstance(timestamps, list):
                # Ensure all timestamps are Python datetime objects
                converted = []
                for ts in timestamps:
                    if isinstance(ts, datetime):
                        converted.append(ts)
                    else:
                        # Convert pl.datetime() expressions by evaluating them
                        # pl.datetime() returns an expression that evaluates to a datetime
                        converted.append(ts)
                data = dict(data)  # Make a copy
                data["timestamp"] = pl.Series("timestamp", converted, dtype=pl.Datetime)

        df = pl.DataFrame(data)

        # Ensure timestamp column is datetime type
        if "timestamp" in df.columns and df["timestamp"].dtype != pl.Datetime:
            df = df.with_columns(pl.col("timestamp").cast(pl.Datetime))

        table = df.to_arrow()

        # Serialize sensors to JSON
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

        writer = pq.ParquetWriter(parquet_path, table.schema)
        writer.add_key_value_metadata({"cleanmast_sensors": sensors_json})
        writer.write_table(table)
        writer.close()

        return parquet_path

    def test_csv_output_format(self, tmp_path):
        """Test CSV output has correct format."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        sensors = [
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_100m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        np.random.seed(42)
        data = {
            "timestamp": pl.datetime_range(
                start=pl.datetime(2023, 1, 1, 0, 0),
                end=pl.datetime(2023, 1, 1, 1, 0),
                interval="10m",
                eager=True,
            ),
            "WS_100m_avg": np.random.uniform(5, 15, 7),
            "WD_100m_avg": np.random.uniform(0, 360, 7),
        }

        self.create_test_parquet(project_dir, "TGL1", sensors, data)

        mast = WtTimeSeriesMast(
            name="TGL1",
            input=TimeSeriesSource(data="./representative-year/filled/TGL1.parquet"),
            csv_heights=[100.0],
            turbulence_heights=[],
        )

        process_single_mast_csv(mast, project_dir)

        # Check CSV was created
        output_csv = project_dir / "wt-timeseries" / "TGL1.csv"
        assert output_csv.exists()

        # Read and verify format
        df = pl.read_csv(output_csv)
        assert "timestamp" in df.columns
        assert "WS_100m_avg" in df.columns
        assert "WD_100m_avg" in df.columns
        assert len(df) == 7

    def test_timestamp_format_iso(self, tmp_path):
        """Test timestamp is in ISO format."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        sensors = [
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_100m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        data = {
            "timestamp": [datetime(2023, 6, 15, 12, 30, 0)],
            "WS_100m_avg": [10.5],
            "WD_100m_avg": [180.0],
        }

        self.create_test_parquet(project_dir, "TGL1", sensors, data)

        mast = WtTimeSeriesMast(
            name="TGL1",
            input=TimeSeriesSource(data="./representative-year/filled/TGL1.parquet"),
            csv_heights=[100.0],
            turbulence_heights=[],
        )

        process_single_mast_csv(mast, project_dir)

        output_csv = project_dir / "wt-timeseries" / "TGL1.csv"
        content = output_csv.read_text()

        # Check timestamp is in ISO format
        assert "2023-06-15T12:30:00" in content

    def test_column_names_original_parquet_names(self, tmp_path):
        """Test that column names match original parquet column names."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        sensors = [
            SensorColumn(
                column_name="WindSpeed_100m_avg_mps",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WindDirection_100m_avg_deg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        data = {
            "timestamp": [datetime(2023, 1, 1, 0, 0, 0)],
            "WindSpeed_100m_avg_mps": [10.0],
            "WindDirection_100m_avg_deg": [180.0],
        }

        self.create_test_parquet(project_dir, "TGL1", sensors, data)

        mast = WtTimeSeriesMast(
            name="TGL1",
            input=TimeSeriesSource(data="./representative-year/filled/TGL1.parquet"),
            csv_heights=[100.0],
            turbulence_heights=[],
        )

        process_single_mast_csv(mast, project_dir)

        output_csv = project_dir / "wt-timeseries" / "TGL1.csv"
        df = pl.read_csv(output_csv)

        # Column names should match original parquet names
        assert "WindSpeed_100m_avg_mps" in df.columns
        assert "WindDirection_100m_avg_deg" in df.columns

    def test_multiple_heights(self, tmp_path):
        """Test processing multiple heights."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        sensors = [
            SensorColumn(
                column_name="WS_100m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_100m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=100.0,
                stat_type="avg",
                unit="deg",
            ),
            SensorColumn(
                column_name="WS_120m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=120.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WD_120m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=120.0,
                stat_type="avg",
                unit="deg",
            ),
        ]

        np.random.seed(42)
        data = {
            "timestamp": pl.datetime_range(
                start=pl.datetime(2023, 1, 1, 0, 0),
                end=pl.datetime(2023, 1, 1, 1, 0),
                interval="10m",
                eager=True,
            ),
            "WS_100m_avg": np.random.uniform(5, 15, 7),
            "WD_100m_avg": np.random.uniform(0, 360, 7),
            "WS_120m_avg": np.random.uniform(5, 15, 7),
            "WD_120m_avg": np.random.uniform(0, 360, 7),
        }

        self.create_test_parquet(project_dir, "TGL1", sensors, data)

        mast = WtTimeSeriesMast(
            name="TGL1",
            input=TimeSeriesSource(data="./representative-year/filled/TGL1.parquet"),
            csv_heights=[100.0, 120.0],
            turbulence_heights=[],
        )

        process_single_mast_csv(mast, project_dir)

        output_csv = project_dir / "wt-timeseries" / "TGL1.csv"
        df = pl.read_csv(output_csv)

        assert "WS_100m_avg" in df.columns
        assert "WD_100m_avg" in df.columns
        assert "WS_120m_avg" in df.columns
        assert "WD_120m_avg" in df.columns
        assert len(df.columns) == 5  # timestamp + 4 data columns

    def test_no_valid_heights(self, tmp_path, caplog):
        """Test when no valid heights are found."""
        import logging

        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        sensors = [
            SensorColumn(
                column_name="WS_80m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=80.0,
                stat_type="avg",
                unit="m/s",
            ),
            # Missing WD sensor
        ]

        np.random.seed(42)
        data = {
            "timestamp": pl.datetime_range(
                start=pl.datetime(2023, 1, 1, 0, 0),
                end=pl.datetime(2023, 1, 1, 1, 0),
                interval="10m",
                eager=True,
            ),
            "WS_80m_avg": np.random.uniform(5, 15, 7),
        }

        self.create_test_parquet(project_dir, "TGL1", sensors, data)

        mast = WtTimeSeriesMast(
            name="TGL1",
            input=TimeSeriesSource(data="./representative-year/filled/TGL1.parquet"),
            csv_heights=[100.0],  # No sensors at this height
            turbulence_heights=[],
        )

        with caplog.at_level(logging.WARNING):
            process_single_mast_csv(mast, project_dir)

        # No CSV should be generated
        output_csv = project_dir / "wt-timeseries" / "TGL1.csv"
        assert not output_csv.exists()


class TestProcessWtTimeseries:
    """Tests for process_wt_timeseries function."""

    def test_process_all_masts(self, tmp_path):
        """Test processing multiple masts."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        # Create two test parquet files
        for mast_name in ["TGL1", "TGL2"]:
            filled_dir = project_dir / "representative-year" / "filled"
            filled_dir.mkdir(parents=True, exist_ok=True)
            parquet_path = filled_dir / f"{mast_name}.parquet"

            sensors = [
                SensorColumn(
                    column_name="WS_100m_avg",
                    sensor_type="WindSpeed",
                    sensor_direction="N",
                    height=100.0,
                    stat_type="avg",
                    unit="m/s",
                ),
                SensorColumn(
                    column_name="WD_100m_avg",
                    sensor_type="WindDirection",
                    sensor_direction="N",
                    height=100.0,
                    stat_type="avg",
                    unit="deg",
                ),
            ]

            data = {
                "timestamp": pl.Series("timestamp", [datetime(2023, 1, 1, 0, 0, 0)], dtype=pl.Datetime),
                "WS_100m_avg": [10.0],
                "WD_100m_avg": [180.0],
            }

            df = pl.DataFrame(data)
            table = df.to_arrow()

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

            writer = pq.ParquetWriter(parquet_path, table.schema)
            writer.add_key_value_metadata({"cleanmast_sensors": sensors_json})
            writer.write_table(table)
            writer.close()

        from cleanmast.wt_timeseries.config import WtTimeSeriesConfiguration

        config = WtTimeSeriesConfiguration(
            masts=[
                WtTimeSeriesMast(
                    name="TGL1",
                    input=TimeSeriesSource(data="./representative-year/filled/TGL1.parquet"),
                    csv_heights=[100.0],
                    turbulence_heights=[],
                ),
                WtTimeSeriesMast(
                    name="TGL2",
                    input=TimeSeriesSource(data="./representative-year/filled/TGL2.parquet"),
                    csv_heights=[100.0],
                    turbulence_heights=[],
                ),
            ]
        )

        process_wt_timeseries(config, project_dir)

        # Both CSVs should be created
        assert (project_dir / "wt-timeseries" / "TGL1.csv").exists()
        assert (project_dir / "wt-timeseries" / "TGL2.csv").exists()
