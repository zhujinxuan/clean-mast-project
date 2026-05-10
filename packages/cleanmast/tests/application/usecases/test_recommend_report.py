from pathlib import Path
from unittest.mock import MagicMock, patch

from cleanmast.application.usecases.recommend_report import (
    _build_dataset_for_timeseries,
    recommend_report,
)

from cleanmast.subdomains.assessment.domain.value_objects.flat_report_config import (
    FlatReportConfig,
)


class TestRecommendReport:
    def _create_fill_heights_toml(self, tmp_path: Path, filename: str, data_dir: str) -> None:
        config = {
            "masts": [
                {
                    "name": "M1",
                    "output": {"data": f"{data_dir}/M1.parquet"},
                }
            ]
        }
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
                {
                    "name": "M1",
                    "output": {"data": f"{data_dir}/M1.parquet"},
                },
                {
                    "name": "M2",
                    "output": {"data": f"{data_dir}/M2.parquet"},
                },
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

        config = FlatReportConfig.from_toml(output_path)

        assert len(config.datasets) == 2
        dataset_names = [ds.name for ds in config.datasets]
        assert "meso" in dataset_names
        assert "repyear" in dataset_names

        meso_ds = next(ds for ds in config.datasets if ds.name == "meso")
        assert meso_ds.path == "./reconstruct-meso-fill-heights/M1.parquet"
        assert len(meso_ds.masts) == 1
        assert meso_ds.masts[0].name == "M1"
        assert meso_ds.masts[0].air_density == 1.225

        repyear_ds = next(ds for ds in config.datasets if ds.name == "repyear")
        assert repyear_ds.path == "./representative-year-fill-heights/M1.parquet"
        assert len(repyear_ds.masts) == 1
        assert repyear_ds.masts[0].name == "M1"
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

        meso_parent = next((s for s in config.subsections if s.index == "2.4"), None)
        assert meso_parent is not None
        assert meso_parent.type == "timeseries"
        assert meso_parent.title == "测风年风资源分析"
        assert meso_parent.datasets == ["meso"]

        meso_children = [s for s in config.subsections if s.index.startswith("2.4.")]
        assert len(meso_children) == 7
        expected_order = [
            ("2.4.1", "air_density"),
            ("2.4.2", "temporal"),
            ("2.4.3", "wind_rose"),
            ("2.4.4", "vertical_profile"),
            ("2.4.5", "wind_frequency"),
            ("2.4.6", "weibull"),
            ("2.4.7", "turbulence"),
        ]
        actual_order = [(s.index, s.type) for s in sorted(meso_children, key=lambda s: s.index)]
        assert actual_order == expected_order

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

        rep_parent = next((s for s in config.subsections if s.index == "2.5"), None)
        assert rep_parent is not None
        assert rep_parent.type == "timeseries"
        assert rep_parent.title == "代表年风资源分析"
        assert rep_parent.datasets == ["repyear"]

        rep_children = [s for s in config.subsections if s.index.startswith("2.5.")]
        assert len(rep_children) == 5
        expected_order = [
            ("2.5.1", "representative_year_calibration"),
            ("2.5.2", "temporal"),
            ("2.5.3", "wind_rose"),
            ("2.5.4", "wind_frequency"),
            ("2.5.5", "weibull"),
        ]
        actual_order = [(s.index, s.type) for s in sorted(rep_children, key=lambda s: s.index)]
        assert actual_order == expected_order

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

        fifty_parent = next((s for s in config.subsections if s.index == "2.6"), None)
        assert fifty_parent is not None
        assert fifty_parent.type == "fifty_year_max_wind"
        assert fifty_parent.title == "五十年一遇最大风速"
        assert fifty_parent.datasets == ["meso"]

        fifty_children = [s for s in config.subsections if s.index.startswith("2.6.")]
        assert len(fifty_children) == 5
        expected_order = [
            ("2.6.1", "iec_standards"),
            ("2.6.2", "fifty_year_method1"),
            ("2.6.3", "fifty_year_method2"),
            ("2.6.4", "fifty_year_method3"),
            ("2.6.5", "fifty_year_summary"),
        ]
        actual_order = [(s.index, s.type) for s in sorted(fifty_children, key=lambda s: s.index)]
        assert actual_order == expected_order

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

        dataset_names = [ds.name for ds in config.datasets]
        assert "meso" not in dataset_names
        assert "repyear" in dataset_names

        indices = [s.index for s in config.subsections]
        assert "2.4" not in indices
        assert "2.5" in indices
        assert "2.6" in indices

        rep_parent = next((s for s in config.subsections if s.index == "2.5"), None)
        assert rep_parent is not None
        assert rep_parent.datasets == ["repyear"]

        fifty_parent = next((s for s in config.subsections if s.index == "2.6"), None)
        assert fifty_parent is not None
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
        assert len(config.datasets) > 0
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
            "meso",
        )

        assert len(ds.masts) == 2
        assert ds.masts[0].input.data.endswith("M1.parquet")
        assert ds.masts[1].input.data.endswith("M2.parquet")
        assert ds.masts[0].input.data != ds.masts[1].input.data
