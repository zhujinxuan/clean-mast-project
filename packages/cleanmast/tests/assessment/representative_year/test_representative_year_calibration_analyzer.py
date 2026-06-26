"""Tests for representative year calibration analyzer.

Task: Write unit tests for representative_year_calibration_analyzer.py
Scenarios:
  1. Normal 30+ year path (climate capped to 30 years)
  2. Short data path (5 complete years)
  3. No correction path (anomaly ~1.5%)
  4. Correction path (anomaly ~2.5%)
"""

from datetime import datetime
from pathlib import Path

import polars as pl
import pytest
from cleanmast.subdomains.assessment.subdomains.representative_year.services._calculator import (
    analyze_representative_year_calibration,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.infrastructure.timeseries_io import save_timeseries
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)

_WS_COL = "WindSpeed_100m_avg [m/s]"


def _make_project(
    tmp_path: Path,
    data_start: datetime,
    data_end: datetime,
    rep_year_start: datetime,
    rep_year_end: datetime,
    climate_ws: float,
    rep_year_ws: float,
) -> Path:
    """Create a temporary project directory with config and meso parquet."""
    timestamps = pl.datetime_range(data_start, data_end, "1h", eager=True)
    df = pl.DataFrame({"timestamp": timestamps})
    df = df.with_columns(
        pl.when(
            (pl.col("timestamp") >= rep_year_start)
            & (pl.col("timestamp") <= rep_year_end)
        )
        .then(rep_year_ws)
        .otherwise(climate_ws)
        .alias(_WS_COL)
    )

    sensors = [
        SensorColumn(
            column_name=_WS_COL,
            sensor_type="WindSpeed",
            sensor_direction="",
            height=100.0,
            stat_type="avg",
            unit="m/s",
        )
    ]
    ts_data = TimeSeriesData(df=df, sensors=sensors)

    parquet_rel = "meso/era5.parquet"
    parquet_path = tmp_path / parquet_rel
    source = TimeSeriesSource(data=str(parquet_path), sensors=None)
    save_timeseries(source, str(tmp_path), ts_data)

    config = f"""[[masts]]
name = "M01"
input = {{ data = "dummy.parquet" }}
output = {{ data = "output.parquet" }}
time_range = {{ min = "{rep_year_start.isoformat()}", max = "{rep_year_end.isoformat()}" }}
[masts.meso_model]
method = "16-sector"
meso_name = "era5"
model_file = "train_meso_era5.jld2"

[[mesos]]
name = "era5"
input = {{ data = "{parquet_rel}" }}
"""
    config_path = tmp_path / "representative-year.toml"
    config_path.write_text(config)

    return tmp_path


class TestAnalyzeRepresentativeYearCalibration:
    """Tests for analyze_representative_year_calibration."""

    def test_normal_30_plus_year_path(self, tmp_path: Path) -> None:
        """Climate period capped to 30 years for long datasets."""
        proj = _make_project(
            tmp_path=tmp_path,
            data_start=datetime(1990, 1, 1),
            data_end=datetime(2024, 6, 30, 23, 0),
            rep_year_start=datetime(2024, 1, 1),
            rep_year_end=datetime(2024, 6, 30, 23, 0),
            climate_ws=7.0,
            rep_year_ws=7.07,
        )

        result = analyze_representative_year_calibration(proj)

        assert result.shape == (1, 7)
        row = result.row(0, named=True)
        assert row["year_range"] == "202401~202406"
        assert row["mast_name"] == "M01"
        assert row["era5_name"] == "era5"
        assert row["climatology_mean_ws"] == pytest.approx(7.0, rel=1e-9)
        assert row["rep_year_mean_ws"] == pytest.approx(7.07, rel=1e-9)
        assert row["anomaly_percent"] == 1.0
        assert row["needs_correction"] is False

    def test_short_data_path(self, tmp_path: Path) -> None:
        """Climate period equals available complete years for short datasets."""
        proj = _make_project(
            tmp_path=tmp_path,
            data_start=datetime(2015, 1, 1),
            data_end=datetime(2020, 6, 30, 23, 0),
            rep_year_start=datetime(2020, 1, 1),
            rep_year_end=datetime(2020, 6, 30, 23, 0),
            climate_ws=7.0,
            rep_year_ws=7.07,
        )

        result = analyze_representative_year_calibration(proj)

        assert result.shape == (1, 7)
        row = result.row(0, named=True)
        assert row["year_range"] == "202001~202006"
        assert row["climatology_mean_ws"] == pytest.approx(7.0, rel=1e-9)
        assert row["rep_year_mean_ws"] == pytest.approx(7.07, rel=1e-9)
        assert row["anomaly_percent"] == 1.0
        assert row["needs_correction"] is False

    def test_no_correction_path(self, tmp_path: Path) -> None:
        """Anomaly ~1.5% does not trigger correction."""
        proj = _make_project(
            tmp_path=tmp_path,
            data_start=datetime(2010, 1, 1),
            data_end=datetime(2020, 6, 30, 23, 0),
            rep_year_start=datetime(2020, 1, 1),
            rep_year_end=datetime(2020, 6, 30, 23, 0),
            climate_ws=7.0,
            rep_year_ws=7.105,
        )

        result = analyze_representative_year_calibration(proj)

        assert result.shape == (1, 7)
        row = result.row(0, named=True)
        assert row["climatology_mean_ws"] == pytest.approx(7.0, rel=1e-9)
        assert row["rep_year_mean_ws"] == pytest.approx(7.105, rel=1e-9)
        assert row["anomaly_percent"] == pytest.approx(1.5, rel=1e-9)
        assert row["needs_correction"] is False

    def test_correction_path(self, tmp_path: Path) -> None:
        """Anomaly ~2.5% triggers correction."""
        proj = _make_project(
            tmp_path=tmp_path,
            data_start=datetime(2010, 1, 1),
            data_end=datetime(2020, 6, 30, 23, 0),
            rep_year_start=datetime(2020, 1, 1),
            rep_year_end=datetime(2020, 6, 30, 23, 0),
            climate_ws=7.0,
            rep_year_ws=7.175,
        )

        result = analyze_representative_year_calibration(proj)

        assert result.shape == (1, 7)
        row = result.row(0, named=True)
        assert row["climatology_mean_ws"] == pytest.approx(7.0, rel=1e-9)
        assert row["rep_year_mean_ws"] == pytest.approx(7.175, rel=1e-9)
        assert row["anomaly_percent"] == pytest.approx(2.5, rel=1e-9)
        assert row["needs_correction"] is True
