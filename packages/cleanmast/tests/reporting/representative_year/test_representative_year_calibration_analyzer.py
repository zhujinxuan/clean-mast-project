"""Tests for representative year calibration compute module — reporting domain.

Ported from tests/assessment/representative_year/test_representative_year_calibration_analyzer.py.
Test logic, inputs, expected values, and assertions preserved exactly.
"""

from datetime import datetime

import polars as pl
import pytest
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.subdomains.reporting.subdomains.representative_year.compute import (
    RepresentativeYearMastInput,
    analyze_representative_year_calibration,
)

_WS_COL = "WindSpeed_100m_avg [m/s]"


def _make_input(
    data_start: datetime,
    data_end: datetime,
    rep_year_start: datetime,
    rep_year_end: datetime,
    climate_ws: float,
    rep_year_ws: float,
) -> RepresentativeYearMastInput:
    """Create a RepresentativeYearMastInput with synthetic meso data."""
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
    meso_data = TimeSeriesData(df=df, sensors=sensors)

    return RepresentativeYearMastInput(
        mast_name="M01",
        meso_name="era5",
        meso_data=meso_data,
        rep_year_min=rep_year_start,
        rep_year_max=rep_year_end,
    )


class TestAnalyzeRepresentativeYearCalibration:
    """Tests for analyze_representative_year_calibration."""

    def test_normal_30_plus_year_path(self) -> None:
        """Climate period capped to 30 years for long datasets."""
        input_data = _make_input(
            data_start=datetime(1990, 1, 1),
            data_end=datetime(2024, 6, 30, 23, 0),
            rep_year_start=datetime(2024, 1, 1),
            rep_year_end=datetime(2024, 6, 30, 23, 0),
            climate_ws=7.0,
            rep_year_ws=7.07,
        )

        result = analyze_representative_year_calibration([input_data])

        assert result.shape == (1, 7)
        row = result.row(0, named=True)
        assert row["year_range"] == "202401~202406"
        assert row["mast_name"] == "M01"
        assert row["era5_name"] == "era5"
        assert row["climatology_mean_ws"] == pytest.approx(7.0, rel=1e-9)
        assert row["rep_year_mean_ws"] == pytest.approx(7.07, rel=1e-9)
        assert row["anomaly_percent"] == 1.0
        assert row["needs_correction"] is False

    def test_short_data_path(self) -> None:
        """Climate period equals available complete years for short datasets."""
        input_data = _make_input(
            data_start=datetime(2015, 1, 1),
            data_end=datetime(2020, 6, 30, 23, 0),
            rep_year_start=datetime(2020, 1, 1),
            rep_year_end=datetime(2020, 6, 30, 23, 0),
            climate_ws=7.0,
            rep_year_ws=7.07,
        )

        result = analyze_representative_year_calibration([input_data])

        assert result.shape == (1, 7)
        row = result.row(0, named=True)
        assert row["year_range"] == "202001~202006"
        assert row["climatology_mean_ws"] == pytest.approx(7.0, rel=1e-9)
        assert row["rep_year_mean_ws"] == pytest.approx(7.07, rel=1e-9)
        assert row["anomaly_percent"] == 1.0
        assert row["needs_correction"] is False

    def test_no_correction_path(self) -> None:
        """Anomaly ~1.5% does not trigger correction."""
        input_data = _make_input(
            data_start=datetime(2010, 1, 1),
            data_end=datetime(2020, 6, 30, 23, 0),
            rep_year_start=datetime(2020, 1, 1),
            rep_year_end=datetime(2020, 6, 30, 23, 0),
            climate_ws=7.0,
            rep_year_ws=7.105,
        )

        result = analyze_representative_year_calibration([input_data])

        assert result.shape == (1, 7)
        row = result.row(0, named=True)
        assert row["climatology_mean_ws"] == pytest.approx(7.0, rel=1e-9)
        assert row["rep_year_mean_ws"] == pytest.approx(7.105, rel=1e-9)
        assert row["anomaly_percent"] == pytest.approx(1.5, rel=1e-9)
        assert row["needs_correction"] is False

    def test_correction_path(self) -> None:
        """Anomaly ~2.5% triggers correction."""
        input_data = _make_input(
            data_start=datetime(2010, 1, 1),
            data_end=datetime(2020, 6, 30, 23, 0),
            rep_year_start=datetime(2020, 1, 1),
            rep_year_end=datetime(2020, 6, 30, 23, 0),
            climate_ws=7.0,
            rep_year_ws=7.175,
        )

        result = analyze_representative_year_calibration([input_data])

        assert result.shape == (1, 7)
        row = result.row(0, named=True)
        assert row["climatology_mean_ws"] == pytest.approx(7.0, rel=1e-9)
        assert row["rep_year_mean_ws"] == pytest.approx(7.175, rel=1e-9)
        assert row["anomaly_percent"] == pytest.approx(2.5, rel=1e-9)
        assert row["needs_correction"] is True
