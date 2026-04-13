from pathlib import Path
from unittest.mock import MagicMock, patch

import tomli
from cleanmast.application.usecases.recommend_report import recommend_report


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

    @patch(
        "cleanmast.application.usecases.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    @patch(
        "cleanmast.application.usecases.recommend_report.load_timeseries_parquet",
        return_value=MagicMock(),
    )
    def test_meso_subsection_ordering(self, mock_load_parquet, mock_calc_density, tmp_path):
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

        with open(output_path, "rb") as f:
            config = tomli.load(f)

        sections = config["document"]["section"]
        assert len(sections) == 1
        subsections = sections[0]["subsections"]

        meso_subsection = next(
            (s for s in subsections if s.get("title") == "测风年风资源分析"), None
        )
        assert meso_subsection is not None
        expected_meso_order = [
            "air_density",
            "temporal",
            "wind_rose",
            "vertical_profile",
            "wind_frequency",
            "weibull",
            "turbulence",
        ]
        actual_meso_order = [s["type"] for s in meso_subsection["subsections"]]
        assert actual_meso_order == expected_meso_order

    @patch(
        "cleanmast.application.usecases.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    @patch(
        "cleanmast.application.usecases.recommend_report.load_timeseries_parquet",
        return_value=MagicMock(),
    )
    def test_rep_subsection_ordering(self, mock_load_parquet, mock_calc_density, tmp_path):
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

        with open(output_path, "rb") as f:
            config = tomli.load(f)

        sections = config["document"]["section"]
        assert len(sections) == 1
        subsections = sections[0]["subsections"]

        rep_subsection = next(
            (s for s in subsections if s.get("title") == "代表年风资源分析"), None
        )
        assert rep_subsection is not None
        expected_rep_order = [
            "representative_year_calibration",
            "temporal",
            "wind_rose",
            "wind_frequency",
            "weibull",
        ]
        actual_rep_order = [s["type"] for s in rep_subsection["subsections"]]
        assert actual_rep_order == expected_rep_order

    @patch(
        "cleanmast.application.usecases.recommend_report.calculate_air_density",
        return_value=1.225,
    )
    @patch(
        "cleanmast.application.usecases.recommend_report.load_timeseries_parquet",
        return_value=MagicMock(),
    )
    def test_rep_only_generates_rep_subsection(self, mock_load_parquet, mock_calc_density, tmp_path):
        self._create_fill_heights_toml(
            tmp_path,
            "fill-heights-representative-year.toml",
            "representative-year-fill-heights",
        )

        output_path = recommend_report(str(tmp_path))

        with open(output_path, "rb") as f:
            config = tomli.load(f)

        sections = config["document"]["section"]
        subsections = sections[0]["subsections"]

        titles = [s.get("title") for s in subsections]
        assert "测风年风资源分析" not in titles
        assert "代表年风资源分析" in titles

        rep_subsection = next(
            (s for s in subsections if s.get("title") == "代表年风资源分析"), None
        )
        expected_rep_order = [
            "representative_year_calibration",
            "temporal",
            "wind_rose",
            "wind_frequency",
            "weibull",
        ]
        actual_rep_order = [s["type"] for s in rep_subsection["subsections"]]
        assert actual_rep_order == expected_rep_order
