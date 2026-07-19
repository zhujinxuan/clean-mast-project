"""Tests for FileTimeSeriesRepository class and its module-level convenience functions.

Covers direct class instantiation, .load/.save on both parquet and csv+sidecar
variants, and the module-level convenience functions load_timeseries/save_timeseries
from shared.timeseries.io."""

from datetime import datetime
from pathlib import Path

import polars as pl
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData, TimeSeriesSource
from cleanmast.shared.timeseries.io import (
    load_timeseries,
    save_timeseries,
)
from cleanmast.shared.timeseries.io.file_repository import (
    FileTimeSeriesRepository,
)


def _make_test_data() -> TimeSeriesData:
    """Shared helper: create TimeSeriesData with 2 sensors exercising all 6 fields."""
    df = pl.DataFrame(
        {
            "timestamp": [
                datetime(2024, 1, 1, 0, 0),
                datetime(2024, 1, 1, 0, 10),
            ],
            "WindSpeed_80m_avg [m/s]": [5.5, 6.0],
            "WindDirection_80m_avg [deg]": [180.0, 185.0],
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
            column_name="WindDirection_80m_avg [deg]",
            sensor_type="WindDirection",
            sensor_direction="N",
            height=80.0,
            stat_type="avg",
            unit="deg",
        ),
    ]
    return TimeSeriesData(df=df, sensors=sensors)


def _assert_sensors_equal(original: list[SensorColumn], loaded: list[SensorColumn]) -> None:
    """Assert full fidelity: all 6 fields match for every sensor."""
    assert len(loaded) == len(original)
    for i, (orig, load) in enumerate(zip(original, loaded)):
        assert load.column_name == orig.column_name, f"sensor[{i}].column_name"
        assert load.sensor_type == orig.sensor_type, f"sensor[{i}].sensor_type"
        assert load.sensor_direction == orig.sensor_direction, f"sensor[{i}].sensor_direction"
        assert load.height == orig.height, f"sensor[{i}].height"
        assert load.stat_type == orig.stat_type, f"sensor[{i}].stat_type"
        assert load.unit == orig.unit, f"sensor[{i}].unit"


class TestFileTimeSeriesRepositoryClass:
    """Direct FileTimeSeriesRepository class tests — parquet and csv variants."""

    def test_parquet_roundtrip(self, tmp_path: Path):
        """Save/load parquet via FileTimeSeriesRepository class; assert full fidelity."""
        repo = FileTimeSeriesRepository()
        original = _make_test_data()
        source = TimeSeriesSource(data="./data.parquet", sensors="")

        repo.save(source, str(tmp_path), original)
        loaded = repo.load(source, str(tmp_path))

        # DataFrame values
        for col in original.df.columns:
            assert original.df[col].to_list() == loaded.df[col].to_list(), f"col {col}"

        _assert_sensors_equal(original.sensors, loaded.sensors)

    def test_csv_roundtrip(self, tmp_path: Path):
        """Save/load CSV via FileTimeSeriesRepository class; assert full fidelity."""
        repo = FileTimeSeriesRepository()
        original = _make_test_data()
        source = TimeSeriesSource(data="./data.csv", sensors="./sensors.yaml")

        repo.save(source, str(tmp_path), original)
        loaded = repo.load(source, str(tmp_path))

        # DataFrame values
        for col in original.df.columns:
            assert original.df[col].to_list() == loaded.df[col].to_list(), f"col {col}"

        _assert_sensors_equal(original.sensors, loaded.sensors)

    def test_parquet_load_with_sensor_direction(self, tmp_path: Path):
        """Parquet roundtrip preserves sensor_direction (non-empty)."""
        repo = FileTimeSeriesRepository()
        # Use non-empty sensor_direction values
        df = pl.DataFrame({
            "timestamp": [datetime(2024, 1, 1)],
            "WindSpeed_100m_avg [m/s]": [5.0],
            "WindDirection_100m_avg [deg]": [180.0],
        })
        sensors = [
            SensorColumn(
                column_name="WindSpeed_100m_avg [m/s]",
                sensor_type="WindSpeed",
                sensor_direction="SE",
                height=100.0,
                stat_type="avg",
                unit="m/s",
            ),
            SensorColumn(
                column_name="WindDirection_100m_avg [deg]",
                sensor_type="WindDirection",
                sensor_direction="NW",
                height=100.0,
                stat_type="avg",
                unit="deg",
            ),
        ]
        original = TimeSeriesData(df=df, sensors=sensors)
        source = TimeSeriesSource(data="./data2.parquet", sensors="")

        repo.save(source, str(tmp_path), original)
        loaded = repo.load(source, str(tmp_path))

        assert loaded.sensors[0].sensor_direction == "SE"
        assert loaded.sensors[1].sensor_direction == "NW"


class TestFileTimeSeriesRepositoryConvenienceFunctions:
    """Module-level convenience functions from shared.timeseries.io."""

    def test_convenience_parquet_roundtrip(self, tmp_path: Path):
        """load_timeseries/save_timeseries for parquet."""
        original = _make_test_data()
        source = TimeSeriesSource(data="./conv.parquet", sensors="")

        save_timeseries(source, str(tmp_path), original)
        loaded = load_timeseries(source, str(tmp_path))

        for col in original.df.columns:
            assert original.df[col].to_list() == loaded.df[col].to_list(), f"col {col}"
        _assert_sensors_equal(original.sensors, loaded.sensors)

    def test_convenience_csv_roundtrip(self, tmp_path: Path):
        """load_timeseries/save_timeseries for CSV."""
        original = _make_test_data()
        source = TimeSeriesSource(data="./conv.csv", sensors="./conv_sensors.yaml")

        save_timeseries(source, str(tmp_path), original)
        loaded = load_timeseries(source, str(tmp_path))

        for col in original.df.columns:
            assert original.df[col].to_list() == loaded.df[col].to_list(), f"col {col}"
        _assert_sensors_equal(original.sensors, loaded.sensors)

    def test_convenience_is_same_as_file_repository(self, tmp_path: Path):
        """Verify io convenience functions are the same as file_repository exports."""
        from cleanmast.shared.timeseries.io.file_repository import (
            load_timeseries as file_repo_load,
        )
        from cleanmast.shared.timeseries.io.file_repository import (
            save_timeseries as file_repo_save,
        )

        # Both paths refer to the same function objects
        assert load_timeseries is file_repo_load
        assert save_timeseries is file_repo_save

        # And they work correctly
        original = _make_test_data()
        source = TimeSeriesSource(data="./distinct.csv", sensors="./distinct.yaml")
        file_repo_save(source, str(tmp_path), original)
        loaded = file_repo_load(source, str(tmp_path))
        _assert_sensors_equal(original.sensors, loaded.sensors)
