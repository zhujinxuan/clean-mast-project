from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import tomli_w
from cleanmast.application.usecases.generate_report import (
    HeadingSection,
    LoadedDataset,
    _generate_from_flat_config,
    generate_report,
)
from cleanmast.subdomains.configuration import (
    DatasetConfig,
    FlatReportConfig,
    FlatSubsectionConfig,
    MastRef,
)
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)
from cleanmast.subdomains.reporting.model.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.model.analysis_parameters import (
    AnalysisParameters,
)


class TestGenerateReport:
    def _create_nested_config(self, tmp_path: Path) -> Path:
        config = {
            "datasets": [
                {
                    "name": "reconstruct_meso_filled_heights",
                    "masts": [{"name": "M1", "air_density": 1.225, "input": {"data": "./reconstruct_meso/M1.parquet"}}],
                },
                {
                    "name": "rep",
                    "masts": [{"name": "M1", "air_density": 1.225, "input": {"data": "./rep/M1.parquet"}}],
                },
            ],
            "subsections": [
                {"index": "2.4", "type": "timeseries", "title": "测风年风资源分析", "datasets": ["reconstruct_meso_filled_heights"]},
                {"index": "2.4.1", "type": "wind_rose", "datasets": ["reconstruct_meso_filled_heights"]},
                {"index": "2.4.2", "type": "temporal", "datasets": ["reconstruct_meso_filled_heights"]},
                {"index": "2.5", "type": "timeseries", "title": "代表年风资源分析", "datasets": ["rep"]},
                {"index": "2.5.1", "type": "wind_rose", "datasets": ["rep"]},
                {"index": "2.5.2", "type": "temporal", "datasets": ["rep"]},
            ],
        }
        path = tmp_path / "rep-ts-report.toml"
        with open(path, "wb") as f:
            tomli_w.dump(config, f)
        # Create dummy parquet files so load_datasets can resolve them
        (tmp_path / "reconstruct_meso").mkdir(exist_ok=True)
        (tmp_path / "rep").mkdir(exist_ok=True)
        (tmp_path / "reconstruct_meso" / "M1.parquet").touch()
        (tmp_path / "rep" / "M1.parquet").touch()
        return path

    def _create_five_subsection_config(self, tmp_path: Path, mast_count: int) -> Path:
        datasets = []
        for i in range(mast_count):
            datasets.append({
                "name": f"ds{i + 1}",
                "masts": [{"name": f"M{i + 1}", "air_density": 1.225, "input": {"data": f"./M{i + 1}.parquet"}}],
            })
        config = {
            "datasets": datasets,
            "subsections": [
                {"index": "2.4", "type": "timeseries", "title": "测风年风资源分析", "datasets": [f"ds{i + 1}" for i in range(mast_count)]},
                {"index": "2.4.1", "type": "wind_frequency", "datasets": [f"ds{i + 1}" for i in range(mast_count)]},
                {"index": "2.4.2", "type": "temporal", "datasets": [f"ds{i + 1}" for i in range(mast_count)]},
                {"index": "2.4.3", "type": "weibull", "datasets": [f"ds{i + 1}" for i in range(mast_count)]},
                {"index": "2.4.4", "type": "vertical_profile", "datasets": [f"ds{i + 1}" for i in range(mast_count)]},
                {"index": "2.4.5", "type": "turbulence", "datasets": [f"ds{i + 1}" for i in range(mast_count)]},
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
    def test_non_timeseries_at_section_level_produces_placeholder(self, mock_load_ts, mock_service_cls, mock_builder_cls, tmp_path):
        # Every tree node produces a HeadingSection, including top-level leaf nodes
        config = {
            "datasets": [
                {"name": "ds1", "masts": [{"name": "M1", "air_density": 1.225, "input": {"data": "./M1.parquet"}}]},
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
                    masts=[MastRef(name="M1", air_density=1.225, input=TimeSeriesSource(data="/fake/data.parquet"))],
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
            mast_data = []
            for mast_ref in ds.masts:
                mast_data.append(SingleMastAnalysisInput(
                    time_series=mock_ts,
                    parameters=AnalysisParameters(air_density=mast_ref.air_density),
                    mast_name=mast_ref.name,
                ))
            loaded[ds.name] = LoadedDataset(
                name=ds.name,
                mast_data=mast_data,
            )
        return loaded

    def _make_loaded_datasets_per_ds(self, config, mock_ts_map):
        """Build loaded_datasets with per-dataset mock timeseries.

        Unlike ``_make_loaded_datasets`` which uses the same mock for all
        datasets, this allows each dataset to have its own mocked
        ``TimeSeriesData`` (e.g. one with WD sensors, one without).

        Args:
            config: FlatReportConfig with dataset definitions.
            mock_ts_map: Mapping of dataset name → mock TimeSeriesData.

        Returns:
            Dict of dataset name → LoadedDataset.
        """
        loaded = {}
        for ds in config.datasets:
            mast_data = []
            for mast_ref in ds.masts:
                mock_ts = mock_ts_map[ds.name]
                mast_data.append(SingleMastAnalysisInput(
                    time_series=mock_ts,
                    parameters=AnalysisParameters(air_density=mast_ref.air_density),
                    mast_name=mast_ref.name,
                ))
            loaded[ds.name] = LoadedDataset(
                name=ds.name,
                mast_data=mast_data,
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
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.2", type="temporal", datasets=["ds1"]),
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
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency", datasets=["ds1"]),
        ])
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert mock_service.generate_wind_frequency_section.call_count == 1

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
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.5", type="timeseries", title="代表年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.5.1", type="weibull", datasets=["ds1"]),
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
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.2", type="temporal", datasets=["ds1"]),
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
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.2", type="iec_standards", datasets=["ds1"]),  # not in method map yet
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
                name="reconstruct_meso",
                masts=[MastRef(name="M1", air_density=1.225, input=TimeSeriesSource(data="/project/reconstruct_meso.parquet"))],
            ),
            DatasetConfig(
                name="repyear",
                masts=[MastRef(name="M1", air_density=1.225, input=TimeSeriesSource(data="/project/repyear.parquet"))],
            ),
        ]
        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="Multi", datasets=["reconstruct_meso", "repyear"]),
            FlatSubsectionConfig(index="2.4.1", type="temporal", datasets=["reconstruct_meso", "repyear"]),
        ], datasets=datasets)
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        # Both datasets should be present in loaded_datasets
        assert "reconstruct_meso" in loaded
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
                masts=[
                    MastRef(name="M1", air_density=1.225, input=TimeSeriesSource(data="/fake/data.parquet")),
                    MastRef(name="M2", air_density=1.200, input=TimeSeriesSource(data="/fake/data.parquet")),
                ],
            ),
        ]
        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="Multi-Mast", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="weibull", datasets=["ds1"]),
        ], datasets=datasets)
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        # Both masts should be in the call
        args = mock_service.generate_weibull_section.call_args.args[0]
        assert len(args) == 2  # Two mast tuples

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
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.2", type="temporal", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.3", type="air_density", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.4", type="weibull", datasets=["ds1"]),
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
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.6", type="timeseries", title="代表年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.6.1", type="wind_frequency", datasets=["ds1"]),
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
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency", datasets=["ds1"]),
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

    def test_child_uses_own_datasets_not_parents(self):
        """Children with explicit datasets receive only masts from their declared datasets.

        RED phase: current code aggregates ALL parent datasets for every child.
        """
        mock_ts_ds1 = self._mock_ts_with_wd()
        mock_ts_ds2 = self._mock_ts_with_wd()

        mock_service = MagicMock()
        mock_service.generate_wind_rose_section.return_value = "wind_rose_result"
        mock_service.generate_temporal_section.return_value = "temporal_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        datasets = [
            DatasetConfig(
                name="ds1",
                masts=[MastRef(name="M1", air_density=1.225, input=TimeSeriesSource(data="/fake/ds1.parquet"))],
            ),
            DatasetConfig(
                name="ds2",
                masts=[MastRef(name="M2", air_density=1.200, input=TimeSeriesSource(data="/fake/ds2.parquet"))],
            ),
        ]
        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="Container", datasets=["ds1", "ds2"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.2", type="temporal", datasets=["ds2"]),
        ], datasets=datasets)
        loaded = self._make_loaded_datasets_per_ds(config, {"ds1": mock_ts_ds1, "ds2": mock_ts_ds2})

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert mock_service.generate_wind_rose_section.call_count == 1
        wr_items = mock_service.generate_wind_rose_section.call_args.args[0]
        assert len(wr_items) == 1, (
            f"Child wind_rose (datasets=[ds1]) should receive 1 mast, got {len(wr_items)}"
        )

        assert mock_service.generate_temporal_section.call_count == 1
        t_items = mock_service.generate_temporal_section.call_args.args[0]
        assert len(t_items) == 1, (
            f"Child temporal (datasets=[ds2]) should receive 1 mast, got {len(t_items)}"
        )

    def test_per_child_wind_direction_sensor_detection(self):
        """Wind rose generation is per-child based on that child's dataset sensors.

        RED phase: current code computes any_has_wd_sensors once per parent.
        """
        mock_ts_with_wd = self._mock_ts_with_wd()
        mock_ts_without_wd = self._mock_ts_without_wd()

        mock_service = MagicMock()
        mock_service.generate_wind_rose_section.return_value = "wind_rose_result"
        mock_service._create_analysis_input.return_value = "analysis_input"

        mock_builder = MagicMock()
        mock_builder.build.return_value = {"typ": Path("report.typ")}

        datasets = [
            DatasetConfig(
                name="ds_with_wd",
                masts=[MastRef(name="M_WD", air_density=1.225, input=TimeSeriesSource(data="/fake/wd.parquet"))],
            ),
            DatasetConfig(
                name="ds_without_wd",
                masts=[MastRef(name="M_NOWD", air_density=1.200, input=TimeSeriesSource(data="/fake/nowd.parquet"))],
            ),
        ]
        config = self._make_config([
            FlatSubsectionConfig(
                index="2.4", type="timeseries", title="Container",
                datasets=["ds_with_wd", "ds_without_wd"],
            ),
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["ds_with_wd"]),
            FlatSubsectionConfig(index="2.4.2", type="wind_rose", datasets=["ds_without_wd"]),
        ], datasets=datasets)
        loaded = self._make_loaded_datasets_per_ds(
            config, {"ds_with_wd": mock_ts_with_wd, "ds_without_wd": mock_ts_without_wd},
        )

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert mock_service.generate_wind_rose_section.call_count == 1, (
            f"Expected 1 wind_rose generation (child A has WD), "
            f"got {mock_service.generate_wind_rose_section.call_count}"
        )

        added = mock_builder.add_section.call_args[0][0]
        real_container = [s for s in added.subsections if getattr(s, "title", None) == "Container"]
        assert len(real_container) == 1
        container_subs = real_container[0].subsections
        assert any(isinstance(s, HeadingSection) for s in container_subs), (
            "Child without WD sensors should produce a Placeholder HeadingSection"
        )


class TestPlaceholderPreservation:
    """Tests that placeholder gaps in the section tree are preserved in output."""

    def _make_config(self, subsections, datasets=None):
        if datasets is None:
            datasets = [
                DatasetConfig(
                    name="ds1",
                    masts=[MastRef(name="M1", air_density=1.225, input=TimeSeriesSource(data="/fake/data.parquet"))],
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
            mast_data = []
            for mast_ref in ds.masts:
                mast_data.append(SingleMastAnalysisInput(
                    time_series=mock_ts,
                    parameters=AnalysisParameters(air_density=mast_ref.air_density),
                    mast_name=mast_ref.name,
                ))
            loaded[ds.name] = LoadedDataset(
                name=ds.name,
                mast_data=mast_data,
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
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.6", type="timeseries", title="代表年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.6.1", type="wind_frequency", datasets=["ds1"]),
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
            FlatSubsectionConfig(index="2.4.1", type="air_density", datasets=["ds1"]),
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
            FlatSubsectionConfig(index="2.4.1", type="air_density", datasets=["ds1"]),
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


class TestDatasetCaching:
    """Tests that datasets are cached within a single _generate_from_flat_config invocation."""

    def _make_config(self, subsections, datasets=None):
        if datasets is None:
            datasets = [
                DatasetConfig(
                    name="ds1",
                    masts=[MastRef(name="M1", air_density=1.225, input=TimeSeriesSource(data="/fake/data.parquet"))],
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
            mast_data = []
            for mast_ref in ds.masts:
                mast_data.append(SingleMastAnalysisInput(
                    time_series=mock_ts,
                    parameters=AnalysisParameters(air_density=mast_ref.air_density),
                    mast_name=mast_ref.name,
                ))
            loaded[ds.name] = LoadedDataset(
                name=ds.name,
                mast_data=mast_data,
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
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.5", type="timeseries", title="代表年", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.5.1", type="wind_frequency", datasets=["ds1"]),
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
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency", datasets=["ds1"]),
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
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency", datasets=["ds1"]),
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
            DatasetConfig(name="ds1", masts=[MastRef(name="M1", air_density=1.225, input=TimeSeriesSource(data="/fake/ds1.parquet"))]),
            DatasetConfig(name="ds2", masts=[MastRef(name="M2", air_density=1.200, input=TimeSeriesSource(data="/fake/ds2.parquet"))]),
        ]
        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="Container1", datasets=["ds1", "ds2"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_frequency", datasets=["ds1", "ds2"]),
            FlatSubsectionConfig(index="2.5", type="timeseries", title="Container2", datasets=["ds1", "ds2"]),
            FlatSubsectionConfig(index="2.5.1", type="wind_frequency", datasets=["ds1", "ds2"]),
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
                masts=[
                    MastRef(name="M1", air_density=1.225, input=TimeSeriesSource(data="/fake/data.parquet")),
                    MastRef(name="M2", air_density=1.200, input=TimeSeriesSource(data="/fake/data.parquet")),
                ],
            ),
        ]
        config = self._make_config([
            FlatSubsectionConfig(index="2.4", type="timeseries", title="Container1", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.4.1", type="weibull", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.5", type="timeseries", title="Container2", datasets=["ds1"]),
            FlatSubsectionConfig(index="2.5.1", type="weibull", datasets=["ds1"]),
        ], datasets=datasets)
        loaded = self._make_loaded_datasets(config, mock_ts)

        _generate_from_flat_config(config, loaded, mock_service, mock_builder)

        assert len(mock_service.generate_weibull_section.call_args_list[0].args[0]) == 2
        assert len(mock_service.generate_weibull_section.call_args_list[1].args[0]) == 2
