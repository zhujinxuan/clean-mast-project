from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import tomli
from cleanmast.shared.timeseries.sensor_column import SensorColumn
from cleanmast.shared.timeseries.time_range import TimeRange
from cleanmast.shared.timeseries.time_series_source import TimeSeriesSource
from cleanmast.subdomains.configuration import (
    AnalysisWindow,
    DiscoveredConfig,
    FillHeightsConfiguration,
    FlatReportConfig,
    ProjectConfig,
    RepresentativeYearMast,
    RepresentativeYearMesoModel,
)
from cleanmast.subdomains.configuration.services.recommend_report import (
    _build_analysis_windows,
    _build_dataset_for_timeseries,
    _discover_temporal_heights,
    _discover_wind_rose_heights,
    recommend_report,
)

TR_A = TimeRange(min=datetime(2025, 3, 1), max=datetime(2026, 2, 28))
TR_B = TimeRange(min=datetime(2024, 1, 1), max=datetime(2024, 12, 31))


class FakeRepo:
    """Stub TimeSeriesRepository returning MagicMock for tests that patch calculate_air_density."""
    def load(self, source, base_dir):
        return MagicMock()

    def save(self, source, base_dir, data):
        raise NotImplementedError


fake_repo = FakeRepo()


def _mast(name: str, tr: TimeRange) -> RepresentativeYearMast:
    src = TimeSeriesSource(data="/dev/null")
    return RepresentativeYearMast(
        name=name,
        input=src,
        output=src,
        time_range=tr,
        meso_model=RepresentativeYearMesoModel(
            method="16-sector",
            meso_name="X",
            model_file="x.jld2",
        ),
    )


class TestBuildAnalysisWindows:
    def test_groups_same_range(self):
        result = _build_analysis_windows(
            [_mast("A", TR_A), _mast("B", TR_A), _mast("C", TR_B)],
        )
        assert len(result) == 2
        names = {tuple(sorted(aw.target_masts)) for aw in result}
        assert names == {("A", "B"), ("C",)}

    def test_single_mast(self):
        result = _build_analysis_windows([_mast("X", TR_A)])
        assert len(result) == 1
        assert result[0].target_masts == ["X"]

    def test_empty(self):
        assert _build_analysis_windows([]) == []


def _sensor_col(sensor_type: str, height: float, stat_type: str = "avg") -> SensorColumn:
    return SensorColumn(
        column_name=f"{sensor_type}_{height}m_{stat_type}",
        sensor_type=sensor_type,
        sensor_direction="",
        height=height,
        stat_type=stat_type,
        unit="m/s" if sensor_type == "WindSpeed" else "deg",
    )


class TestDiscoverWindRoseHeights:
    """Tests for the _discover_wind_rose_heights pairing + band rule."""

    def test_band_case_returns_paired_heights_in_120_160(self):
        """Paired heights inside 120–160m win when any exist."""
        sensors = [
            _sensor_col("WindSpeed", 50.0),
            _sensor_col("WindDirection", 50.0),
            _sensor_col("WindSpeed", 130.0),
            _sensor_col("WindDirection", 130.0),
            _sensor_col("WindSpeed", 160.0),
            _sensor_col("WindDirection", 160.0),
        ]
        assert _discover_wind_rose_heights(sensors) == [130.0, 160.0]

    def test_fallback_case_returns_all_paired_heights_when_no_band(self):
        """Short masts fall back to every paired height, unfiltered."""
        sensors = [
            _sensor_col("WindSpeed", 50.0),
            _sensor_col("WindDirection", 50.0),
            _sensor_col("WindSpeed", 100.0),
            _sensor_col("WindDirection", 100.0),
        ]
        assert _discover_wind_rose_heights(sensors) == [50.0, 100.0]

    def test_unpaired_ws_height_is_excluded(self):
        """WS avg without a WD avg pair at the same height is not recommended."""
        sensors = [
            _sensor_col("WindSpeed", 80.0),
            _sensor_col("WindSpeed", 140.0),
            _sensor_col("WindDirection", 140.0),
        ]
        assert _discover_wind_rose_heights(sensors) == [140.0]

    def test_unpaired_ws_only_yields_empty(self):
        """WS sensors with no WD pairs at all yield an empty list."""
        sensors = [
            _sensor_col("WindSpeed", 100.0),
            _sensor_col("WindSpeed", 140.0),
        ]
        assert _discover_wind_rose_heights(sensors) == []

    def test_wd_only_heights_are_ignored(self):
        """WD sensors without WS pairs do not contribute heights."""
        sensors = [
            _sensor_col("WindDirection", 130.0),
        ]
        assert _discover_wind_rose_heights(sensors) == []

    def test_empty_sensors(self):
        assert _discover_wind_rose_heights([]) == []


class TestDiscoverTemporalHeights:
    """Tests for the _discover_temporal_heights band-when-available rule."""

    def test_band_case_returns_band_heights_only(self):
        """WS avg heights inside 120–160m win when any exist."""
        sensors = [
            _sensor_col("WindSpeed", 40.0),
            _sensor_col("WindSpeed", 120.0),
            _sensor_col("WindSpeed", 140.0),
            _sensor_col("WindSpeed", 160.0),
            _sensor_col("WindSpeed", 200.0),
        ]
        assert _discover_temporal_heights(sensors) == [120.0, 140.0, 160.0]

    def test_fallback_case_returns_all_heights_when_no_band(self):
        """Short masts fall back to every WS avg height, non-empty."""
        sensors = [
            _sensor_col("WindSpeed", 40.0),
            _sensor_col("WindSpeed", 80.0),
            _sensor_col("WindSpeed", 100.0),
        ]
        assert _discover_temporal_heights(sensors) == [40.0, 80.0, 100.0]

    def test_non_avg_and_non_ws_sensors_are_ignored(self):
        """Only WindSpeed avg sensors contribute temporal heights."""
        sensors = [
            _sensor_col("WindSpeed", 50.0),
            _sensor_col("WindSpeed", 140.0, "sd"),
            _sensor_col("WindSpeed", 150.0, "max"),
            _sensor_col("WindDirection", 140.0),
        ]
        assert _discover_temporal_heights(sensors) == [50.0]

    def test_no_ws_avg_sensors_yields_empty(self):
        """No WS avg sensors at all yields an empty list."""
        sensors = [_sensor_col("WindDirection", 130.0)]
        assert _discover_temporal_heights(sensors) == []

    def test_empty_sensors(self):
        assert _discover_temporal_heights([]) == []


def _sensor(col: str, height: float, stype: str, unit: str) -> dict:
    return {
        "column_name": col,
        "height": height,
        "sensor_type": stype,
        "sensor_direction": "",
        "stat_type": "avg",
        "unit": unit,
    }


def _valid_mast(name: str, data_dir: str) -> dict:
    return {
        "name": name,
        "input": {"data": f"input/{name}.csv"},
        "output": {"data": f"{data_dir}/{name}.parquet"},
        "windspeed": [
            {
                "target_sensor": _sensor("WS_100m:interpolated", 100.0, "WindSpeed", "m/s"),
                "references": [
                    {"sensor": _sensor("WS_80m", 80.0, "WindSpeed", "m/s"), "weight": 0.5},
                    {"sensor": _sensor("WS_120m", 120.0, "WindSpeed", "m/s"), "weight": 0.5},
                ],
                "shear": 0.14,
            }
        ],
        "winddirection": [
            {
                "target_sensor": _sensor("WD_100m:interpolated", 100.0, "WindDirection", "deg"),
                "references": [
                    {"sensor": _sensor("WD_80m", 80.0, "WindDirection", "deg"), "weight": 0.5},
                    {"sensor": _sensor("WD_120m", 120.0, "WindDirection", "deg"), "weight": 0.5},
                ],
                "deg_diff_per_m": 0.5,
            }
        ],
    }


def _valid_reconstruct_meso_mast(name: str, data_dir: str) -> dict:
    return {
        "name": name,
        "input": {"data": f"input/{name}.csv"},
        "output": {"data": f"{data_dir}/{name}.parquet"},
        "time_range": {
            "min": datetime(2025, 3, 1),
            "max": datetime(2026, 2, 28),
        },
        "models": {
            "windspeed": {
                "method": "1-sector",
                "meso_name": "ERA5",
                "model_file": "models/ws.jld2",
            },
            "winddirection": {
                "method": "constant-offset",
                "meso_name": "ERA5",
                "model_file": "models/wd.jld2",
            },
        },
    }


class TestRecommendReport:
    def _create_fill_heights_toml(self, tmp_path: Path, filename: str, data_dir: str) -> None:
        config = {"masts": [_valid_mast("M1", data_dir)]}
        path = tmp_path / filename
        import tomli_w
        with open(path, "wb") as f:
            tomli_w.dump(config, f)

        parquet_path = tmp_path / data_dir / "M1.parquet"
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        parquet_path.write_bytes(b"")

    def _create_multi_mast_fill_heights_toml(
        self, tmp_path: Path, filename: str, data_dir: str
    ) -> None:
        config = {
            "masts": [
                _valid_mast("M1", data_dir),
                _valid_mast("M2", data_dir),
            ]
        }
        path = tmp_path / filename
        import tomli_w
        with open(path, "wb") as f:
            tomli_w.dump(config, f)

        for mast_name in ("M1", "M2"):
            parquet_path = tmp_path / data_dir / f"{mast_name}.parquet"
            parquet_path.parent.mkdir(parents=True, exist_ok=True)
            parquet_path.write_bytes(b"")

    def _create_representative_year_toml(
        self, tmp_path: Path, mast_names: list[str] | None = None, tr: TimeRange | None = None
    ) -> None:
        """Create representative-year.toml with given mast names and time range."""
        if mast_names is None:
            mast_names = ["M1"]
        if tr is None:
            tr = TR_A

        masts = []
        for name in mast_names:
            masts.append({
                "name": name,
                "input": {"data": "/dev/null"},
                "output": {"data": "/dev/null"},
                "time_range": {"min": tr.min, "max": tr.max},
                "meso_model": {
                    "method": "16-sector",
                    "meso_name": "ERA5",
                    "model_file": "model.jld2",
                },
            })
        config = {
            "masts": masts,
            "mesos": [{"name": "ERA5", "input": {"data": "raw/ERA5.csv"}}],
        }
        import tomli_w
        with open(tmp_path / "representative-year.toml", "wb") as f:
            tomli_w.dump(config, f)

    @patch(
        "cleanmast.subdomains.configuration.services.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    def test_generates_flat_format_with_datasets_catalog(self, mock_calc_density, tmp_path):
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
        )
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-representative-year.toml",
            "representative-year-fill-heights",
        )

        self._create_representative_year_toml(tmp_path)

        pc = ProjectConfig(tmp_path)
        dc = recommend_report(pc, repo=fake_repo)
        dc.write_to(tmp_path)
        output_path = tmp_path / dc.filename

        assert output_path.exists()
        assert output_path.name == "rep-ts-report.toml"

        with open(output_path, "rb") as f:
            config = FlatReportConfig.model_validate(tomli.load(f))
        assert len(config.datasets) == 3

        filled_meso_ds = next(ds for ds in config.datasets if ds.name == "reconstruct_meso_filled_heights")
        repyear_ds = next(ds for ds in config.datasets if ds.name == "repyear")
        assert len(filled_meso_ds.masts) == 1
        assert len(repyear_ds.masts) == 1
        assert filled_meso_ds.masts[0].air_density == 1.225
        assert repyear_ds.masts[0].air_density == 1.225

    @patch(
        "cleanmast.subdomains.configuration.services.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    def test_meso_subsection_indices_and_ordering(self, mock_calc_density, tmp_path):
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
        )
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-representative-year.toml",
            "representative-year-fill-heights",
        )

        self._create_representative_year_toml(tmp_path)

        pc = ProjectConfig(tmp_path)
        dc = recommend_report(pc, repo=fake_repo)
        dc.write_to(tmp_path)
        output_path = tmp_path / dc.filename
        with open(output_path, "rb") as f:
            config = FlatReportConfig.model_validate(tomli.load(f))

        meso_subsections = [s for s in config.subsections if s.index.startswith("2.4")]
        assert len(meso_subsections) == 8
        assert meso_subsections[0].type == "timeseries"
        assert meso_subsections[0].title == "测风年风资源分析"
        for child in meso_subsections[1:]:
            assert child.datasets == ["reconstruct_meso_filled_heights"], f"Expected datasets=['reconstruct_meso_filled_heights'] for {child.index}, got {child.datasets}"

    @patch(
        "cleanmast.subdomains.configuration.services.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    def test_rep_subsection_indices_and_ordering(self, mock_calc_density, tmp_path):
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
        )
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-representative-year.toml",
            "representative-year-fill-heights",
        )

        self._create_representative_year_toml(tmp_path)

        pc = ProjectConfig(tmp_path)
        dc = recommend_report(pc, repo=fake_repo)
        dc.write_to(tmp_path)
        output_path = tmp_path / dc.filename
        with open(output_path, "rb") as f:
            config = FlatReportConfig.model_validate(tomli.load(f))

        rep_subsections = [s for s in config.subsections if s.index.startswith("2.5")]
        assert len(rep_subsections) == 6
        assert rep_subsections[0].type == "timeseries"
        for child in rep_subsections[1:]:
            if child.index == "2.5.1":
                assert child.datasets == ["receive_repyear_calibration_input"]
            else:
                assert child.datasets == ["repyear"], f"Expected datasets=['repyear'] for {child.index}, got {child.datasets}"

    @patch(
        "cleanmast.subdomains.configuration.services.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    def test_fifty_year_subsection_indices_and_ordering(self, mock_calc_density, tmp_path):
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
        )
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-representative-year.toml",
            "representative-year-fill-heights",
        )

        self._create_representative_year_toml(tmp_path)

        pc = ProjectConfig(tmp_path)
        dc = recommend_report(pc, repo=fake_repo)
        dc.write_to(tmp_path)
        output_path = tmp_path / dc.filename
        with open(output_path, "rb") as f:
            config = FlatReportConfig.model_validate(tomli.load(f))
        fifty_year_subsections = [s for s in config.subsections if s.index.startswith("2.6")]
        assert len(fifty_year_subsections) == 6
        assert fifty_year_subsections[0].type == "fifty_year_max_wind"
        assert fifty_year_subsections[0].title == "五十年一遇最大风速"
        for child in fifty_year_subsections[1:]:
            assert child.datasets == ["reconstruct_meso_filled_heights"], f"Expected datasets=['reconstruct_meso_filled_heights'] for {child.index}, got {child.datasets}"

    @patch(
        "cleanmast.subdomains.configuration.services.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    def test_rep_only_generates_rep_and_fifty_year_subsections(self, mock_calc_density, tmp_path):
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-representative-year.toml",
            "representative-year-fill-heights",
        )

        self._create_representative_year_toml(tmp_path)

        pc = ProjectConfig(tmp_path)
        dc = recommend_report(pc, repo=fake_repo)
        dc.write_to(tmp_path)
        output_path = tmp_path / dc.filename
        with open(output_path, "rb") as f:
            config = FlatReportConfig.model_validate(tomli.load(f))

        rep_subsections = [s for s in config.subsections if s.index.startswith("2.5")]
        fifty_year_subsections = [s for s in config.subsections if s.index.startswith("2.6")]
        assert len(rep_subsections) >= 1
        assert len(fifty_year_subsections) >= 1

        rep_parent = next(s for s in rep_subsections if s.index == "2.5")
        fifty_parent = next(s for s in fifty_year_subsections if s.index == "2.6")
        assert rep_parent.datasets == ["repyear"]
        assert fifty_parent.datasets == ["repyear"]

    @patch(
        "cleanmast.subdomains.configuration.services.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    def test_air_density_per_mast_in_dataset(self, mock_calc_density, tmp_path):
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
        )
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-representative-year.toml",
            "representative-year-fill-heights",
        )

        self._create_representative_year_toml(tmp_path)

        pc = ProjectConfig(tmp_path)
        dc = recommend_report(pc, repo=fake_repo)
        dc.write_to(tmp_path)
        output_path = tmp_path / dc.filename
        with open(output_path, "rb") as f:
            config = FlatReportConfig.model_validate(tomli.load(f))

        for ds in config.datasets:
            assert ds.masts is not None
            for mast in ds.masts:
                assert mast.air_density == 1.225

    @patch(
        "cleanmast.subdomains.configuration.services.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    def test_output_file_is_valid_toml_roundtrip(self, mock_calc_density, tmp_path):
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
        )
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-representative-year.toml",
            "representative-year-fill-heights",
        )

        self._create_representative_year_toml(tmp_path)

        pc = ProjectConfig(tmp_path)
        dc = recommend_report(pc, repo=fake_repo)
        dc.write_to(tmp_path)
        output_path = tmp_path / dc.filename
        with open(output_path, "rb") as f:
            config = FlatReportConfig.model_validate(tomli.load(f))

        assert config.datasets is not None
        assert len(config.datasets) > 0
        assert config.subsections is not None
        assert len(config.subsections) > 0

    @patch(
        "cleanmast.subdomains.configuration.services.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    def test_build_dataset_multi_mast_distinct_paths(
        self, mock_calc_density, tmp_path
    ):
        self._create_multi_mast_fill_heights_toml(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
        )

        import tomli
        with open(tmp_path / 'fill-heights-reconstruct-meso.toml', 'rb') as f:
            data = tomli.load(f)
        config = FillHeightsConfiguration(**data)
        dc = DiscoveredConfig(config=config, filename='fill-heights-reconstruct-meso.toml')
        windows = [AnalysisWindow(target_masts=["M1", "M2"], time_range=TR_A)]
        ds = _build_dataset_for_timeseries(
            tmp_path,
            dc,
            'reconstruct-meso-fill-heights',
            'reconstruct_meso_filled_heights',
            analysis_windows=windows,
            repo=fake_repo,
        )

        assert len(ds.masts) == 2
        assert ds.masts[0].input.data.endswith("M1.parquet")
        assert ds.masts[1].input.data.endswith("M2.parquet")
        assert ds.masts[0].input.data != ds.masts[1].input.data

    def test_raises_when_representative_year_toml_missing(self, tmp_path):
        """recommend_report raises FileNotFoundError when representative-year.toml is missing."""
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
        )
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-representative-year.toml",
            "representative-year-fill-heights",
        )
        # NO representative-year.toml
        pc = ProjectConfig(tmp_path)
        with pytest.raises(FileNotFoundError, match="representative-year.toml is required"):
            recommend_report(pc, repo=fake_repo)

    @patch(
        "cleanmast.subdomains.configuration.services.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    def test_raises_when_fill_heights_rep_year_toml_missing(self, mock_calc_density, tmp_path):
        """recommend_report raises FileNotFoundError when fill-heights-representative-year.toml is missing."""
        self._create_representative_year_toml(tmp_path)
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
        )
        # NO fill-heights-representative-year.toml
        pc = ProjectConfig(tmp_path)
        with pytest.raises(FileNotFoundError, match="fill-heights-representative-year.toml is required"):
            recommend_report(pc, repo=fake_repo)

    @patch(
        "cleanmast.subdomains.configuration.services.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    def test_meso_datasets_have_analysis_windows(self, mock_calc_density, tmp_path):
        """Meso datasets (filled + original) carry analysis_windows matching their mast names."""
        self._create_representative_year_toml(tmp_path)
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
        )
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-representative-year.toml",
            "representative-year-fill-heights",
        )

        pc = ProjectConfig(tmp_path)
        dc = recommend_report(pc, repo=fake_repo)
        dc.write_to(tmp_path)
        with open(tmp_path / dc.filename, "rb") as f:
            config = FlatReportConfig.model_validate(tomli.load(f))

        filled_meso_ds = next(ds for ds in config.datasets if ds.name == "reconstruct_meso_filled_heights")
        assert len(filled_meso_ds.analysis_windows) >= 1
        meso_mast_names = {aw_mast for aw in filled_meso_ds.analysis_windows for aw_mast in aw.target_masts}
        assert "M1" in meso_mast_names

        repyear_ds = next(ds for ds in config.datasets if ds.name == "repyear")
        assert len(repyear_ds.analysis_windows) >= 1
        repyear_mast_names = {aw_mast for aw in repyear_ds.analysis_windows for aw_mast in aw.target_masts}
        assert "M1" in repyear_mast_names

    @patch(
        "cleanmast.subdomains.configuration.services.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    def test_calibration_dataset_windows_cover_filled_meso_masts(
        self, mock_calc_density, tmp_path
    ):
        """Calibration dataset windows cover filled-meso masts, not blindly repyear windows."""
        self._create_representative_year_toml(tmp_path)
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
        )
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-representative-year.toml",
            "representative-year-fill-heights",
        )

        pc = ProjectConfig(tmp_path)
        dc = recommend_report(pc, repo=fake_repo)
        dc.write_to(tmp_path)
        with open(tmp_path / dc.filename, "rb") as f:
            config = FlatReportConfig.model_validate(tomli.load(f))

        cal_ds = next(ds for ds in config.datasets if ds.name == "receive_repyear_calibration_input")
        assert len(cal_ds.analysis_windows) >= 1
        # calibration windows should cover ONLY the filled-meso mast "M1"
        cal_mast_names = {aw_mast for aw in cal_ds.analysis_windows for aw_mast in aw.target_masts}
        assert cal_mast_names == {"M1"}

    @patch(
        "cleanmast.subdomains.configuration.services.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    def test_mast_in_meso_but_absent_from_rep_year_raises(self, mock_calc_density, tmp_path):
        """Mast present in meso dataset but absent from rep-year → ValueError from coverage validator."""
        # representative-year.toml has mast "OtherMast", not "M1"
        self._create_representative_year_toml(tmp_path, mast_names=["OtherMast"])
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
        )
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-representative-year.toml",
            "representative-year-fill-heights",
        )

        pc = ProjectConfig(tmp_path)
        with pytest.raises(ValueError, match="analysis_windows must contain at least one window"):
            recommend_report(pc, repo=fake_repo)


class TestOriginalHeightsDataset:
    def _create_reconstruct_meso_toml(self, tmp_path: Path, data_dir: str = "reconstruct-meso") -> None:
        config = {
            "masts": [_valid_reconstruct_meso_mast("M1", data_dir)],
            "mesos": [{"name": "ERA5", "input": {"data": "raw/ERA5.csv"}}],
        }
        import tomli_w
        with open(tmp_path / "reconstruct-meso.toml", "wb") as f:
            tomli_w.dump(config, f)

        parquet_path = tmp_path / data_dir / "M1.parquet"
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        parquet_path.write_bytes(b"")

    def _create_fill_heights_toml(self, tmp_path: Path, filename: str, data_dir: str) -> None:
        config = {"masts": [_valid_mast("M1", data_dir)]}
        import tomli_w
        with open(tmp_path / filename, "wb") as f:
            tomli_w.dump(config, f)

        parquet_path = tmp_path / data_dir / "M1.parquet"
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        parquet_path.write_bytes(b"")

    def _create_representative_year_toml(
        self, tmp_path: Path, mast_names: list[str] | None = None, tr: TimeRange | None = None
    ) -> None:
        """Create representative-year.toml with given mast names and time range."""
        if mast_names is None:
            mast_names = ["M1"]
        if tr is None:
            tr = TR_A

        masts = []
        for name in mast_names:
            masts.append({
                "name": name,
                "input": {"data": "/dev/null"},
                "output": {"data": "/dev/null"},
                "time_range": {"min": tr.min, "max": tr.max},
                "meso_model": {
                    "method": "16-sector",
                    "meso_name": "ERA5",
                    "model_file": "model.jld2",
                },
            })
        config = {
            "masts": masts,
            "mesos": [{"name": "ERA5", "input": {"data": "raw/ERA5.csv"}}],
        }
        import tomli_w
        with open(tmp_path / "representative-year.toml", "wb") as f:
            tomli_w.dump(config, f)

    @patch(
        "cleanmast.subdomains.configuration.services.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    def test_original_heights_dataset_built_and_assigned(
        self, mock_calc_density, tmp_path
    ):
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
        )
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-representative-year.toml",
            "representative-year-fill-heights",
        )
        self._create_reconstruct_meso_toml(tmp_path)

        self._create_representative_year_toml(tmp_path)

        pc = ProjectConfig(tmp_path)
        dc = recommend_report(pc, repo=fake_repo)
        dc.write_to(tmp_path)
        with open(tmp_path / dc.filename, "rb") as f:
            config = FlatReportConfig.model_validate(tomli.load(f))

        dataset_names = [ds.name for ds in config.datasets]
        assert "reconstruct_meso_filled_heights" in dataset_names
        assert "reconstruct_meso_original_heights" in dataset_names
        assert len(config.datasets) == 4  # filled + repyear + original + calibration

        by_index = {s.index: s for s in config.subsections}
        assert by_index["2.4.4"].type == "vertical_profile"
        assert by_index["2.4.4"].datasets == ["reconstruct_meso_original_heights"]
        assert by_index["2.4.7"].type == "turbulence"
        assert by_index["2.4.7"].datasets == ["reconstruct_meso_original_heights"]
        for idx in ("2.4.1", "2.4.2", "2.4.3", "2.4.5", "2.4.6"):
            assert by_index[idx].datasets == ["reconstruct_meso_filled_heights"], (
                f"Expected filled-heights dataset for {idx}, got {by_index[idx].datasets}"
            )

        original_ds = next(
            ds for ds in config.datasets if ds.name == "reconstruct_meso_original_heights"
        )
        assert len(original_ds.masts) == 1
        # Original dataset references reconstruct-meso parquet directly (no path rewrite)
        assert original_ds.masts[0].input.data == "reconstruct-meso/M1.parquet"
        assert original_ds.masts[0].air_density == 1.225

    @patch(
        "cleanmast.subdomains.configuration.services.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    def test_turbulence_and_vertical_profile_fall_back_to_filled(
        self, mock_calc_density, tmp_path
    ):
        """Without reconstruct-meso.toml, 2.4.4 and 2.4.7 use the filled-heights dataset."""
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
        )
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-representative-year.toml",
            "representative-year-fill-heights",
        )

        self._create_representative_year_toml(tmp_path)

        pc = ProjectConfig(tmp_path)
        dc = recommend_report(pc, repo=fake_repo)
        dc.write_to(tmp_path)
        with open(tmp_path / dc.filename, "rb") as f:
            config = FlatReportConfig.model_validate(tomli.load(f))

        dataset_names = [ds.name for ds in config.datasets]
        assert "reconstruct_meso_original_heights" not in dataset_names

        by_index = {s.index: s for s in config.subsections}
        assert by_index["2.4.4"].datasets == ["reconstruct_meso_filled_heights"]
        assert by_index["2.4.7"].datasets == ["reconstruct_meso_filled_heights"]
