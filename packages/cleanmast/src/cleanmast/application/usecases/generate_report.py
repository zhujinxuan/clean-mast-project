"""Generate report use case.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-a-001-use-case-pattern
Compliance: Subdomain layout ✓ | Use Case ✓ | CLI Adapter Ready ✓
Description: Application use case for generating representative timeseries reports

This module provides the use case for generating representative timeseries reports
from processed mast data.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from cleanmast.subdomains.assessment.application.services.report_generation_service import (
    ReportGenerationService,
)
from cleanmast.subdomains.assessment.domain.types import TypstHeading, TypstSection
from cleanmast.subdomains.assessment.domain.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.domain.value_objects.collections.atom_collection import (
    AtomCollection,
)
from cleanmast.subdomains.assessment.domain.value_objects.flat_report_config import (
    FlatReportConfig,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.tree_builder import SectionNode
from cleanmast.subdomains.assessment.infrastructure.report_builder import (
    AssessmentReportBuilder as ReportBuilder,
)
from cleanmast.subdomains.assessment.infrastructure.report_builder import (
    BuildResult,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.infrastructure import load_timeseries
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)


@dataclass(frozen=True)
class HeadingSection:
    """Minimal section that renders only a heading (no content)."""

    title: str
    atoms: AtomCollection = field(default_factory=lambda: AtomCollection.from_dict({}))
    subsections: list[Any] = field(default_factory=list)

    def render_ir(self, images_dir: Path) -> TypstSection:
        return TypstSection(
            heading=TypstHeading(text=self.title),
            body=[],
            subsections=[s.render_ir(images_dir) for s in self.subsections],
        )


@dataclass(frozen=True)
class LoadedDataset:
    """Pre-loaded dataset: resolved path, timeseries, and mast inputs.

    Created by :func:`load_datasets` at the application boundary before
    report generation begins. Separates I/O from pure orchestration.
    """
    path: Path
    timeseries: TimeSeriesData
    mast_inputs: list[tuple[SingleMastAnalysisInput, SingleMastMeta]]


def generate_report(config_path: str) -> BuildResult:
    """Generate representative timeseries report from config.

    This use case:
    1. Reads the TOML config file from the given path
    2. For each section, iterates over timeseries subsections and their nested leaf subsections
    3. Uses ReportGenerationService to process data and create report sections
    4. Generates a complete Typst report with images and tables using IR-based rendering

    Prerequisites:
    - Config file (rep-ts-report.toml) must exist at the given path
    - Parquet files must exist at paths specified in config

    Args:
        config_path: Path to the TOML config file (e.g., rep-ts-report.toml)

    Returns:
        Dict with report generation results including paths

    Raises:
        FileNotFoundError: If config file not found
        ValueError: If a document section contains a non-timeseries subsection directly
    """
    config_file_path = Path(config_path)
    base_dir = config_file_path.parent.resolve()

    if not config_file_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. "
            "Run 'recommend report timeseries' command first."
        )

    config = FlatReportConfig.from_toml(config_file_path)
    output_dir = base_dir / "rep-ts"
    output_dir.mkdir(parents=True, exist_ok=True)
    service = ReportGenerationService(project_dir=base_dir)
    report_title = (config.tree[0].title or "风资源评估报告") if config.tree else "风资源评估报告"
    builder = ReportBuilder(report_title, output_dir)
    loaded = load_datasets(config, base_dir, service)
    return _generate_from_flat_config(config, loaded, service, builder)


def load_datasets(
    config: FlatReportConfig,
    base_dir: Path,
    service: ReportGenerationService,
) -> dict[str, LoadedDataset]:
    """Resolve paths, load timeseries, build mast inputs — once, at the boundary.

    All dataset I/O happens here. Downstream functions receive
    :class:`LoadedDataset` objects — no path resolution, no ``load_timeseries``.

    Args:
        config: Flat report config with dataset definitions.
        base_dir: Directory containing the config file.
        service: Report generation service (for ``_create_analysis_input``).

    Returns:
        Mapping of dataset name → LoadedDataset.

    Raises:
        FileNotFoundError: If any dataset path does not exist.

    ADR-GUARDRAILS: ddd-a-001-use-case-pattern
    I/O at use case boundary — domain logic is I/O-free.
    """
    loaded: dict[str, LoadedDataset] = {}
    for ds in config.datasets:
        resolved = base_dir / ds.path
        if not resolved.exists():
            raise FileNotFoundError(
                f"Dataset file not found: {resolved}"
            )
        source = TimeSeriesSource(data=str(resolved))
        timeseries = load_timeseries(source, ".")
        mast_inputs: list[tuple[SingleMastAnalysisInput, SingleMastMeta]] = []
        for mast_ref in ds.masts:
            meta = SingleMastMeta(
                mast_name=mast_ref.name,
                air_density=mast_ref.air_density,
                width="80%",
            )
            input_data = service._create_analysis_input(
                timeseries, meta, mast_ref.air_density
            )
            mast_inputs.append((input_data, meta))
        loaded[ds.name] = LoadedDataset(
            path=resolved,
            timeseries=timeseries,
            mast_inputs=mast_inputs,
        )
    return loaded


def _has_wind_direction_sensors(timeseries: TimeSeriesData) -> bool:
    """Check if timeseries has wind direction sensors.

    Args:
        timeseries: TimeSeriesData with sensors

    Returns:
        True if wind direction sensors exist
    """
    wd_sensors = [
        s for s in timeseries.sensors
        if s.sensor_type == "WindDirection" and s.stat_type == "avg"
    ]
    return len(wd_sensors) > 0


def _generate_from_flat_config(
    config: FlatReportConfig,
    loaded_datasets: dict[str, LoadedDataset],
    service: ReportGenerationService,
    builder: ReportBuilder,
) -> BuildResult:
    """Generate report from flat config tree.

    Iterates the hierarchical tree produced by config.tree, dispatches leaf
    subsections to existing service methods, and wraps children under
    HeadingSection containers.

    Args:
        config: FlatReportConfig with datasets and hierarchical subsections.
        loaded_datasets: Pre-loaded datasets from :func:`load_datasets`.
        service: ReportGenerationService instance.
        builder: ReportBuilder instance.

    Returns:
        BuildResult from the report builder.
    """
    all_sections: list = []

    subsection_method_map: dict[str, tuple[bool, Callable]] = {
        "air_density": (True, service.generate_air_density_section),
        "representative_year_calibration": (True, service.generate_representative_year_calibration_section),
        "wind_rose": (False, service.generate_wind_rose_section),
        "vertical_profile": (True, service.generate_vertical_profile_section),
        "wind_frequency": (True, service.generate_wind_frequency_section),
        "weibull": (True, service.generate_weibull_section),
        "turbulence": (True, service.generate_turbulence_section),
        "temporal": (True, service.generate_temporal_section),
        "fifty_year_max_wind": (True, service.generate_fifty_year_max_wind_section),
    }

    def _walk_node(node: SectionNode, depth: int = 0) -> HeadingSection:
        """Recursively walk a section node and return a HeadingSection."""
        if depth > 10:
            return HeadingSection(
                title=node.title or "Placeholder",
                subsections=[],
            )

        if node.is_placeholder:
            subsections: list[Any] = []
            for child in node.children:
                result = _walk_node(child, depth + 1)
                subsections.append(result)
            return HeadingSection(
                title=node.title or "Placeholder",
                subsections=subsections,
            )

        if node.type == "timeseries":
            leaf_sections = _process_flat_timeseries_node(
                node, service, subsection_method_map, loaded_datasets,
            )
            return HeadingSection(
                title=node.title or "Placeholder",
                subsections=leaf_sections,
            )

        if node.type == "fifty_year_max_wind":
            result = _handle_fifty_year_max_wind_flat(
                node, service, loaded_datasets,
            )
            return HeadingSection(
                title=node.title or "Placeholder",
                subsections=result,
            )

        return HeadingSection(
            title=node.title or "Placeholder",
            subsections=[],
        )

    for node in config.tree:
        result = _walk_node(node, depth=0)
        if result is not None:
            all_sections.append(result)

    for section in all_sections:
        builder.add_section(section)

    return builder.build()


def _process_flat_timeseries_node(
    node: SectionNode,
    service: ReportGenerationService,
    subsection_method_map: dict[str, tuple[bool, Callable]],
    loaded_datasets: dict[str, LoadedDataset],
) -> list[Any]:
    """Process a timeseries container node and return leaf sections."""
    if not node.children:
        return []

    ts_items: list[tuple[TimeSeriesData, SingleMastMeta]] = []
    input_items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]] = []
    any_has_wd_sensors = False

    for ds_name in node.datasets or []:
        loaded = loaded_datasets.get(ds_name)
        if loaded is None:
            continue
        ts = loaded.timeseries
        for input_data, meta in loaded.mast_inputs:
            ts_items.append((ts, meta))
            input_items.append((input_data, meta))
            if _has_wind_direction_sensors(ts):
                any_has_wd_sensors = True

    leaf_sections: list[Any] = []
    for child in node.children:
        subsection_type = child.type

        if subsection_type == "wind_rose" and not any_has_wd_sensors:
            leaf_sections.append(HeadingSection(title="Placeholder"))
            continue

        if subsection_type not in subsection_method_map:
            leaf_sections.append(HeadingSection(title="Placeholder"))
            continue

        requires_input_data, method = subsection_method_map[subsection_type]

        if requires_input_data:
            section_result = method(input_items)
        else:
            section_result = method(ts_items)

        if section_result is not None:
            leaf_sections.append(section_result)

    return leaf_sections


def _handle_fifty_year_max_wind_flat(
    node: SectionNode,
    service: ReportGenerationService,
    loaded_datasets: dict[str, LoadedDataset],
) -> list[Any]:
    fifty_input_items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]] = []
    for ds_name in node.datasets or []:
        loaded = loaded_datasets.get(ds_name)
        if loaded is not None:
            fifty_input_items.extend(loaded.mast_inputs)

    if not fifty_input_items:
        return []

    result = service.generate_fifty_year_max_wind_section(fifty_input_items)

    type_to_field = {
        "iec_standards": "iec_standards",
        "fifty_year_method1": "method1",
        "fifty_year_method2": "method2",
        "fifty_year_method3": "method3",
        "fifty_year_summary": "summary",
    }

    subsections: list[Any] = []
    for child in node.children:
        field_name = type_to_field.get(child.type)
        if field_name:
            subsections.append(getattr(result, field_name))
        else:
            subsections.append(HeadingSection(title="Placeholder"))

    return subsections
