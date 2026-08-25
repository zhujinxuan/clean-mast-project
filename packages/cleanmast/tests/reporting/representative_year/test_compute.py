"""Unit tests for extracted functions in compute.py."""

from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.subdomains.reporting.model.analysis_input import (
    RepresentativeYearCalibrationPayload,
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.model.analysis_parameters import AnalysisParameters
from cleanmast.subdomains.reporting.subdomains.representative_year.compute import (
    _combine_sector_rows,
    _compute_calibration_summary,
    _compute_per_sector_regression,
    _SectorMesoStats,
    _SectorRegResult,
)


def _make_sensor(name: str, sensor_type: str, height: float) -> SensorColumn:
    """Create a minimal SensorColumn for testing."""
    return SensorColumn(
        column_name=name,
        sensor_type=sensor_type,
        sensor_direction="",
        stat_type="avg",
        height=height,
        unit="m/s" if sensor_type == "WindSpeed" else "deg",
    )


class TestCombineSectorRows:
    """Tests for _combine_sector_rows — pure zip function."""

    def test_adjustment_equals_slope_times_diff(self):
        """adjustment = slope x diff for each sector."""
        stats = [
            _SectorMesoStats(sector_index=i, clim_mean=5.0, rep_mean=5.5, diff=-0.5)
            for i in range(1, 17)
        ]
        regs = [
            _SectorRegResult(sector_index=i, slope=1.2, intercept=0.1, data_points=100)
            for i in range(1, 17)
        ]
        rows = _combine_sector_rows(stats, regs, height=120.0)
        assert len(rows) == 16
        for row in rows:
            assert row.adjustment == pytest.approx(row.slope * row.meso_difference, abs=1e-4)
            assert row.climatology_mean == 5.0
            assert row.rep_year_mean == 5.5
            assert row.slope == 1.2
            assert row.data_points == 100

    def test_sector_indices_match(self):
        """Each row's sector_index matches the input stats/regs."""
        stats = [_SectorMesoStats(sector_index=i, clim_mean=0.0, rep_mean=0.0, diff=0.0) for i in range(1, 17)]
        regs = [_SectorRegResult(sector_index=i, slope=0.0, intercept=0.0, data_points=0) for i in range(1, 17)]
        rows = _combine_sector_rows(stats, regs, height=100.0)
        for i, row in enumerate(rows, 1):
            assert row.sector_index == i


class TestComputePerSectorRegression:
    """Tests for _compute_per_sector_regression."""

    @pytest.fixture
    def aligned_data(self) -> tuple:
        """Create synthetic aligned mast+meso data with 16 sectors."""
        n = 1600
        rng = np.random.default_rng(42)
        timestamps = [datetime(2025, 1, 1) + timedelta(minutes=10 * i) for i in range(n)]
        wd = np.tile(np.arange(0, 360, 22.5), n // 16 + 1)[:n]
        meso_ws = rng.normal(6.0, 1.0, n).clip(0)
        mast_ws = 0.9 * meso_ws + 0.5 + rng.normal(0, 0.1, n)

        mast_sensors = [_make_sensor("ws_120m_avg", "WindSpeed", 120.0)]
        meso_sensors = [
            _make_sensor("meso_ws", "WindSpeed", 100.0),
            _make_sensor("meso_wd", "WindDirection", 100.0),
        ]

        mast_df = pl.DataFrame({"timestamp": timestamps, "ws_120m_avg": mast_ws})
        meso_df = pl.DataFrame({"timestamp": timestamps, "meso_ws": meso_ws, "meso_wd": wd})

        mast_ts = TimeSeriesData(df=mast_df, sensors=mast_sensors)
        meso_ts = TimeSeriesData(df=meso_df, sensors=meso_sensors)

        return mast_ts, meso_ts, mast_sensors[0], meso_sensors[0], meso_sensors[1]

    def test_returns_16_results(self, aligned_data):
        """Returns exactly 16 sector results."""
        mast, meso, mast_ws, meso_ws, meso_wd = aligned_data
        train_min = datetime(2025, 1, 1)
        train_max = datetime(2025, 1, 2)
        results = _compute_per_sector_regression(
            mast, meso, mast_ws, meso_ws, meso_wd, train_min, train_max,
        )
        assert len(results) == 16
        indices = {r.sector_index for r in results}
        assert indices == set(range(1, 17))

    def test_slope_near_one_for_correlated_data(self, aligned_data):
        """Slope should be ~1 for data with mast = 0.9 x meso + 0.5."""
        mast, meso, mast_ws, meso_ws, meso_wd = aligned_data
        train_min = datetime(2025, 1, 1)
        train_max = datetime(2025, 1, 2)
        results = _compute_per_sector_regression(
            mast, meso, mast_ws, meso_ws, meso_wd, train_min, train_max,
        )
        slopes = [r.slope for r in results if r.slope > 0]
        avg_slope = sum(slopes) / len(slopes)
        assert 0.7 < avg_slope < 1.1


class TestComputeCalibrationSummary:
    """Tests for _compute_calibration_summary."""

    @staticmethod
    def _build_meso_ts(r: float) -> TimeSeriesData:
        """Build meso TimeSeriesData: 2010-2020 daily, WindSpeed=7.0 except 2020=R."""
        timestamps = pl.datetime_range(
            datetime(2010, 1, 1), datetime(2020, 12, 31), "1d", eager=True
        )
        df = pl.DataFrame({"timestamp": timestamps})
        ws_col = "WindSpeed_100.0m_avg [m/s]"
        df = df.with_columns(
            pl.when(pl.col("timestamp").dt.year() == 2020)
            .then(r)
            .otherwise(7.0)
            .alias(ws_col)
        )
        sensor = _make_sensor(ws_col, "WindSpeed", 100.0)
        return TimeSeriesData(df=df, sensors=[sensor])

    @staticmethod
    def _build_item(meso_ts: TimeSeriesData) -> SingleMastAnalysisInput:
        """Build SingleMastAnalysisInput with rep_year = 2020."""
        payload = RepresentativeYearCalibrationPayload(
            meso_time_series=meso_ts,
            meso_name="era5",
            sampling_period="1d",
            rep_year_start=datetime(2020, 1, 1),
            rep_year_end=datetime(2020, 12, 31),
        )
        return SingleMastAnalysisInput(
            time_series=meso_ts,
            parameters=AnalysisParameters(
                air_density=1.225,
                extreme_wind_10min_heights=[],
                extreme_wind_3s_heights=[],
                extreme_wind_gust_factors=[],
                representative_year_heights=[100.0],
            ),
            mast_name="M01",
            representative_year_calibration_payload=payload,
        )

    def test_anomaly_positive_when_rep_year_windier(self):
        """Rep-year windier than climatology → positive anomaly, needs_correction."""
        r = 7.5
        meso_ts = self._build_meso_ts(r)
        item = self._build_item(meso_ts)
        summary = _compute_calibration_summary(item)
        # climatology: 3652 days@7.0 + 366 days@7.5 → 28309/4018 ≈ 7.0455
        # anomaly = (7.5 - 7.0455)/7.0455*100 ≈ 6.45
        assert summary.anomaly_percent == pytest.approx(6.45, abs=0.02)
        assert summary.needs_correction is True
        assert summary.rep_year_mean_ws == 7.5
        assert summary.climatology_mean_ws == pytest.approx(7.05, abs=0.02)

    def test_no_correction_when_rep_year_close_to_climatology(self):
        """Rep-year close to climatology → small anomaly, no correction."""
        r = 7.05
        meso_ts = self._build_meso_ts(r)
        item = self._build_item(meso_ts)
        summary = _compute_calibration_summary(item)
        # climatology: 3652*7.0 + 366*7.05 → 28144.3/4018 ≈ 7.0046
        # anomaly = (7.05 - 7.0046)/7.0046*100 ≈ 0.65
        assert summary.anomaly_percent == pytest.approx(0.65, abs=0.02)
        assert summary.needs_correction is False


class TestRepresentativeYearSectionGuard:
    """Tests for the from_inputs guard on empty representative_year_heights."""

    def test_from_inputs_raises_on_empty_representative_year_heights(self):
        """RepresentativeYearSection.from_inputs raises ValueError when
        representative_year_heights is empty for a SingleMastAnalysisInput."""
        from datetime import datetime

        from cleanmast.subdomains.reporting.subdomains.representative_year.section import (
            RepresentativeYearSection,
        )

        item = SingleMastAnalysisInput(
            time_series=TestComputeCalibrationSummary._build_meso_ts(7.0),
            parameters=AnalysisParameters(
                air_density=1.225,
                extreme_wind_10min_heights=[],
                extreme_wind_3s_heights=[],
                extreme_wind_gust_factors=[],
                representative_year_heights=[],  # empty — should trigger guard
            ),
            mast_name="M01",
            representative_year_calibration_payload=RepresentativeYearCalibrationPayload(
                meso_time_series=TestComputeCalibrationSummary._build_meso_ts(7.0),
                meso_name="era5",
                sampling_period="1d",
                rep_year_start=datetime(2020, 1, 1),
                rep_year_end=datetime(2020, 12, 31),
            ),
        )

        with pytest.raises(ValueError, match="representative_year_heights"):
            RepresentativeYearSection.from_inputs([item])

    def test_from_inputs_succeeds_with_non_empty_representative_year_heights(self):
        """from_inputs succeeds when representative_year_heights is populated."""
        from datetime import datetime

        from cleanmast.subdomains.reporting.subdomains.representative_year.section import (
            RepresentativeYearSection,
        )

        meso_ts = TestComputeCalibrationSummary._build_meso_ts(7.0)
        item = SingleMastAnalysisInput(
            time_series=meso_ts,
            parameters=AnalysisParameters(
                air_density=1.225,
                extreme_wind_10min_heights=[],
                extreme_wind_3s_heights=[],
                extreme_wind_gust_factors=[],
                representative_year_heights=[100.0],
            ),
            mast_name="M01",
            representative_year_calibration_payload=RepresentativeYearCalibrationPayload(
                meso_time_series=meso_ts,
                meso_name="era5",
                sampling_period="10min",
                rep_year_start=datetime(2020, 1, 1),
                rep_year_end=datetime(2020, 12, 31),
            ),
        )

        section = RepresentativeYearSection.from_inputs([item])
        assert section is not None
        assert len(section.atoms) >= 0
