"""Tests for ParquetRepository class and its module-level convenience functions.

Covers direct class instantiation, .load/.save on both parquet and csv+sidecar
variants, and the module-level convenience functions load_timeseries/save_timeseries
from repositories.parquet_repository.
"""

from datetime import datetime
from pathlib import Path

import polars as pl
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData, TimeSeriesSource
from cleanmast.subdomains.dataingestion.repositories.parquet_repository import (
    ParquetRepository,
    load_timeseries,
    save_timeseries,
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


class TestParquetRepositoryClass:
    """Direct ParquetRepository class tests — parquet and csv variants."""

    def test_parquet_roundtrip(self, tmp_path: Path):
        """Save/load parquet via ParquetRepository class; assert full fidelity."""
        repo = ParquetRepository()
        original = _make_test_data()
        source = TimeSeriesSource(data="./data.parquet", sensors="")

        repo.save(source, str(tmp_path), original)
        loaded = repo.load(source, str(tmp_path))

        # DataFrame values
        for col in original.df.columns:
            assert original.df[col].to_list() == loaded.df[col].to_list(), f"col {col}"

        _assert_sensors_equal(original.sensors, loaded.sensors)

    def test_csv_roundtrip(self, tmp_path: Path):
        """Save/load CSV via ParquetRepository class; assert full fidelity."""
        repo = ParquetRepository()
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
        repo = ParquetRepository()
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


class TestParquetRepositoryConvenienceFunctions:
    """Module-level convenience functions from repositories.parquet_repository."""

    def test_convenience_parquet_roundtrip(self, tmp_path: Path):
        """load_timeseries/save_timeseries (from repositories) for parquet."""
        original = _make_test_data()
        source = TimeSeriesSource(data="./conv.parquet", sensors="")

        save_timeseries(source, str(tmp_path), original)
        loaded = load_timeseries(source, str(tmp_path))

        for col in original.df.columns:
            assert original.df[col].to_list() == loaded.df[col].to_list(), f"col {col}"
        _assert_sensors_equal(original.sensors, loaded.sensors)

    def test_convenience_csv_roundtrip(self, tmp_path: Path):
        """load_timeseries/save_timeseries (from repositories) for CSV."""
        original = _make_test_data()
        source = TimeSeriesSource(data="./conv.csv", sensors="./conv_sensors.yaml")

        save_timeseries(source, str(tmp_path), original)
        loaded = load_timeseries(source, str(tmp_path))

        for col in original.df.columns:
            assert original.df[col].to_list() == loaded.df[col].to_list(), f"col {col}"
        _assert_sensors_equal(original.sensors, loaded.sensors)

    def test_convenience_is_distinct_from_infrastructure(self, tmp_path: Path):
        """Verify repos convenience functions import is distinct from infrastructure."""
        # If this test passes, we have a valid import from the correct module
        from cleanmast.subdomains.dataingestion.infrastructure.timeseries_io import (
            load_timeseries as infra_load,
        )
        from cleanmast.subdomains.dataingestion.infrastructure.timeseries_io import (
            save_timeseries as infra_save,
        )
        from cleanmast.subdomains.dataingestion.repositories.parquet_repository import (
            load_timeseries as repo_load,
        )
        from cleanmast.subdomains.dataingestion.repositories.parquet_repository import (
            save_timeseries as repo_save,
        )

        # They are different objects (different modules)
        assert repo_load is not infra_load
        assert repo_save is not infra_save

        # But both work correctly
        original = _make_test_data()
        source = TimeSeriesSource(data="./distinct.csv", sensors="./distinct.yaml")
        repo_save(source, str(tmp_path), original)
        loaded = repo_load(source, str(tmp_path))
        _assert_sensors_equal(original.sensors, loaded.sensors)
