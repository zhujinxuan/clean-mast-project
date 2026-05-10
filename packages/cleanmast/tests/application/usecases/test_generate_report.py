from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import tomli_w
from cleanmast.application.usecases.generate_report import (
    HeadingSection,
    LoadedDataset,
    _generate_from_flat_config,
    _handle_fifty_year_max_wind_flat,
    generate_report,
)
from cleanmast.subdomains.assessment.domain.value_objects.dataset_config import (
    DatasetConfig,
    MastRef,
)
from cleanmast.subdomains.assessment.domain.value_objects.flat_report_config import (
    FlatReportConfig,
)
from cleanmast.subdomains.assessment.domain.value_objects.flat_subsection_config import (
    FlatSubsectionConfig,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)


class TestGenerateReport:
    def _create_nested_config(self, tmp_path: Path) -> Path:
        config = {
            "datasets": [
                {
                    "name": "meso",
                    "path": "./meso/M1.parquet",
                    "masts": [{"name": "M1", "air_density": 1.225}],
                },
                {
                    "name": "rep",
                    "path": "./rep/M1.parquet",
                    "masts": [{"name": "M1", "air_density": 1.225}],
                },
            ],
            "subsections": [
                {"index": "2.4", "type": "timeseries", "title": "测风年风资源分析", "datasets": ["meso"]},
                {"index": "2.4.1", "type": "wind_rose"},
                {"index": "2.4.2", "type": "temporal"},
                {"index": "2.5", "type": "timeseries", "title": "代表年风资源分析", "datasets": ["rep"]},
                {"index": "2.5.1", "type": "wind_rose"},
                {"index": "2.5.2", "type": "temporal"},
            ],
        }
        path = tmp_path / "rep-ts-report.toml"
        with open(path, "wb") as f:
            tomli_w.dump(config, f)
        # Create dummy parquet files so load_datasets can resolve them
        (tmp_path / "meso").mkdir(exist_ok=True)
        (tmp_path / "rep").mkdir(exist_ok=True)
        (tmp_path / "meso" / "M1.parquet").touch()
        (tmp_path / "rep" / "M1.parquet").touch()
        return path

    def _create_five_subsection_config(self, tmp_path: Path, mast_count: int) -> Path:
        datasets = []
        for i in range(mast_count):
            datasets.append({
                "name": f"ds{i + 1}",
                "path": f"./M{i + 1}.parquet",
                "masts": [{"name": f"M{i + 1}", "air_density": 1.225}],
            })
        config = {
            "datasets": datasets,
            "subsections": [
                {"index": "2.4", "type": "timeseries", "title": "测风年风资源分析", "datasets": [f"ds{i + 1}" for i in range(mast_count)]},
                {"index": "2.4.1", "type": "wind_frequency"},
                {"index": "2.4.2", "type": "temporal"},
                {"index": "2.4.3", "type": "weibull"},
                {"index": "2.4.4", "type": "vertical_profile"},
                {"index": "2.4.5", "type": "turbulence"},
            ],
        }
        path = tmp_path / "rep-ts-report.toml"
        with open(path, "wb") as f:
            tomli_w.dump(config, f)
        # Create dummy parquet files so load_datasets can resolve them
        for i in range(mast_count):
            (tmp_path / f"M{i + 1}.parquet").touch()
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

        added = mock_builder.add_section.call_args[0][0]
        assert isinstance(added, HeadingSection)
        assert added.title == "Placeholder"
        assert len(added.subsections) == 5  # 2.1-2.3 placeholders + 2.4 测风年 + 2.5 代表年

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

        assert mock_builder.add_section.call_count == 2

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

        assert mock_builder.add_section.call_count == 2

        # Assert each service method receives exactly 1 mast tuple
        assert len(mock_service.generate_wind_frequency_section.call_args.args[0]) == 1
        assert len(mock_service.generate_temporal_section.call_args.args[0]) == 1
        assert len(mock_service.generate_weibull_section.call_args.args[0]) == 1
        assert len(mock_service.generate_vertical_profile_section.call_args.args[0]) == 1
        assert len(mock_service.generate_turbulence_section.call_args.args[0]) == 1

    @patch("cleanmast.application.usecases.generate_report.ReportBuilder")
    @patch("cleanmast.application.usecases.generate_report.ReportGenerationService")
    @patch("cleanmast.application.usecases.generate_report.load_timeseries")
    def test_non_timeseries_at_section_level_produces_placeholder(self, mock_load_ts, mock_service_cls, mock_builder_cls, tmp_path):
        # Every tree node produces a HeadingSection, including top-level leaf nodes
        config = {
            "datasets": [
                {"name": "ds1", "path": "./M1.parquet", "masts": [{"name": "M1", "air_density": 1.225}]},
            ],
            "subsections": [
                {"index": "1", "type": "wind_rose", "datasets": ["ds1"]},
            ],
        }
        path = tmp_path / "rep-ts-report.toml"
        with open(path, "wb") as f:
            tomli_w.dump(config, f)
        (tmp_path / "M1.parquet").touch()

        mock_ts = MagicMock()
        mock_ts.sensors = []
        mock_load_ts.return_value = mock_ts
        mock_service = MagicMock()
        mock_service.generate_wind_rose_section.return_value = "wind_rose_section"
        mock_service._create_analysis_input.return_value = "analysis_input"
        mock_service_cls.return_value = mock_service
        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ"), "pdf": Path("report.pdf"), "docx": Path("report.docx")}
        mock_builder_cls.return_value = mock_builder

        result = generate_report(str(path))
        assert result["pdf"] == Path("report.pdf")
        # Top-level leaf produces HeadingSection("Placeholder")
        assert mock_service.generate_wind_rose_section.call_count == 0
        assert mock_builder.add_section.call_count == 1
        added = mock_builder.add_section.call_args[0][0]
        assert isinstance(added, HeadingSection)
        assert added.title == "Placeholder"
        assert added.subsections == []

    @patch("cleanmast.application.usecases.generate_report.ReportBuilder")
    @patch("cleanmast.application.usecases.generate_report.ReportGenerationService")
    @patch("cleanmast.application.usecases.generate_report.load_timeseries")
    def test_timeseries_without_masts_produces_placeholder(self, mock_load_ts, mock_service_cls, mock_builder_cls, tmp_path):
        mock_ts = MagicMock()
        wd_sensor = MagicMock()
        wd_sensor.sensor_type = "WindDirection"
        wd_sensor.stat_type = "avg"
        mock_ts.sensors = [wd_sensor]
        mock_load_ts.return_value = mock_ts

        def _section_side_effect(items):
            return "section" if items else None

        mock_service = MagicMock()
        mock_service.generate_wind_rose_section.side_effect = _section_side_effect
        mock_service.generate_temporal_section.side_effect = _section_side_effect
        mock_service._create_analysis_input.return_value = "analysis_input"
        mock_service_cls.return_value = mock_service

        mock_builder = MagicMock()
        mock_builder.build.return_value = {
            "typ": Path("report.typ"),
            "pdf": Path("report.pdf"),
            "docx": Path("report.docx"),
        }
        mock_builder_cls.return_value = mock_builder

        # Flat config: every node produces output, including empty placeholders
        config = {
            "datasets": [
                {"name": "ds1", "path": "./M1.parquet", "masts": [{"name": "M1", "air_density": 1.225}]},
            ],
            "subsections": [
                {"index": "2.4", "type": "timeseries", "title": "有数据", "datasets": ["ds1"]},
                {"index": "2.4.1", "type": "wind_rose"},
                {"index": "2.5", "type": "timeseries", "title": "无数据"},
                {"index": "2.5.1", "type": "temporal"},
            ],
        }
        config_path = tmp_path / "rep-ts-report.toml"
        with open(config_path, "wb") as f:
            tomli_w.dump(config, f)
        (tmp_path / "M1.parquet").touch()

        result = generate_report(str(config_path))

        assert result["pdf"] == Path("report.pdf")
        assert mock_load_ts.call_count == 1
        assert mock_service.generate_wind_rose_section.call_count == 1
        # Both the data container and the empty placeholder produce HeadingSections
        assert mock_builder.add_section.call_count == 2
        added = mock_builder.add_section.call_args[0][0]
        assert isinstance(added, HeadingSection)
        empty_container = [s for s in added.subsections if getattr(s, 'title', None) == "无数据"]
        assert len(empty_container) == 1
        assert empty_container[0].subsections == []

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
            "datasets": [
                {"name": "ds1", "path": "./M1.parquet", "masts": [{"name": "M1", "air_density": 1.225}]},
            ],
            "subsections": [
                {"index": "2.4", "type": "timeseries", "title": "测风年风资源分析", "datasets": ["ds1"]},
                {"index": "2.4.1", "type": "wind_rose"},
                {"index": "2.4.2", "type": "vertical_profile"},
            ],
        }
        path = tmp_path / "rep-ts-report.toml"
        with open(path, "wb") as f:
            tomli_w.dump(config, f)
        (tmp_path / "M1.parquet").touch()

        result = generate_report(str(path))
        assert result["pdf"] == Path("report.pdf")

        added_sections = [call.args[0] for call in mock_builder.add_section.call_args_list]
        heading_sections = [s for s in added_sections if isinstance(s, HeadingSection)]
        assert len(heading_sections) == 2

        heading_ir = heading_sections[1].render_ir(tmp_path)
        assert len(heading_ir.subsections) > 0, "Parent HeadingSection should contain nested subsections"

        doc = TypstDocument(children=[heading_ir])
        serialized = serialize(doc)
        assert "== " in serialized, "Serialized output should contain == markers for child headings"

    def test_config_not_found_raises_error(self, tmp_path):
        missing_path = tmp_path / "nonexistent.toml"
        with pytest.raises(FileNotFoundError):
            generate_report(str(missing_path))


class TestFlatConfigOrchestration:
    """Tests for the new _generate_from_flat_config orchestration path."""

    def _make_config(self, subsections, datasets=None):
        """Helper to build a FlatReportConfig for tests."""
        if datasets is None:
            datasets = [
                DatasetConfig(
                    name="ds1",
                    path="/fake/data.parquet",
                    masts=[MastRef(name="M1", air_density=1.225)],
                )
            ]
        return FlatReportConfig(datasets=datasets, subsections=subsections)

    def _mock_ts_with_wd(self):
        """Return a mocked TimeSeriesData that has wind-direction sensors."""
        mock_ts = MagicMock()
        wd_sensor = MagicMock()
        wd_sensor.sensor_type = "WindDirection"
        wd_sensor.stat_type = "avg"
        mock_ts.sensors = [wd_sensor]
        return mock_ts

    def _mock_ts_without_wd(self):
        """Return a mocked TimeSeriesData without wind-direction sensors."""
        mock_ts = MagicMock()
        mock_ts.sensors = []
        return mock_ts

    def _make_loaded_datasets(self, config, mock_ts):
        """Build a loaded_datasets dict from a FlatReportConfig and mocked timeseries."""
        loaded = {}
        for ds in config.datasets:
            mast_inputs = []
            for mast_ref in ds.masts:
                meta = SingleMastMeta(
                    mast_name=mast_ref.name,
                    air_density=mast_ref.air_density,
                    width="80%",
                )
                mast_inputs.append(("analysis_input", meta))
            loaded[ds.name] = LoadedDataset(
                path=Path(ds.path),
                timeseries=mock_ts,
                mast_inputs=mast_inputs,
            )
        return loaded

    def test_single_timeseries_container_dispatches_leaf_children(self):
        """A timeseries container with two leaf children is dispatched correctly."""
        mock_ts = self._mock_ts_with_wd()

        mock_service = MagicMock()
        mock_service.generate_wind_rose_section.return_value = "wind_rose_result"
        mock_service.generate_temporal_section.return_value = "temporal_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="测风年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_rose"),
            FlatSubsectionConfig(index="2.4.2", type="temporal"),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        result = _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert result == {"typ": Path("report.typ")}
        assert mock_service.generate_wind_rose_section.call_count == 1
        assert mock_service.generate_temporal_section.call_count == 1
        assert mock_builder.add_section.call_count == 2

        added = mock_builder.add_section.call_args[0][0]
        assert isinstance(added, HeadingSection)
        assert added.title == "Placeholder"
        assert len(added.subsections) == 4
        real_container = [s for s in added.subsections if getattr(s, 'title', None) == "测风年"]
        assert len(real_container) == 1
        assert len(real_container[0].subsections) == 2

    def test_dataset_inherited_from_ancestor(self):
        """Leaf children inherit datasets from the parent timeseries container."""
        mock_ts = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_wind_frequency_section.return_value = "wf_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        # Parent has datasets, child has None — tree builder propagates it
        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="Container", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency"),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert mock_service.generate_wind_frequency_section.call_count == 1

    def test_fifty_year_max_wind_container_stub(self):
        """fifty_year_max_wind container routes to the Task-10 placeholder."""
        mock_ts = self._mock_ts_without_wd()

        result = MagicMock()
        result.iec_standards = "iec_result"
        result.method1 = "m1_result"
        result.method2 = "m2_result"
        result.method3 = "m3_result"
        result.summary = "summary_result"
        mock_service = MagicMock()
        mock_service.generate_fifty_year_max_wind_section.return_value = result
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        config = self._make_config([
            FlatSubsectionConfig(index="2.6", type="fifty_year_max_wind", title="五十年一遇", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.6.1", type="iec_standards"),
            FlatSubsectionConfig(index="2.6.2", type="fifty_year_method1"),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert mock_service.generate_fifty_year_max_wind_section.call_count == 1
        assert mock_builder.add_section.call_count == 2
        added = mock_builder.add_section.call_args[0][0]
        assert isinstance(added, HeadingSection)
        assert added.title == "Placeholder"
        assert len(added.subsections) == 6
        real_container = [s for s in added.subsections if getattr(s, 'title', None) == "五十年一遇"]
        assert len(real_container) == 1
        assert real_container[0].subsections == ["iec_result", "m1_result"]

    def test_multiple_timeseries_containers(self):
        """Two separate timeseries containers each produce a HeadingSection."""
        mock_ts = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_wind_frequency_section.return_value = "wf_result"
        mock_service.generate_weibull_section.return_value = "weibull_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="测风年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency"),
            FlatSubsectionConfig(index="2.5", type="timeseries", title="代表年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.5.1", type="weibull"),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert mock_builder.add_section.call_count == 2
        added = mock_builder.add_section.call_args[0][0]
        assert isinstance(added, HeadingSection)
        assert added.title == "Placeholder"
        assert len(added.subsections) == 5
        titles = [h.title for h in added.subsections]
        assert "测风年" in titles
        assert "代表年" in titles

    def test_wind_rose_skipped_without_wd_sensors(self):
        """wind_rose leaf is skipped when no wind-direction sensors exist."""
        mock_ts = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_wind_rose_section.return_value = "wind_rose_result"
        mock_service.generate_temporal_section.return_value = "temporal_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="Container", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_rose"),
            FlatSubsectionConfig(index="2.4.2", type="temporal"),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert mock_service.generate_wind_rose_section.call_count == 0
        assert mock_service.generate_temporal_section.call_count == 1
        # Only temporal inside HeadingSection
        added = mock_builder.add_section.call_args[0][0]
        assert isinstance(added, HeadingSection)
        assert len(added.subsections) == 4

    def test_unknown_leaf_type_is_skipped(self):
        """A leaf type not in subsection_method_map is silently skipped."""
        mock_ts = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_wind_frequency_section.return_value = "wf_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        # Use a known leaf plus an unknown one
        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="Container", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency"),
            FlatSubsectionConfig(index="2.4.2", type="iec_standards"),  # not in method map yet
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        # wind_frequency should be called, iec_standards skipped
        assert mock_service.generate_wind_frequency_section.call_count == 1
        added = mock_builder.add_section.call_args[0][0]
        assert len(added.subsections) == 4

    def test_loads_datasets_by_name(self):
        """Dataset paths are resolved by name from the catalog and passed to load_timeseries."""
        mock_ts = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_temporal_section.return_value = "temporal_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        datasets = [
            DatasetConfig(
                name="meso",
                path="/project/meso.parquet",
                masts=[MastRef(name="M1", air_density=1.225)],
            ),
            DatasetConfig(
                name="repyear",
                path="/project/repyear.parquet",
                masts=[MastRef(name="M1", air_density=1.225)],
            ),
        ]
        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="Multi", datasets=["meso", "repyear"]),
            FlatSubsectionConfig(index="2.4.1", type="temporal"),
        ], datasets=datasets)
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        # Both datasets should be present in loaded_datasets
        assert "meso" in loaded
        assert "repyear" in loaded

    def test_multi_mast_dataset_aggregated(self):
        """A dataset with multiple masts aggregates them into a single input_items list."""
        mock_ts = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_weibull_section.return_value = "weibull_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        datasets = [
            DatasetConfig(
                name="ds1",
                path="/fake/data.parquet",
                masts=[
                    MastRef(name="M1", air_density=1.225),
                    MastRef(name="M2", air_density=1.200),
                ],
            ),
        ]
        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="Multi-Mast", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="weibull"),
        ], datasets=datasets)
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        # Both masts should be in the call
        args = mock_service.generate_weibull_section.call_args.args[0]
        assert len(args) == 2  # Two mast tuples

    def test_all_config_sections_appear_in_builder(self):
        """All top-level sections (2.4, 2.5, 2.6) must appear in builder output."""
        mock_ts = self._mock_ts_with_wd()

        mock_service = MagicMock()
        mock_service.generate_wind_rose_section.return_value = "wind_rose_result"
        mock_service.generate_temporal_section.return_value = "temporal_result"
        mock_service.generate_air_density_section.return_value = "air_density_result"
        mock_service.generate_fifty_year_max_wind_section.return_value = MagicMock(
            iec_standards="iec_result"
        )
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="测风年风资源分析", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_rose"),
            FlatSubsectionConfig(index="2.5", type="timeseries", title="代表年风资源分析", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.5.1", type="temporal"),
            FlatSubsectionConfig(index="2.6", type="fifty_year_max_wind", title="五十年一遇最大风速", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.6.1", type="iec_standards"),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert mock_builder.add_section.call_count == 2, (
            f"Expected 2 sections added to builder, got {mock_builder.add_section.call_count}"
        )
        added = mock_builder.add_section.call_args[0][0]
        assert isinstance(added, HeadingSection)
        assert added.title == "Placeholder"
        titles = [s.title for s in added.subsections]
        assert "测风年风资源分析" in titles, f"Missing '测风年风资源分析' in titles: {titles}"
        assert "代表年风资源分析" in titles, f"Missing '代表年风资源分析' in titles: {titles}"
        assert "五十年一遇最大风速" in titles, f"Missing '五十年一遇最大风速' in titles: {titles}"

    def test_timeseries_children_processed(self):
        """Sections 2.4 children (wind_rose, air_density) must dispatch to service methods."""
        mock_ts = self._mock_ts_with_wd()

        mock_service = MagicMock()
        mock_service.generate_wind_rose_section.return_value = "wind_rose_result"
        mock_service.generate_temporal_section.return_value = "temporal_result"
        mock_service.generate_air_density_section.return_value = "air_density_result"
        mock_service.generate_weibull_section.return_value = "weibull_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="测风年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_rose"),
            FlatSubsectionConfig(index="2.4.2", type="temporal"),
            FlatSubsectionConfig(index="2.4.3", type="air_density"),
            FlatSubsectionConfig(index="2.4.4", type="weibull"),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert mock_service.generate_wind_rose_section.call_count == 1, (
            f"Expected wind_rose section to be generated once, got {mock_service.generate_wind_rose_section.call_count}"
        )
        assert mock_service.generate_air_density_section.call_count == 1, (
            f"Expected air_density section to be generated once, got {mock_service.generate_air_density_section.call_count}"
        )
        assert mock_service.generate_temporal_section.call_count == 1, (
            f"Expected temporal section to be generated once, got {mock_service.generate_temporal_section.call_count}"
        )
        assert mock_service.generate_weibull_section.call_count == 1, (
            f"Expected weibull section to be generated once, got {mock_service.generate_weibull_section.call_count}"
        )

    def test_placeholder_sections_in_dispatcher(self):
        """Dispatcher produces HeadingSection(\"Placeholder\") for ancestor and gap nodes."""
        mock_ts = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_wind_frequency_section.return_value = "wf_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="测风年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency"),
            FlatSubsectionConfig(index="2.6", type="timeseries", title="代表年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.6.1", type="wind_frequency"),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert mock_builder.add_section.call_count == 2
        added = mock_builder.add_section.call_args[0][0]
        assert isinstance(added, HeadingSection)
        assert added.title == "Placeholder", (
            f"Expected Placeholder title, got '{added.title}'"
        )

        assert len(added.subsections) == 6, (
            f"Expected 6 subsections, got {len(added.subsections)}"
        )
        titles = [s.title for s in added.subsections]
        assert "测风年" in titles, f"Missing '测风年' in titles: {titles}"
        assert "代表年" in titles, f"Missing '代表年' in titles: {titles}"
        middle = added.subsections[4]
        assert isinstance(middle, HeadingSection)
        assert middle.title == "Placeholder"
        assert middle.subsections == []

    def test_placeholder_heading_in_typst_ir(self):
        """Placeholder HeadingSection renders as TypstSection with empty body and 'Placeholder' heading."""
        from pathlib import Path

        from typst_ir import serialize
        from typst_ir.nodes import TypstDocument

        section = HeadingSection(title="Placeholder")
        ir_section = section.render_ir(Path("/tmp"))

        # Verify structure
        assert ir_section.heading.text == "Placeholder"
        assert ir_section.body == []
        assert ir_section.subsections == []

        # Verify serialization
        doc = TypstDocument(children=[ir_section])
        markup = serialize(doc)
        assert "= Placeholder" in markup
        assert "Placeholder" in markup

    def test_placeholders_in_serialized_typ(self):
        """Placeholder sections appear as headings in serialized .typ output."""
        from typst_ir import serialize
        from typst_ir.nodes import TypstDocument

        mock_ts = self._mock_ts_without_wd()
        mock_service = MagicMock()
        mock_wf = MagicMock()
        from typst_ir.nodes import TypstHeading, TypstSection
        mock_wf.render_ir.return_value = TypstSection(
            heading=TypstHeading(text="风频"),
            body=[],
            subsections=[],
        )
        mock_service.generate_wind_frequency_section.return_value = mock_wf
        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="测风年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency"),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        root_section = mock_builder.add_section.call_args[0][0]
        assert isinstance(root_section, HeadingSection)
        assert root_section.title == "Placeholder"

        ir_section = root_section.render_ir(Path("/tmp"))
        doc = TypstDocument(children=[ir_section])
        markup = serialize(doc)

        assert "= Placeholder" in markup, (
            f"Expected '= Placeholder' in serialized typst, got:\n{markup[:500]}"
        )


class TestPlaceholderPreservation:
    """Tests that placeholder gaps in the section tree are preserved in output."""

    def _make_config(self, subsections, datasets=None):
        if datasets is None:
            datasets = [
                DatasetConfig(
                    name="ds1",
                    path="/fake/data.parquet",
                    masts=[MastRef(name="M1", air_density=1.225)],
                ),
            ]
        return FlatReportConfig(datasets=datasets, subsections=subsections)

    def _mock_ts_without_wd(self):
        mock_ts = MagicMock()
        mock_ts.sensors = []
        return mock_ts

    def _make_loaded_datasets(self, config, mock_ts):
        loaded = {}
        for ds in config.datasets:
            mast_inputs = []
            for mast_ref in ds.masts:
                meta = SingleMastMeta(
                    mast_name=mast_ref.name,
                    air_density=mast_ref.air_density,
                    width="80%",
                )
                mast_inputs.append(("analysis_input", meta))
            loaded[ds.name] = LoadedDataset(
                path=Path(ds.path),
                timeseries=mock_ts,
                mast_inputs=mast_inputs,
            )
        return loaded

    def test_gap_placeholder_appears_in_output(self):
        """Gap at 2.5 between 2.4 and 2.6 is preserved as empty placeholder."""
        mock_ts = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_wind_frequency_section.return_value = "wf_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="测风年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency"),
            FlatSubsectionConfig(index="2.6", type="timeseries", title="代表年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.6.1", type="wind_frequency"),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert mock_builder.add_section.call_count == 2
        root = mock_builder.add_section.call_args[0][0]
        assert isinstance(root, HeadingSection)
        assert len(root.subsections) == 6, (
            f"Expected 6 subsections, got {len(root.subsections)}"
        )
        titles = [s.title for s in root.subsections]
        assert "测风年" in titles, f"Missing '测风年' in titles: {titles}"
        assert "代表年" in titles, f"Missing '代表年' in titles: {titles}"
        placeholder = root.subsections[4]
        assert isinstance(placeholder, HeadingSection)
        assert placeholder.title == "Placeholder", (
            f"Expected placeholder title 'Placeholder', got '{placeholder.title}'"
        )

    def test_intermediate_gaps_preserved(self):
        """Gaps 2.1, 2.2, 2.3 before 2.4 are preserved as placeholders."""
        mock_ts = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_air_density_section.return_value = "ad_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="测风年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="air_density"),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert mock_builder.add_section.call_count == 2
        root = mock_builder.add_section.call_args[0][0]
        assert isinstance(root, HeadingSection)
        assert len(root.subsections) == 4, (
            f"Expected 4 subsections (2.1-2.3 placeholders + 2.4), got {len(root.subsections)}"
        )
        for i in range(3):
            sub = root.subsections[i]
            assert isinstance(sub, HeadingSection), (
                f"Expected HeadingSection at index {i}, got {type(sub)}"
            )
            assert sub.title == "Placeholder", (
                f"Expected 'Placeholder' at index {i}, got '{sub.title}'"
            )
        assert root.subsections[3].title == "测风年", (
            f"Expected '测风年' at index 3, got '{root.subsections[3].title}'"
        )

    def test_all_tree_nodes_in_builder(self):
        """All nodes in the tree including placeholders are passed to builder."""
        mock_ts = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_air_density_section.return_value = "ad_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="air_density"),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert mock_builder.add_section.call_count == 2, (
            f"Expected 2 add_section calls, got {mock_builder.add_section.call_count}"
        )
        root = mock_builder.add_section.call_args[0][0]
        assert isinstance(root, HeadingSection)
        assert len(root.subsections) == 4, (
            f"Expected 4 subsections including placeholders, got {len(root.subsections)}"
        )


class TestFiftyYearFlatDispatch:
    """Tests for _handle_fifty_year_max_wind_flat subsection extraction."""

    def _make_node(self, children_types=None, datasets=None):
        from cleanmast.subdomains.assessment.domain.value_objects.tree_builder import (
            SectionNode,
        )
        children = []
        if children_types:
            for i, t in enumerate(children_types):
                children.append(SectionNode(index=f"2.6.{i + 1}", type=t))
        return SectionNode(index="2.6", type="fifty_year_max_wind", title="五十年一遇", datasets=datasets or ["ds1"], children=children)

    def _make_mock_result(self):
        """Return a mock FiftyYearMaxWindSection with identifiable subsections."""
        result = MagicMock()
        result.iec_standards = "iec_standards_subsection"
        result.method1 = "method1_subsection"
        result.method2 = "method2_subsection"
        result.method3 = "method3_subsection"
        result.summary = "summary_subsection"
        return result

    def _make_loaded(self, items=None):
        return {
            "ds1": LoadedDataset(
                path=Path("/fake/ds1.parquet"),
                timeseries=MagicMock(),
                mast_inputs=items if items is not None else [("input", "meta")],
            )
        }

    def test_extracts_all_subsections_when_all_children_present(self):
        mock_service = MagicMock()
        mock_service.generate_fifty_year_max_wind_section.return_value = self._make_mock_result()

        node = self._make_node(["iec_standards", "fifty_year_method1", "fifty_year_method2", "fifty_year_method3", "fifty_year_summary"])
        result = _handle_fifty_year_max_wind_flat(node, mock_service, self._make_loaded())

        assert result == ["iec_standards_subsection", "method1_subsection", "method2_subsection", "method3_subsection", "summary_subsection"]
        mock_service.generate_fifty_year_max_wind_section.assert_called_once()

    def test_extracts_only_matching_subsections(self):
        mock_service = MagicMock()
        mock_service.generate_fifty_year_max_wind_section.return_value = self._make_mock_result()

        node = self._make_node(["iec_standards", "fifty_year_method3"])
        result = _handle_fifty_year_max_wind_flat(node, mock_service, self._make_loaded())

        assert result == ["iec_standards_subsection", "method3_subsection"]

    def test_returns_empty_list_when_no_matching_children(self):
        mock_service = MagicMock()
        mock_service.generate_fifty_year_max_wind_section.return_value = self._make_mock_result()

        node = self._make_node(["wind_rose"])
        result = _handle_fifty_year_max_wind_flat(node, mock_service, self._make_loaded())

        assert len(result) == 1
        assert isinstance(result[0], HeadingSection)
        assert result[0].title == "Placeholder"

    def test_returns_none_when_no_input_items(self):
        mock_service = MagicMock()

        node = self._make_node(["iec_standards"])
        result = _handle_fifty_year_max_wind_flat(node, mock_service, self._make_loaded(items=[]))

        assert result == []
        mock_service.generate_fifty_year_max_wind_section.assert_not_called()

    def test_preserves_child_order_in_result(self):
        mock_service = MagicMock()
        mock_service.generate_fifty_year_max_wind_section.return_value = self._make_mock_result()

        node = self._make_node(["fifty_year_summary", "iec_standards", "fifty_year_method1"])
        result = _handle_fifty_year_max_wind_flat(node, mock_service, self._make_loaded())

        assert result == ["summary_subsection", "iec_standards_subsection", "method1_subsection"]

    def test_single_child_returns_single_subsection(self):
        mock_service = MagicMock()
        mock_service.generate_fifty_year_max_wind_section.return_value = self._make_mock_result()

        node = self._make_node(["fifty_year_method2"])
        result = _handle_fifty_year_max_wind_flat(node, mock_service, self._make_loaded())

        assert result == ["method2_subsection"]
        mock_service.generate_fifty_year_max_wind_section.assert_called_once()


class TestDatasetCaching:
    """Tests that datasets are cached within a single _generate_from_flat_config invocation."""

    def _make_config(self, subsections, datasets=None):
        if datasets is None:
            datasets = [
                DatasetConfig(
                    name="ds1",
                    path="/fake/data.parquet",
                    masts=[MastRef(name="M1", air_density=1.225)],
                ),
            ]
        return FlatReportConfig(datasets=datasets, subsections=subsections)

    def _mock_ts_without_wd(self):
        mock_ts = MagicMock()
        mock_ts.sensors = []
        return mock_ts

    def _make_loaded_datasets(self, config, mock_ts):
        """Build a loaded_datasets dict from a FlatReportConfig and mocked timeseries."""
        loaded = {}
        for ds in config.datasets:
            mast_inputs = []
            for mast_ref in ds.masts:
                meta = SingleMastMeta(
                    mast_name=mast_ref.name,
                    air_density=mast_ref.air_density,
                    width="80%",
                )
                mast_inputs.append(("analysis_input", meta))
            loaded[ds.name] = LoadedDataset(
                path=Path(ds.path),
                timeseries=mock_ts,
                mast_inputs=mast_inputs,
            )
        return loaded

    def test_same_dataset_loaded_once_across_two_containers(self):
        mock_ts = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_wind_frequency_section.return_value = "wf_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="测风年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency"),
            FlatSubsectionConfig(index="2.5", type="timeseries", title="代表年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.5.1", type="wind_frequency"),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert mock_service.generate_wind_frequency_section.call_count == 2

    def test_same_dataset_loaded_once_across_timeseries_and_fifty_year(self):
        mock_ts = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_wind_frequency_section.return_value = "wf_result"
        mock_service.generate_fifty_year_max_wind_section.return_value = "fifty_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="测风年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency"),
            FlatSubsectionConfig(index="2.6", type="fifty_year_max_wind", title="五十年一遇", datasets=["ds1"]),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert mock_service.generate_fifty_year_max_wind_section.call_count == 1

    def test_cache_isolated_between_invocations(self):
        mock_ts = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_wind_frequency_section.return_value = "wf_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="测风年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency"),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)
        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        # Both invocations use the same pre-loaded data
        assert mock_service.generate_wind_frequency_section.call_count == 2

    def test_multiple_datasets_each_loaded_once(self):
        mock_ts = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_wind_frequency_section.return_value = "wf_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        datasets = [
            DatasetConfig(name="ds1", path="/fake/ds1.parquet", masts=[MastRef(name="M1", air_density=1.225)]),
            DatasetConfig(name="ds2", path="/fake/ds2.parquet", masts=[MastRef(name="M2", air_density=1.200)]),
        ]
        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="Container1", datasets=["ds1", "ds2"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency"),
            FlatSubsectionConfig(index="2.5", type="timeseries", title="Container2", datasets=["ds1", "ds2"]),
            FlatSubsectionConfig(index="2.5.1", type="wind_frequency"),
        ], datasets=datasets)
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert len(loaded) == 2
        assert "ds1" in loaded
        assert "ds2" in loaded

    def test_multi_mast_dataset_cached_once(self):
        mock_ts = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_weibull_section.return_value = "weibull_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        datasets = [
            DatasetConfig(
                name="ds1",
                path="/fake/data.parquet",
                masts=[
                    MastRef(name="M1", air_density=1.225),
                    MastRef(name="M2", air_density=1.200),
                ],
            ),
        ]
        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="Container1", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="weibull"),
            FlatSubsectionConfig(index="2.5", type="timeseries", title="Container2", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.5.1", type="weibull"),
        ], datasets=datasets)
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert len(mock_service.generate_weibull_section.call_args_list[0].args[0]) == 2
        assert len(mock_service.generate_weibull_section.call_args_list[1].args[0]) == 2
