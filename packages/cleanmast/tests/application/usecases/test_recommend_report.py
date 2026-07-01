from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from cleanmast.application.usecases.recommend_report import (
    _build_analysis_windows,
    _build_dataset_for_timeseries,
    recommend_report,
)
from cleanmast.subdomains.configuration.value_objects.representative_year import (
    RepresentativeYearMast,
    RepresentativeYearMesoModel,
)
from cleanmast.subdomains.dataingestion.value_objects.time_range import TimeRange
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)
from cleanmast.subdomains.reporting.model.report_config import (
    FlatReportConfig,
)

TR_A = TimeRange(min=datetime(2025, 3, 1), max=datetime(2026, 2, 28))
TR_B = TimeRange(min=datetime(2024, 1, 1), max=datetime(2024, 12, 31))


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

    @patch(
        "cleanmast.application.usecases.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    @patch(
        "cleanmast.application.usecases.recommend_report.load_timeseries_parquet",
        return_value=MagicMock(),
    )
    def test_generates_flat_format_with_datasets_catalog(self, mock_load_parquet, mock_calc_density, tmp_path):
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

        output_path = recommend_report(str(tmp_path))

        assert output_path.exists()
        assert output_path.name == "rep-ts-report.toml"

        config = FlatReportConfig.from_toml(output_path)
        assert len(config.datasets) == 3

        reconstruct_meso_ds = next(ds for ds in config.datasets if ds.name == "reconstruct_meso")
        repyear_ds = next(ds for ds in config.datasets if ds.name == "repyear")
        assert len(reconstruct_meso_ds.masts) == 1
        assert len(repyear_ds.masts) == 1
        assert reconstruct_meso_ds.masts[0].air_density == 1.225
        assert repyear_ds.masts[0].air_density == 1.225

    @patch(
        "cleanmast.application.usecases.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    @patch(
        "cleanmast.application.usecases.recommend_report.load_timeseries_parquet",
        return_value=MagicMock(),
    )
    def test_meso_subsection_indices_and_ordering(self, mock_load_parquet, mock_calc_density, tmp_path):
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

        output_path = recommend_report(str(tmp_path))
        config = FlatReportConfig.from_toml(output_path)

        meso_subsections = [s for s in config.subsections if s.index.startswith("2.4")]
        assert len(meso_subsections) == 8
        assert meso_subsections[0].type == "timeseries"
        assert meso_subsections[0].title == "测风年风资源分析"
        for child in meso_subsections[1:]:
            assert child.datasets == ["reconstruct_meso"], f"Expected datasets=['reconstruct_meso'] for {child.index}, got {child.datasets}"

    @patch(
        "cleanmast.application.usecases.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    @patch(
        "cleanmast.application.usecases.recommend_report.load_timeseries_parquet",
        return_value=MagicMock(),
    )
    def test_rep_subsection_indices_and_ordering(self, mock_load_parquet, mock_calc_density, tmp_path):
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

        output_path = recommend_report(str(tmp_path))
        config = FlatReportConfig.from_toml(output_path)

        rep_subsections = [s for s in config.subsections if s.index.startswith("2.5")]
        assert len(rep_subsections) == 6
        assert rep_subsections[0].type == "timeseries"
        for child in rep_subsections[1:]:
            if child.index == "2.5.1":
                assert child.datasets == ["repyear_calibration"]
            else:
                assert child.datasets == ["repyear"], f"Expected datasets=['repyear'] for {child.index}, got {child.datasets}"

    @patch(
        "cleanmast.application.usecases.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    @patch(
        "cleanmast.application.usecases.recommend_report.load_timeseries_parquet",
        return_value=MagicMock(),
    )
    def test_fifty_year_subsection_indices_and_ordering(self, mock_load_parquet, mock_calc_density, tmp_path):
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

        output_path = recommend_report(str(tmp_path))
        config = FlatReportConfig.from_toml(output_path)
        fifty_year_subsections = [s for s in config.subsections if s.index.startswith("2.6")]
        assert len(fifty_year_subsections) == 6
        assert fifty_year_subsections[0].type == "fifty_year_max_wind"
        assert fifty_year_subsections[0].title == "五十年一遇最大风速"
        for child in fifty_year_subsections[1:]:
            assert child.datasets == ["reconstruct_meso"], f"Expected datasets=['reconstruct_meso'] for {child.index}, got {child.datasets}"

    @patch(
        "cleanmast.application.usecases.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    @patch(
        "cleanmast.application.usecases.recommend_report.load_timeseries_parquet",
        return_value=MagicMock(),
    )
    def test_rep_only_generates_rep_and_fifty_year_subsections(self, mock_load_parquet, mock_calc_density, tmp_path):
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-representative-year.toml",
            "representative-year-fill-heights",
        )

        output_path = recommend_report(str(tmp_path))
        config = FlatReportConfig.from_toml(output_path)

        rep_subsections = [s for s in config.subsections if s.index.startswith("2.5")]
        fifty_year_subsections = [s for s in config.subsections if s.index.startswith("2.6")]
        assert len(rep_subsections) >= 1
        assert len(fifty_year_subsections) >= 1

        rep_parent = next(s for s in rep_subsections if s.index == "2.5")
        fifty_parent = next(s for s in fifty_year_subsections if s.index == "2.6")
        assert rep_parent.datasets == ["repyear"]
        assert fifty_parent.datasets == ["repyear"]

    @patch(
        "cleanmast.application.usecases.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    @patch(
        "cleanmast.application.usecases.recommend_report.load_timeseries_parquet",
        return_value=MagicMock(),
    )
    def test_air_density_per_mast_in_dataset(self, mock_load_parquet, mock_calc_density, tmp_path):
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

        output_path = recommend_report(str(tmp_path))
        config = FlatReportConfig.from_toml(output_path)

        for ds in config.datasets:
            assert ds.masts is not None
            for mast in ds.masts:
                assert mast.air_density == 1.225

    @patch(
        "cleanmast.application.usecases.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    @patch(
        "cleanmast.application.usecases.recommend_report.load_timeseries_parquet",
        return_value=MagicMock(),
    )
    def test_output_file_is_valid_toml_roundtrip(self, mock_load_parquet, mock_calc_density, tmp_path):
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

        output_path = recommend_report(str(tmp_path))
        config = FlatReportConfig.from_toml(output_path)

        assert config.datasets is not None
        assert len(config.datasets) > 0
        assert config.subsections is not None
        assert len(config.subsections) > 0

    @patch(
        "cleanmast.application.usecases.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    @patch(
        "cleanmast.application.usecases.recommend_report.load_timeseries_parquet",
        return_value=MagicMock(),
    )
    def test_build_dataset_multi_mast_distinct_paths(
        self, mock_load_parquet, mock_calc_density, tmp_path
    ):
        self._create_multi_mast_fill_heights_toml(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
        )

        ds = _build_dataset_for_timeseries(
            tmp_path,
            "fill-heights-reconstruct-meso.toml",
            "reconstruct-meso-fill-heights",
            "reconstruct_meso",
        )

        assert len(ds.masts) == 2
        assert ds.masts[0].input.data.endswith("M1.parquet")
        assert ds.masts[1].input.data.endswith("M2.parquet")
        assert ds.masts[0].input.data != ds.masts[1].input.data
