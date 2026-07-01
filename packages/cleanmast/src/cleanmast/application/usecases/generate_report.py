"""Generate report use case.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-a-001-use-case-pattern
Compliance: Subdomain layout ✓ | Use Case ✓ | CLI Adapter Ready ✓
Description: Application use case for generating representative timeseries reports

This module provides the use case for generating representative timeseries reports
from processed mast data.
"""

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable

from typst_ir import TypstHeading, TypstSection

from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.infrastructure import load_timeseries
from cleanmast.subdomains.dataingestion.value_objects.time_range import TimeRange
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)
from cleanmast.subdomains.reporting.api import ReportGenerationService
from cleanmast.subdomains.reporting.assemble.tree_builder import SectionNode
from cleanmast.subdomains.reporting.model.analysis_input import (
    RepresentativeYearCalibrationPayload,
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.model.report_config import (
    AtomCollection,
    FlatReportConfig,
)
from cleanmast.subdomains.reporting.protocols.report_builder import BuildResult
from cleanmast.subdomains.reporting.render.report_builder import (
    ReportBuilderService as ReportBuilder,
)

_SubsectionDispatch = Callable[[list[SingleMastAnalysisInput]], Any]


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
    """Pre-loaded dataset with per-mast data.

    Created by :func:`load_datasets` at the application boundary before
    report generation begins. Separates I/O from pure orchestration.

    Attributes:
        name: Dataset identifier
        mast_data: List of per-mast analysis inputs (each carries its own
            time series data via ``SingleMastAnalysisInput.time_series``)
    """
    name: str
    mast_data: list[SingleMastAnalysisInput]


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
        mast_data: list[SingleMastAnalysisInput] = []
        for mast_ref in ds.masts or []:
            resolved = base_dir / mast_ref.input.data
            if not resolved.exists():
                raise FileNotFoundError(
                    f"Dataset file not found for mast '{mast_ref.name}': {resolved}"
                )
            source = TimeSeriesSource(data=str(resolved))
            timeseries = load_timeseries(source, ".")
            input_data = service._create_analysis_input(
                timeseries, mast_ref.name, mast_ref.air_density
            )
            mast_data.append(input_data)
        mast_analysis_windows: dict[str, TimeRange] = {}
        for aw in ds.analysis_windows or []:
            for mast_name in aw.target_masts:
                mast_analysis_windows[mast_name] = aw.time_range
        # Attach calibration payloads from meso references
        if ds.mesos:
            meso_data: dict[str, TimeSeriesData] = {}
            for meso_ref in ds.mesos:
                resolved = base_dir / meso_ref.input.data
                if not resolved.exists():
                    raise FileNotFoundError(
                        f"Meso dataset file not found for '{meso_ref.meso_name}': {resolved}"
                    )
                source = TimeSeriesSource(data=str(resolved))
                meso_data[meso_ref.meso_name] = load_timeseries(source, ".")
            for i, input_data in enumerate(mast_data):
                for meso_ref in ds.mesos:
                    if input_data.mast_name in meso_ref.target_masts:
                        tr = mast_analysis_windows[input_data.mast_name]
                        payload = RepresentativeYearCalibrationPayload(
                            meso_time_series=meso_data[meso_ref.meso_name],
                            meso_name=meso_ref.meso_name,
                            sampling_period="10min",
                            analysis_start=tr.min,
                            analysis_end=tr.max,
                        )
                        mast_data[i] = replace(
                            input_data,
                            representative_year_calibration_payload=payload,
                        )
                        break
        loaded[ds.name] = LoadedDataset(
            name=ds.name,
            mast_data=mast_data,
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

    subsection_method_map: dict[str, _SubsectionDispatch] = {
        "air_density": service.generate_air_density_section,
        "representative_year_calibration": service.generate_representative_year_calibration_section,
        "wind_rose": service.generate_wind_rose_section,
        "vertical_profile": service.generate_vertical_profile_section,
        "wind_frequency": service.generate_wind_frequency_section,
        "weibull": service.generate_weibull_section,
        "turbulence": service.generate_turbulence_section,
        "temporal": service.generate_temporal_section,
        "fifty_year_max_wind": service.generate_fifty_year_max_wind_section,
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
            section = _handle_fifty_year_max_wind_flat(
                node, service, loaded_datasets,
            )
            if section is not None:
                return section  # ExtremeWindSection already renders with heading
            return HeadingSection(
                title=node.title or "Placeholder",
                subsections=[],
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
    subsection_method_map: dict[str, _SubsectionDispatch],
    loaded_datasets: dict[str, LoadedDataset],
) -> list[Any]:
    """Process a timeseries container node and return leaf sections.

    Each child receives only the masts from its own declared datasets.
    Siblings sharing identical dataset sets reuse cached aggregations.
    """
    if not node.children:
        return []

    input_cache: dict[frozenset[str], list[SingleMastAnalysisInput]] = {}
    wd_cache: dict[frozenset[str], bool] = {}

    def _aggregate(key: frozenset[str]) -> None:
        input_items: list[SingleMastAnalysisInput] = []
        any_has_wd = False
        for ds_name in key:
            loaded = loaded_datasets.get(ds_name)
            if loaded is None:
                continue
            for input_data in loaded.mast_data:
                input_items.append(input_data)
                if _has_wind_direction_sensors(input_data.time_series):
                    any_has_wd = True
        input_cache[key] = input_items
        wd_cache[key] = any_has_wd

    leaf_sections: list[Any] = []
    for child in node.children:
        ds_names = child.datasets if child.datasets is not None else (node.datasets or [])
        if not ds_names:
            leaf_sections.append(HeadingSection(title="Placeholder"))
            continue

        key = frozenset(ds_names)
        if key not in input_cache:
            _aggregate(key)

        input_items = input_cache[key]
        any_has_wd_sensors = wd_cache[key]

        subsection_type = child.type

        if subsection_type == "wind_rose" and not any_has_wd_sensors:
            leaf_sections.append(HeadingSection(title="Placeholder"))
            continue

        if subsection_type not in subsection_method_map:
            leaf_sections.append(HeadingSection(title="Placeholder"))
            continue

        method = subsection_method_map[subsection_type]
        section_result = method(input_items)

        if section_result is not None:
            leaf_sections.append(section_result)

    return leaf_sections


def _handle_fifty_year_max_wind_flat(
    node: SectionNode,
    service: ReportGenerationService,
    loaded_datasets: dict[str, LoadedDataset],
):
    """Handle fifty-year max wind section — returns ExtremeWindSection directly."""
    items: list[SingleMastAnalysisInput] = []
    for ds_name in node.datasets or []:
        loaded = loaded_datasets.get(ds_name)
        if loaded is not None:
            items.extend(loaded.mast_data)
    if not items:
        return None
    return service.generate_fifty_year_max_wind_section(items)
