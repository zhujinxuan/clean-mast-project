"""Integration test for representative year calibration in report generation."""

from datetime import datetime
from pathlib import Path

import polars as pl
import tomli_w
from cleanmast.application.usecases.generate_report import generate_report
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.infrastructure.timeseries_io import save_timeseries
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)

_WS_COL = "WindSpeed_100m_avg [m/s]"


def _create_meso_parquet(tmp_path: Path) -> Path:
    """Create meso parquet with embedded sensor metadata spanning multiple years."""
    data_start = datetime(2010, 1, 1)
    data_end = datetime(2020, 6, 30, 23, 0)
    rep_year_start = datetime(2020, 1, 1)
    rep_year_end = datetime(2020, 6, 30, 23, 0)
    climate_ws = 7.0
    rep_year_ws = 7.07

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

    parquet_path = tmp_path / "meso" / "era5.parquet"
    source = TimeSeriesSource(data=str(parquet_path), sensors=None)
    save_timeseries(source, str(tmp_path), ts_data)
    return parquet_path


def _create_mast_parquet(tmp_path: Path) -> Path:
    """Create mast parquet with embedded sensor metadata."""
    data_start = datetime(2020, 1, 1)
    data_end = datetime(2020, 6, 30, 23, 0)
    timestamps = pl.datetime_range(data_start, data_end, "1h", eager=True)
    df = pl.DataFrame({
        "timestamp": timestamps,
        _WS_COL: [7.0] * len(timestamps),
    })

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

    parquet_path = tmp_path / "masts" / "M01.parquet"
    source = TimeSeriesSource(data=str(parquet_path), sensors=None)
    save_timeseries(source, str(tmp_path), ts_data)
    return parquet_path


def _create_representative_year_toml(tmp_path: Path) -> Path:
    """Create representative-year.toml for the analyzer."""
    config = {
        "masts": [
            {
                "name": "M01",
                "input": {"data": "masts/M01.parquet"},
                "output": {"data": "output.parquet"},
                "time_range": {
                    "min": "2020-01-01T00:00:00",
                    "max": "2020-06-30T23:00:00",
                },
                "meso_model": {
                    "method": "16-sector",
                    "meso_name": "era5",
                    "model_file": "train_meso_era5.jld2",
                },
            }
        ],
        "mesos": [
            {
                "name": "era5",
                "input": {"data": "meso/era5.parquet"},
            }
        ],
    }
    config_path = tmp_path / "representative-year.toml"
    with open(config_path, "wb") as f:
        tomli_w.dump(config, f)
    return config_path


def _create_rep_ts_report_toml(tmp_path: Path) -> Path:
    """Create rep-ts-report.toml with representative_year_calibration subsection."""
    config = {
        "datasets": [
            {
                "name": "mast",
                "masts": [{"name": "M01", "air_density": 1.225, "input": {"data": "./masts/M01.parquet"}}],
            },
        ],
        "subsections": [
            {"index": "2.5", "type": "timeseries", "title": "代表年风资源分析", "datasets": ["mast"]},
            {"index": "2.5.1", "type": "representative_year_calibration"},
        ],
    }
    config_path = tmp_path / "rep-ts-report.toml"
    with open(config_path, "wb") as f:
        tomli_w.dump(config, f)
    return config_path


class TestRepresentativeYearCalibrationIntegration:
    """Integration test for end-to-end report generation with rep year calibration."""

    def test_generates_report_with_representative_year_calibration(self, tmp_path: Path) -> None:
        """Report generation produces Typst source containing Chinese rep year headers."""
        _create_meso_parquet(tmp_path)
        _create_mast_parquet(tmp_path)
        _create_representative_year_toml(tmp_path)
        rep_ts_report_path = _create_rep_ts_report_toml(tmp_path)

        result = generate_report(str(rep_ts_report_path))

        assert isinstance(result, dict)
        assert "typ" in result

        typst_path = tmp_path / "rep-ts" / "report.typ"
        assert typst_path.exists(), f"Expected Typst file at {typst_path}"

        typst_content = typst_path.read_text(encoding="utf-8")
        assert (
            "测风代表年range" in typst_content
            or "代表年订正" in typst_content
        ), "Expected Chinese representative year calibration headers in Typst output"
