from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import tomli_w
from cleanmast.application.usecases.generate_report import generate_report


class TestGenerateReport:
    def _create_nested_config(self, tmp_path: Path) -> Path:
        config = {
            "document": {
                "section": [
                    {
                        "title": "风资源分析",
                        "subsections": [
                            {
                                "type": "timeseries",
                                "title": "测风年风资源分析",
                                "masts": [
                                    {"name": "M1", "air_density": 1.225, "input": {"data": "./meso/M1.parquet"}}
                                ],
                                "subsections": [
                                    {"type": "wind_rose"},
                                    {"type": "temporal"},
                                ],
                            },
                            {
                                "type": "timeseries",
                                "title": "代表年风资源分析",
                                "masts": [
                                    {"name": "M1", "air_density": 1.225, "input": {"data": "./rep/M1.parquet"}}
                                ],
                                "subsections": [
                                    {"type": "wind_rose"},
                                    {"type": "temporal"},
                                ],
                            },
                        ],
                    }
                ]
            }
        }
        path = tmp_path / "rep-ts-report.toml"
        with open(path, "wb") as f:
            tomli_w.dump(config, f)
        return path

    def _create_five_subsection_config(self, tmp_path: Path, mast_count: int) -> Path:
        masts = [
            {"name": f"M{i + 1}", "air_density": 1.225, "input": {"data": f"./M{i + 1}.parquet"}}
            for i in range(mast_count)
        ]
        config = {
            "document": {
                "section": [
                    {
                        "title": "风资源分析",
                        "subsections": [
                            {
                                "type": "timeseries",
                                "title": "测风年风资源分析",
                                "masts": masts,
                                "subsections": [
                                    {"type": "wind_frequency"},
                                    {"type": "temporal"},
                                    {"type": "weibull"},
                                    {"type": "vertical_profile"},
                                    {"type": "turbulence"},
                                ],
                            }
                        ],
                    }
                ]
            }
        }
        path = tmp_path / "rep-ts-report.toml"
        with open(path, "wb") as f:
            tomli_w.dump(config, f)
        return path

    @patch("cleanmast.application.usecases.generate_report.ReportBuilder")
    @patch("cleanmast.application.usecases.generate_report.ReportGenerationService")
    @patch("cleanmast.application.usecases.generate_report.load_timeseries")
    def test_processes_nested_timeseries(self, mock_load_ts, mock_service_cls, mock_builder_cls, tmp_path):
        mock_ts = MagicMock()
        wd_sensor = MagicMock()
        wd_sensor.sensor_type = "WindDirection"
        wd_sensor.stat_type = "avg"
        mock_ts.sensors = [wd_sensor]
        mock_load_ts.return_value = mock_ts

        mock_service = MagicMock()
        mock_service.generate_wind_rose_section.return_value = "wind_rose_section"
        mock_service.generate_temporal_section.return_value = "temporal_section"
        mock_service._create_analysis_input.return_value = "analysis_input"
        mock_service_cls.return_value = mock_service

        mock_builder = MagicMock()
        mock_builder.build.return_value = {
            "typ": Path("report.typ"),
            "pdf": Path("report.pdf"),
            "docx": Path("report.docx"),
        }
        mock_builder_cls.return_value = mock_builder

        config_path = self._create_nested_config(tmp_path)
        result = generate_report(str(config_path))

        assert result["pdf"] == Path("report.pdf")
        assert mock_load_ts.call_count == 2
        assert mock_service.generate_wind_rose_section.call_count == 2
        assert mock_service.generate_temporal_section.call_count == 2
        assert mock_builder.add_section.call_count == 2

        # Assert multi-mast contract: each call receives a list of tuples
        for call in mock_service.generate_wind_rose_section.call_args_list:
            items = call.args[0]
            assert isinstance(items, list)
            assert len(items) == 1
            assert len(items[0]) == 2

    @patch("cleanmast.application.usecases.generate_report.ReportBuilder")
    @patch("cleanmast.application.usecases.generate_report.ReportGenerationService")
    @patch("cleanmast.application.usecases.generate_report.load_timeseries")
    def test_three_mast_config_produces_five_sections(self, mock_load_ts, mock_service_cls, mock_builder_cls, tmp_path):
        mock_ts = MagicMock()
        mock_ts.sensors = []
        mock_load_ts.return_value = mock_ts

        mock_service = MagicMock()
        mock_service.generate_wind_frequency_section.return_value = "wind_frequency_section"
        mock_service.generate_temporal_section.return_value = "temporal_section"
        mock_service.generate_weibull_section.return_value = "weibull_section"
        mock_service.generate_vertical_profile_section.return_value = "vertical_profile_section"
        mock_service.generate_turbulence_section.return_value = "turbulence_section"
        mock_service._create_analysis_input.return_value = "analysis_input"
        mock_service_cls.return_value = mock_service

        mock_builder = MagicMock()
        mock_builder.build.return_value = {
            "typ": Path("report.typ"),
            "pdf": Path("report.pdf"),
            "docx": Path("report.docx"),
        }
        mock_builder_cls.return_value = mock_builder

        config_path = self._create_five_subsection_config(tmp_path, mast_count=3)
        result = generate_report(str(config_path))

        assert result["pdf"] == Path("report.pdf")
        assert mock_load_ts.call_count == 3

        # Each service method called exactly once (multi-mast)
        assert mock_service.generate_wind_frequency_section.call_count == 1
        assert mock_service.generate_temporal_section.call_count == 1
        assert mock_service.generate_weibull_section.call_count == 1
        assert mock_service.generate_vertical_profile_section.call_count == 1
        assert mock_service.generate_turbulence_section.call_count == 1

        assert mock_builder.add_section.call_count == 1

        # Assert each service method receives exactly 3 mast tuples
        assert len(mock_service.generate_wind_frequency_section.call_args.args[0]) == 3
        assert len(mock_service.generate_temporal_section.call_args.args[0]) == 3
        assert len(mock_service.generate_weibull_section.call_args.args[0]) == 3
        assert len(mock_service.generate_vertical_profile_section.call_args.args[0]) == 3
        assert len(mock_service.generate_turbulence_section.call_args.args[0]) == 3

    @patch("cleanmast.application.usecases.generate_report.ReportBuilder")
    @patch("cleanmast.application.usecases.generate_report.ReportGenerationService")
    @patch("cleanmast.application.usecases.generate_report.load_timeseries")
    def test_one_mast_config_produces_five_sections(self, mock_load_ts, mock_service_cls, mock_builder_cls, tmp_path):
        mock_ts = MagicMock()
        mock_ts.sensors = []
        mock_load_ts.return_value = mock_ts

        mock_service = MagicMock()
        mock_service.generate_wind_frequency_section.return_value = "wind_frequency_section"
        mock_service.generate_temporal_section.return_value = "temporal_section"
        mock_service.generate_weibull_section.return_value = "weibull_section"
        mock_service.generate_vertical_profile_section.return_value = "vertical_profile_section"
        mock_service.generate_turbulence_section.return_value = "turbulence_section"
        mock_service._create_analysis_input.return_value = "analysis_input"
        mock_service_cls.return_value = mock_service

        mock_builder = MagicMock()
        mock_builder.build.return_value = {
            "typ": Path("report.typ"),
            "pdf": Path("report.pdf"),
            "docx": Path("report.docx"),
        }
        mock_builder_cls.return_value = mock_builder

        config_path = self._create_five_subsection_config(tmp_path, mast_count=1)
        result = generate_report(str(config_path))

        assert result["pdf"] == Path("report.pdf")
        assert mock_load_ts.call_count == 1

        # Each service method called exactly once (backward compatible structure)
        assert mock_service.generate_wind_frequency_section.call_count == 1
        assert mock_service.generate_temporal_section.call_count == 1
        assert mock_service.generate_weibull_section.call_count == 1
        assert mock_service.generate_vertical_profile_section.call_count == 1
        assert mock_service.generate_turbulence_section.call_count == 1

        assert mock_builder.add_section.call_count == 1

        # Assert each service method receives exactly 1 mast tuple
        assert len(mock_service.generate_wind_frequency_section.call_args.args[0]) == 1
        assert len(mock_service.generate_temporal_section.call_args.args[0]) == 1
        assert len(mock_service.generate_weibull_section.call_args.args[0]) == 1
        assert len(mock_service.generate_vertical_profile_section.call_args.args[0]) == 1
        assert len(mock_service.generate_turbulence_section.call_args.args[0]) == 1

    @patch("cleanmast.application.usecases.generate_report.ReportBuilder")
    @patch("cleanmast.application.usecases.generate_report.ReportGenerationService")
    @patch("cleanmast.application.usecases.generate_report.load_timeseries")
    def test_rejects_non_timeseries_at_section_level(self, mock_load_ts, mock_service_cls, mock_builder_cls, tmp_path):
        config = {
            "document": {
                "section": [
                    {
                        "title": "风资源分析",
                        "subsections": [
                            {"type": "wind_rose"},
                        ],
                    }
                ]
            }
        }
        path = tmp_path / "rep-ts-report-bad.toml"
        with open(path, "wb") as f:
            tomli_w.dump(config, f)

        with pytest.raises(ValueError, match="Document sections may only contain container subsections"):
            generate_report(str(path))

    @patch("cleanmast.application.usecases.generate_report.RepTsReportConfig")
    @patch("cleanmast.application.usecases.generate_report.ReportBuilder")
    @patch("cleanmast.application.usecases.generate_report.ReportGenerationService")
    @patch("cleanmast.application.usecases.generate_report.load_timeseries")
    def test_skips_timeseries_without_masts(self, mock_load_ts, mock_service_cls, mock_builder_cls, mock_config_cls, tmp_path):
        mock_ts = MagicMock()
        wd_sensor = MagicMock()
        wd_sensor.sensor_type = "WindDirection"
        wd_sensor.stat_type = "avg"
        mock_ts.sensors = [wd_sensor]
        mock_load_ts.return_value = mock_ts

        mock_service = MagicMock()
        mock_service.generate_wind_rose_section.return_value = "wind_rose_section"
        mock_service._create_analysis_input.return_value = "analysis_input"
        mock_service_cls.return_value = mock_service

        mock_builder = MagicMock()
        mock_builder.build.return_value = {
            "typ": Path("report.typ"),
            "pdf": Path("report.pdf"),
            "docx": Path("report.docx"),
        }
        mock_builder_cls.return_value = mock_builder

        mock_subsection_with_masts = MagicMock()
        mock_subsection_with_masts.type = "timeseries"
        mock_mast = MagicMock()
        mock_mast.name = "M1"
        mock_mast.air_density = 1.225
        mock_mast.input = {"data": "./M1.parquet"}
        mock_subsection_with_masts.masts = [mock_mast]
        mock_leaf = MagicMock()
        mock_leaf.type = "wind_rose"
        mock_subsection_with_masts.subsections = [mock_leaf]

        mock_subsection_no_masts = MagicMock()
        mock_subsection_no_masts.type = "timeseries"
        mock_subsection_no_masts.masts = []
        mock_subsection_no_masts.subsections = [MagicMock(type="temporal")]

        mock_section = MagicMock()
        mock_section.title = "风资源分析"
        mock_section.subsections = [mock_subsection_with_masts, mock_subsection_no_masts]

        mock_config = MagicMock()
        mock_config.document.sections = [mock_section]
        mock_config_cls.from_toml.return_value = mock_config

        config_path = tmp_path / "rep-ts-report.toml"
        config_path.touch()

        result = generate_report(str(config_path))

        assert result["pdf"] == Path("report.pdf")
        assert mock_load_ts.call_count == 1
        assert mock_service.generate_wind_rose_section.call_count == 1
        assert mock_builder.add_section.call_count == 1

    @patch("cleanmast.application.usecases.generate_report.ReportBuilder")
    @patch("cleanmast.application.usecases.generate_report.ReportGenerationService")
    @patch("cleanmast.application.usecases.generate_report.load_timeseries")
    def test_nested_subsections_render_with_correct_heading_levels(self, mock_load_ts, mock_service_cls, mock_builder_cls, tmp_path):
        from cleanmast.application.usecases.generate_report import HeadingSection
        from typst_ir import TypstDocument, TypstHeading, TypstSection, serialize

        mock_ts = MagicMock()
        mock_ts.sensors = []
        mock_load_ts.return_value = mock_ts

        class FakeSection:
            def __init__(self, title: str) -> None:
                self.title = title

            def render_ir(self, images_dir: Path) -> TypstSection:
                return TypstSection(heading=TypstHeading(text=self.title), body=[], subsections=[])

        mock_service = MagicMock()
        mock_service.generate_wind_rose_section.return_value = FakeSection("Wind Rose")
        mock_service.generate_vertical_profile_section.return_value = FakeSection("Vertical Profile")
        mock_service._create_analysis_input.return_value = "analysis_input"
        mock_service_cls.return_value = mock_service

        mock_builder = MagicMock()
        mock_builder.build.return_value = {
            "typ": Path("report.typ"),
            "pdf": Path("report.pdf"),
            "docx": Path("report.docx"),
        }
        mock_builder_cls.return_value = mock_builder

        config = {
            "document": {
                "section": [
                    {
                        "title": "风资源分析",
                        "subsections": [
                            {
                                "type": "timeseries",
                                "title": "测风年风资源分析",
                                "masts": [
                                    {"name": "M1", "air_density": 1.225, "input": {"data": "./M1.parquet"}}
                                ],
                                "subsections": [
                                    {"type": "wind_rose"},
                                    {"type": "vertical_profile"},
                                ],
                            }
                        ],
                    }
                ]
            }
        }
        path = tmp_path / "rep-ts-report.toml"
        with open(path, "wb") as f:
            tomli_w.dump(config, f)

        result = generate_report(str(path))
        assert result["pdf"] == Path("report.pdf")

        added_sections = [call.args[0] for call in mock_builder.add_section.call_args_list]
        heading_sections = [s for s in added_sections if isinstance(s, HeadingSection)]
        assert len(heading_sections) == 1

        heading_ir = heading_sections[0].render_ir(tmp_path)
        assert len(heading_ir.subsections) > 0, "Parent HeadingSection should contain nested subsections"

        doc = TypstDocument(children=[heading_ir])
        serialized = serialize(doc)
        assert "== " in serialized, "Serialized output should contain == markers for child headings"

    def test_config_not_found_raises_error(self, tmp_path):
        missing_path = tmp_path / "nonexistent.toml"
        with pytest.raises(FileNotFoundError):
            generate_report(str(missing_path))
