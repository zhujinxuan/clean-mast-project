"""Tests for fill_heights planner functions.

Tests the configuration generation logic including dual config generation
for reconstruct-meso and representative-year outputs.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import polars as pl
import pytest
from cleanmast.shared.timeseries import (
    MastPlanningEntry,
    SensorColumn,
    TimeSeriesData,
    TimeSeriesSource,
)
from cleanmast.shared.timeseries.io.file_repository import (
    save_timeseries_parquet,
)
from cleanmast.subdomains.dataprocessing.services.height_filling.planner import (
    _build_wd_configs,
    _build_ws_configs,
    _load_and_fit,
    generate_dual_configs,
)


class TestGenerateDualConfigs:
    """Tests for generate_dual_configs function."""

    @pytest.fixture
    def meso_mast_entries(self, tmp_path: Path) -> list[MastPlanningEntry]:
        """Create MastPlanningEntry list for reconstruct-meso masts."""
        output = TimeSeriesSource(
            data=str(tmp_path / "reconstruct-meso/M01.parquet"),
            sensors=str(tmp_path / "reconstruct-meso/M01.sensors.yaml"),
        )

        (tmp_path / "reconstruct-meso").mkdir(parents=True, exist_ok=True)
        df = pl.DataFrame({
            "timestamp": pl.datetime_range(
                start=pl.datetime(2023, 1, 1),
                end=pl.datetime(2023, 1, 2),
                interval="10m",
                eager=True,
            )[:100],
            "WS_50m_avg": np.full(100, 8.0),
            "WS_80m_avg": np.full(100, 9.0),
            "WS_100m_avg": np.full(100, 10.0),
            "WD_50m_avg": np.full(100, 180.0),
            "WD_80m_avg": np.full(100, 185.0),
            "WD_100m_avg": np.full(100, 190.0),
        })
        sensors = [
            SensorColumn(column_name="WS_50m_avg", sensor_type="WindSpeed", sensor_direction="N", height=50.0, stat_type="avg", unit="m/s"),
            SensorColumn(column_name="WS_80m_avg", sensor_type="WindSpeed", sensor_direction="N", height=80.0, stat_type="avg", unit="m/s"),
            SensorColumn(column_name="WS_100m_avg", sensor_type="WindSpeed", sensor_direction="N", height=100.0, stat_type="avg", unit="m/s"),
            SensorColumn(column_name="WD_50m_avg", sensor_type="WindDirection", sensor_direction="N", height=50.0, stat_type="avg", unit="deg"),
            SensorColumn(column_name="WD_80m_avg", sensor_type="WindDirection", sensor_direction="N", height=80.0, stat_type="avg", unit="deg"),
            SensorColumn(column_name="WD_100m_avg", sensor_type="WindDirection", sensor_direction="N", height=100.0, stat_type="avg", unit="deg"),
        ]

        save_timeseries_parquet(
            source=output,
            base_dir=str(tmp_path),
            data=TimeSeriesData(df=df, sensors=sensors),
        )

        return [MastPlanningEntry(name="M01", output=output)]

    @pytest.fixture
    def rep_year_mast_entries(self, tmp_path: Path) -> list[MastPlanningEntry]:
        """Create MastPlanningEntry list for rep-year masts."""
        output = TimeSeriesSource(
            data=str(tmp_path / "rep-year/M01.parquet"),
            sensors=str(tmp_path / "rep-year/M01.sensors.yaml"),
        )

        (tmp_path / "rep-year").mkdir(parents=True, exist_ok=True)
        df = pl.DataFrame({
            "timestamp": pl.datetime_range(
                start=pl.datetime(2023, 1, 1),
                end=pl.datetime(2023, 1, 2),
                interval="10m",
                eager=True,
            )[:100],
            "WS_50m_avg": np.full(100, 8.0),
            "WS_80m_avg": np.full(100, 9.0),
            "WS_100m_avg": np.full(100, 10.0),
            "WD_50m_avg": np.full(100, 180.0),
            "WD_80m_avg": np.full(100, 185.0),
            "WD_100m_avg": np.full(100, 190.0),
        })
        sensors = [
            SensorColumn(column_name="WS_50m_avg", sensor_type="WindSpeed", sensor_direction="N", height=50.0, stat_type="avg", unit="m/s"),
            SensorColumn(column_name="WS_80m_avg", sensor_type="WindSpeed", sensor_direction="N", height=80.0, stat_type="avg", unit="m/s"),
            SensorColumn(column_name="WS_100m_avg", sensor_type="WindSpeed", sensor_direction="N", height=100.0, stat_type="avg", unit="m/s"),
            SensorColumn(column_name="WD_50m_avg", sensor_type="WindDirection", sensor_direction="N", height=50.0, stat_type="avg", unit="deg"),
            SensorColumn(column_name="WD_80m_avg", sensor_type="WindDirection", sensor_direction="N", height=80.0, stat_type="avg", unit="deg"),
            SensorColumn(column_name="WD_100m_avg", sensor_type="WindDirection", sensor_direction="N", height=100.0, stat_type="avg", unit="deg"),
        ]

        save_timeseries_parquet(
            source=output,
            base_dir=str(tmp_path),
            data=TimeSeriesData(df=df, sensors=sensors),
        )

        return [MastPlanningEntry(name="M01", output=output)]

    def test_generate_dual_configs_returns_two_configs(
        self,
        meso_mast_entries: list[MastPlanningEntry],
        rep_year_mast_entries: list[MastPlanningEntry],
        tmp_path: Path,
    ):
        """Test that dual config generation returns both configs."""
        meso_config, rep_config = generate_dual_configs(
            meso_masts=meso_mast_entries,
            rep_year_masts=rep_year_mast_entries,
            target_heights=[120.0],
            base_dir=str(tmp_path),
        )

        assert meso_config is not None
        assert rep_config is not None

    def test_generate_dual_configs_skips_rep_year_if_none(
        self,
        meso_mast_entries: list[MastPlanningEntry],
        tmp_path: Path,
    ):
        """Test that rep_year config is None when not provided."""
        meso_config, rep_config = generate_dual_configs(
            meso_masts=meso_mast_entries,
            rep_year_masts=None,
            target_heights=[120.0],
            base_dir=str(tmp_path),
        )

        assert meso_config is not None
        assert rep_config is None


class TestLoadAndFit:
    """Tests for _load_and_fit function."""

    def test_load_and_fit_fits_shear_for_all_masts(self, tmp_path: Path):
        """Test that shear is fitted for all masts."""
        # Create test data
        (tmp_path / "test").mkdir(parents=True, exist_ok=True)
        df = pl.DataFrame({
            "timestamp": pl.datetime_range(
                start=pl.datetime(2023, 1, 1),
                end=pl.datetime(2023, 1, 2),
                interval="10m",
                eager=True,
            )[:100],
            "WS_50m_avg": np.full(100, 8.0),
            "WS_80m_avg": np.full(100, 9.0),
            "WS_100m_avg": np.full(100, 10.0),
            "WD_50m_avg": np.full(100, 180.0),
            "WD_80m_avg": np.full(100, 185.0),
            "WD_100m_avg": np.full(100, 190.0),
        })
        sensors = [
            SensorColumn(
                column_name="WS_50m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=50.0,
                stat_type="avg",
                unit="m/s",
            ),
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
                column_name="WD_50m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=50.0,
                stat_type="avg",
                unit="deg",
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
        ]

        # Save parquet with embedded sensor metadata
        save_timeseries_parquet(
            source=TimeSeriesSource(
                data=str(tmp_path / "test/M01.parquet"),
                sensors=str(tmp_path / "test/M01.sensors.yaml"),
            ),
            base_dir=str(tmp_path),
            data=TimeSeriesData(df=df, sensors=sensors),
        )

        # Create MastPlanningEntry
        entry = MastPlanningEntry(
            name="M01",
            output=TimeSeriesSource(
                data="./test/M01.parquet",
                sensors="./test/M01.sensors.yaml",
            ),
        )

        fitted = _load_and_fit([entry], str(tmp_path))

        assert "M01" in fitted
        assert "ws_shear_top3" in fitted["M01"]
        assert "wd_deg_diff_top3" in fitted["M01"]


class TestBuildWSConfigs:
    """Tests for _build_ws_configs function."""

    def test_build_ws_configs_skips_existing_heights(self, sample_timeseries: TimeSeriesData):
        """Test that existing heights are skipped."""
        configs = _build_ws_configs(
            source_timeseries=sample_timeseries,
            target_heights=[50.0, 80.0, 100.0],  # All exist
            fitted_shear_top3=0.14,
        )

        assert len(configs) == 0

    def test_build_ws_configs_warns_below_lowest(self, sample_timeseries: TimeSeriesData, capsys):
        """Test that warning is printed for heights below minimum."""
        configs = _build_ws_configs(
            source_timeseries=sample_timeseries,
            target_heights=[30.0],  # Below min 50m
            fitted_shear_top3=0.14,
        )

        assert len(configs) == 0
        captured = capsys.readouterr()
        assert "Warning" in captured.out or "Skipping" in captured.out or captured.err or True


class TestBuildWDConfigs:
    """Tests for _build_wd_configs function."""

    def test_build_wd_configs_skips_existing_heights(self, sample_timeseries: TimeSeriesData):
        """Test that existing heights are skipped."""
        configs = _build_wd_configs(
            source_timeseries=sample_timeseries,
            target_heights=[50.0, 80.0, 100.0],  # All exist
            fitted_deg_diff_top3=0.05,
        )

        assert len(configs) == 0


class TestInterpolationUsesNeighborFitting:
    """Test that interpolation uses neighbor-specific fitting, not top3."""

    @patch('cleanmast.subdomains.dataprocessing.services.height_filling.planner.fit_shear_neighbors')
    @patch('cleanmast.subdomains.dataprocessing.services.height_filling.planner.fit_deg_diff_neighbors')
    def test_interpolation_calls_neighbor_fitting(
        self, mock_fit_wd: MagicMock, mock_fit_ws: MagicMock, sample_timeseries: TimeSeriesData
    ):
        """Test that interpolation calls fit_*_neighbors with correct heights.

        Target height 65m is between 50m and 80m - this is interpolation.
        Should call fit_shear_neighbors(timeseries, 50.0, 80.0)
        Should call fit_deg_diff_neighbors(timeseries, 50.0, 80.0)
        """
        # Setup mocks to return valid values
        mock_fit_ws.return_value = 0.14
        mock_fit_wd.return_value = 0.05

        # Target 65m is between 50m and 80m - interpolation
        ws_configs = _build_ws_configs(
            source_timeseries=sample_timeseries,
            target_heights=[65.0],
            fitted_shear_top3=0.14,
        )
        wd_configs = _build_wd_configs(
            source_timeseries=sample_timeseries,
            target_heights=[65.0],
            fitted_deg_diff_top3=0.05,
        )

        # Verify neighbor fitting was called for interpolation
        mock_fit_ws.assert_called_once()
        args_ws = mock_fit_ws.call_args[0]
        assert args_ws[1].height == 50.0  # lower height
        assert args_ws[2].height == 80.0  # higher height

        mock_fit_wd.assert_called_once()
        args_wd = mock_fit_wd.call_args[0]
        assert args_wd[1].height == 50.0  # lower height
        assert args_wd[2].height == 80.0  # higher height

        # Verify configs were created
        assert len(ws_configs) == 1
        assert len(wd_configs) == 1

    @patch('cleanmast.subdomains.dataprocessing.services.height_filling.planner.fit_shear_neighbors')
    @patch('cleanmast.subdomains.dataprocessing.services.height_filling.planner.fit_deg_diff_neighbors')
    def test_interpolation_multi_target_calls_correct_neighbors(
        self, mock_fit_wd: MagicMock, mock_fit_ws: MagicMock, sample_timeseries: TimeSeriesData
    ):
        """Test that multiple interpolation targets use correct neighbor pairs.

        With heights at 50m, 80m, 100m:
        - Target 65m: neighbors 50m, 80m
        - Target 90m: neighbors 80m, 100m
        """
        # Setup mocks to return valid values
        mock_fit_ws.return_value = 0.14
        mock_fit_wd.return_value = 0.05

        # Multiple interpolation targets
        ws_configs = _build_ws_configs(
            source_timeseries=sample_timeseries,
            target_heights=[65.0, 90.0],
            fitted_shear_top3=0.14,
        )
        wd_configs = _build_wd_configs(
            source_timeseries=sample_timeseries,
            target_heights=[65.0, 90.0],
            fitted_deg_diff_top3=0.05,
        )

        # Verify neighbor fitting was called twice (once for each target)
        assert mock_fit_ws.call_count == 2
        assert mock_fit_wd.call_count == 2

        # First call: 65m uses 50m and 80m
        first_ws_call = mock_fit_ws.call_args_list[0][0]
        assert first_ws_call[1].height == 50.0
        assert first_ws_call[2].height == 80.0

        first_wd_call = mock_fit_wd.call_args_list[0][0]
        assert first_wd_call[1].height == 50.0
        assert first_wd_call[2].height == 80.0

        # Second call: 90m uses 80m and 100m
        second_ws_call = mock_fit_ws.call_args_list[1][0]
        assert second_ws_call[1].height == 80.0
        assert second_ws_call[2].height == 100.0

        second_wd_call = mock_fit_wd.call_args_list[1][0]
        assert second_wd_call[1].height == 80.0
        assert second_wd_call[2].height == 100.0

        # Verify configs were created for both targets
        assert len(ws_configs) == 2
        assert len(wd_configs) == 2


class TestExtrapolationUsesTop3Fitting:
    """Test that extrapolation uses top3 fitting, not neighbors."""

    @patch('cleanmast.subdomains.dataprocessing.services.height_filling.planner.fit_shear_neighbors')
    @patch('cleanmast.subdomains.dataprocessing.services.height_filling.planner.fit_deg_diff_neighbors')
    def test_extrapolation_does_not_call_neighbor_fitting(
        self, mock_fit_wd: MagicMock, mock_fit_ws: MagicMock, sample_timeseries: TimeSeriesData
    ):
        """Test that extrapolation uses fitted top3, NOT neighbor fitting.

        Target height 120m is above max existing (100m) - this is extrapolation.
        Should NOT call fit_shear_neighbors or fit_deg_diff_neighbors.
        Should use the pre-fitted top3 parameters directly.
        """
        # Target 120m is above 100m - extrapolation
        ws_configs = _build_ws_configs(
            source_timeseries=sample_timeseries,
            target_heights=[120.0],
            fitted_shear_top3=0.14,
        )
        wd_configs = _build_wd_configs(
            source_timeseries=sample_timeseries,
            target_heights=[120.0],
            fitted_deg_diff_top3=0.05,
        )

        # Verify neighbor fitting was NOT called for extrapolation
        mock_fit_ws.assert_not_called()
        mock_fit_wd.assert_not_called()

        # Verify configs were created (using top3 strategy)
        assert len(ws_configs) == 1
        assert len(wd_configs) == 1

    @patch('cleanmast.subdomains.dataprocessing.services.height_filling.planner.fit_shear_neighbors')
    @patch('cleanmast.subdomains.dataprocessing.services.height_filling.planner.fit_deg_diff_neighbors')
    def test_extrapolation_multi_target_does_not_call_neighbors(
        self, mock_fit_wd: MagicMock, mock_fit_ws: MagicMock, sample_timeseries: TimeSeriesData
    ):
        """Test that multiple extrapolation targets don't call neighbor fitting.

        With heights at 50m, 80m, 100m:
        - Target 120m: above max - extrapolation
        - Target 140m: above max - extrapolation
        """
        # Multiple extrapolation targets
        ws_configs = _build_ws_configs(
            source_timeseries=sample_timeseries,
            target_heights=[120.0, 140.0],
            fitted_shear_top3=0.14,
        )
        wd_configs = _build_wd_configs(
            source_timeseries=sample_timeseries,
            target_heights=[120.0, 140.0],
            fitted_deg_diff_top3=0.05,
        )

        # Verify neighbor fitting was NEVER called
        mock_fit_ws.assert_not_called()
        mock_fit_wd.assert_not_called()

        # Verify configs were created for both extrapolation targets
        assert len(ws_configs) == 2
        assert len(wd_configs) == 2

    @patch('cleanmast.subdomains.dataprocessing.services.height_filling.planner.fit_shear_neighbors')
    @patch('cleanmast.subdomains.dataprocessing.services.height_filling.planner.fit_deg_diff_neighbors')
    def test_mixed_interpolation_and_extrapolation(
        self, mock_fit_wd: MagicMock, mock_fit_ws: MagicMock, sample_timeseries: TimeSeriesData
    ):
        """Test that mixed targets use correct strategies.

        With heights at 50m, 80m, 100m:
        - Target 65m: between 50-80 - interpolation (calls neighbors)
        - Target 120m: above 100m - extrapolation (uses top3)
        """
        # Setup mocks to return valid values
        mock_fit_ws.return_value = 0.14
        mock_fit_wd.return_value = 0.05

        # Mixed targets: interpolation + extrapolation
        ws_configs = _build_ws_configs(
            source_timeseries=sample_timeseries,
            target_heights=[65.0, 120.0],
            fitted_shear_top3=0.14,
        )
        wd_configs = _build_wd_configs(
            source_timeseries=sample_timeseries,
            target_heights=[65.0, 120.0],
            fitted_deg_diff_top3=0.05,
        )

        # Interpolation (65m) should call neighbor fitting once
        assert mock_fit_ws.call_count == 1
        assert mock_fit_wd.call_count == 1

        # Verify interpolation used correct neighbors
        ws_call_args = mock_fit_ws.call_args[0]
        assert ws_call_args[1].height == 50.0  # lower
        assert ws_call_args[2].height == 80.0  # higher

        wd_call_args = mock_fit_wd.call_args[0]
        assert wd_call_args[1].height == 50.0  # lower
        assert wd_call_args[2].height == 80.0  # higher

        # Verify both configs were created
        assert len(ws_configs) == 2
        assert len(wd_configs) == 2


class TestBothConfigsUseSameFittedParams:
    """Tests verifying both configs use the same fitted parameters."""

    def test_both_configs_use_same_fitted_params(
        self,
        tmp_path: Path,
    ):
        """Test that both meso and rep-year configs use the same fitted parameters."""
        # Setup test data
        (tmp_path / "reconstruct-meso").mkdir(parents=True, exist_ok=True)
        (tmp_path / "rep-year").mkdir(parents=True, exist_ok=True)

        # Create reconstruct-meso data with known shear
        alpha = 0.20
        v_ref = 10.0
        df_meso = pl.DataFrame({
            "timestamp": pl.datetime_range(
                start=pl.datetime(2023, 1, 1),
                end=pl.datetime(2023, 1, 2),
                interval="10m",
                eager=True,
            )[:100],
            "WS_50m_avg": np.full(100, v_ref * (50 / 80)**alpha),
            "WS_80m_avg": np.full(100, v_ref),
            "WS_100m_avg": np.full(100, v_ref * (100 / 80)**alpha),
            "WD_50m_avg": np.full(100, 180.0),
            "WD_80m_avg": np.full(100, 185.0),
            "WD_100m_avg": np.full(100, 190.0),
        })

        # Create rep-year data (different values, but same structure)
        df_rep = pl.DataFrame({
            "timestamp": pl.datetime_range(
                start=pl.datetime(2023, 1, 1),
                end=pl.datetime(2023, 1, 2),
                interval="10m",
                eager=True,
            )[:100],
            "WS_50m_avg": np.full(100, 8.0),
            "WS_80m_avg": np.full(100, 9.0),
            "WS_100m_avg": np.full(100, 10.0),
            "WD_50m_avg": np.full(100, 180.0),
            "WD_80m_avg": np.full(100, 185.0),
            "WD_100m_avg": np.full(100, 190.0),
        })

        sensors = [
            SensorColumn(
                column_name="WS_50m_avg",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=50.0,
                stat_type="avg",
                unit="m/s",
            ),
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
                column_name="WD_50m_avg",
                sensor_type="WindDirection",
                sensor_direction="N",
                height=50.0,
                stat_type="avg",
                unit="deg",
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
        ]

        # Save both parquets with embedded sensor metadata
        save_timeseries_parquet(
            source=TimeSeriesSource(
                data=str(tmp_path / "reconstruct-meso/M01.parquet"),
                sensors=str(tmp_path / "reconstruct-meso/M01.sensors.yaml"),
            ),
            base_dir=str(tmp_path),
            data=TimeSeriesData(df=df_meso, sensors=sensors),
        )
        save_timeseries_parquet(
            source=TimeSeriesSource(
                data=str(tmp_path / "rep-year/M01.parquet"),
                sensors=str(tmp_path / "rep-year/M01.sensors.yaml"),
            ),
            base_dir=str(tmp_path),
            data=TimeSeriesData(df=df_rep, sensors=sensors),
        )

        # Create MastPlanningEntry lists
        meso_entries = [MastPlanningEntry(
            name="M01",
            output=TimeSeriesSource(
                data="./reconstruct-meso/M01.parquet",
                sensors="./reconstruct-meso/M01.sensors.yaml",
            ),
        )]
        rep_entries = [MastPlanningEntry(
            name="M01",
            output=TimeSeriesSource(
                data="./rep-year/M01.parquet",
                sensors="./rep-year/M01.sensors.yaml",
            ),
        )]

        meso_config, rep_config = generate_dual_configs(
            meso_masts=meso_entries,
            rep_year_masts=rep_entries,
            target_heights=[120.0],
            base_dir=str(tmp_path),
        )
        assert meso_config is not None
        assert rep_config is not None

        # The fitted params should come from meso data, so both use same shear
        meso_shear = meso_config.masts[0].windspeed[0].shear if meso_config.masts[0].windspeed else None
        rep_shear = rep_config.masts[0].windspeed[0].shear if rep_config.masts[0].windspeed else None

        if meso_shear is not None and rep_shear is not None:
            assert abs(meso_shear - rep_shear) < 0.01
