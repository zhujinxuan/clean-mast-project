"""Generate report use case.

Description: Application use case for generating representative timeseries reports

This module provides the use case for generating representative timeseries reports
from processed mast data.
"""

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, cast, get_args

import polars as pl
from typst_ir import TypstHeading, TypstSection

from cleanmast.shared.timeseries import TimeSeriesData
from cleanmast.shared.timeseries.io import TimeSeriesRepository
from cleanmast.shared.timeseries.time_range import TimeRange
from cleanmast.shared.timeseries.time_series_source import TimeSeriesSource
from cleanmast.subdomains.configuration.model.report_config import (
    FlatReportConfig,
    SubsectionType,
)
from cleanmast.subdomains.reporting.api import ReportGenerationService
from cleanmast.subdomains.reporting.assemble.tree_builder import build_section_tree
from cleanmast.subdomains.reporting.model.analysis_input import (
    RepresentativeYearCalibrationPayload,
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.model.extreme_wind_gust_factor import (
    ExtremeWindGustFactor,
)
from cleanmast.subdomains.reporting.model.section_node import SectionNode
from cleanmast.subdomains.reporting.protocols.report_builder import BuildResult
from cleanmast.subdomains.reporting.render.report_builder import (
    ReportBuilderService as ReportBuilder,
)

_SubsectionDispatch = Callable[[list[SingleMastAnalysisInput]], Any]


@dataclass(frozen=True)
class HeadingSection:
    """Minimal section that renders only a heading (no content)."""

    title: str
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
        analysis_windows: Per-mast analysis time window bounds (mast_name → TimeRange).
            Derived from the dataset's ``analysis_windows`` configuration.
            Used downstream to clip timeseries to the analysis window before dispatch.
    """
    name: str
    mast_data: list[SingleMastAnalysisInput]
    analysis_windows: dict[str, TimeRange] = field(default_factory=dict)


def generate_report(config_path: str, repo: TimeSeriesRepository) -> BuildResult:
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
        repo: TimeSeriesRepository used to load dataset timeseries

    Returns:
        Dict with report generation results including paths

    Raises:
        FileNotFoundError: If config file not found
        ValueError: If a document section contains a non-timeseries subsection directly
    """
    from cleanmast.subdomains.configuration import load_config
    from cleanmast.subdomains.configuration.model.report_config import (
        FlatReportConfig,
    )

    base_dir = Path(config_path).parent.resolve()
    config = load_config(FlatReportConfig, config_path)
    output_dir = base_dir / "rep-ts"
    output_dir.mkdir(parents=True, exist_ok=True)
    service = ReportGenerationService(project_dir=base_dir)
    tree = build_section_tree(config.subsections)
    report_title = (tree[0].title or "风资源评估报告") if tree else "风资源评估报告"
    builder = ReportBuilder(report_title, output_dir)
    loaded = load_datasets(config, base_dir, service, repo)
    return _generate_from_flat_config(config, loaded, service, builder)


def load_datasets(
    config: FlatReportConfig,
    base_dir: Path,
    service: ReportGenerationService,
    repo: TimeSeriesRepository,
) -> dict[str, LoadedDataset]:
    """Resolve paths, load timeseries, build mast inputs — once, at the boundary.

    All dataset I/O happens here. Downstream functions receive
    :class:`LoadedDataset` objects — no path resolution, no repository access.

    Args:
        config: Flat report config with dataset definitions.
        base_dir: Directory containing the config file.
        service: Report generation service (for ``_create_analysis_input``).
        repo: TimeSeriesRepository used to load dataset timeseries.

    Returns:
        Mapping of dataset name → LoadedDataset.

    Raises:
        FileNotFoundError: If any dataset path does not exist.

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
            timeseries = repo.load(source, ".")
            # Map config ExtremeWindGustFactor → reporting ExtremeWindGustFactor
            # at the composition boundary, mirroring the turbulence_heights handoff.
            reporting_gust_factors = [
                ExtremeWindGustFactor(
                    height=gf.height, gust_factor=gf.gust_factor
                )
                for gf in mast_ref.extreme_wind_gust_factors
            ]
            input_data = service._create_analysis_input(
                timeseries,
                mast_ref.name,
                mast_ref.air_density,
            turbulence_heights=mast_ref.turbulence_heights,
            wind_frequency_heights=mast_ref.wind_frequency_heights,
            weibull_heights=mast_ref.weibull_heights,
            representative_year_heights=mast_ref.representative_year_heights,
            wind_rose_heights=mast_ref.wind_rose_heights,
            temporal_heights=mast_ref.temporal_heights,
            extreme_wind_10min_heights=mast_ref.extreme_wind_10min_heights,
            extreme_wind_3s_heights=mast_ref.extreme_wind_3s_heights,
            extreme_wind_gust_factors=reporting_gust_factors,
            )
            mast_data.append(input_data)
        mast_analysis_windows: dict[str, TimeRange] = {}
        for aw in ds.analysis_windows:
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
                meso_data[meso_ref.meso_name] = repo.load(source, ".")
            for i, input_data in enumerate(mast_data):
                for meso_ref in ds.mesos:
                    if input_data.mast_name in meso_ref.target_masts:
                        tr = mast_analysis_windows[input_data.mast_name]
                        payload = RepresentativeYearCalibrationPayload(
                            meso_time_series=meso_data[meso_ref.meso_name],
                            meso_name=meso_ref.meso_name,
                            sampling_period="10min",
                            rep_year_start=tr.min,
                            rep_year_end=tr.max,
                        )
                        mast_data[i] = replace(
                            input_data,
                            representative_year_calibration_payload=payload,
                        )
                        break
        loaded[ds.name] = LoadedDataset(
            name=ds.name,
            mast_data=mast_data,
            analysis_windows=mast_analysis_windows,
        )
    return loaded


def _clip_input_to_window(
    input_data: SingleMastAnalysisInput,
    window: TimeRange,
    dataset_name: str,
) -> SingleMastAnalysisInput:
    """Clip a mast timeseries to the given analysis window.

    Parquet timestamps are tz-naive, so the window bounds are also
    stripped of timezone info before comparison.

    Args:
        input_data: Single-mast analysis input with timeseries data.
        window: Analysis time window bounds.
        dataset_name: Name of the dataset the input belongs to (for errors).

    Returns:
        New SingleMastAnalysisInput with time_series clipped to the window.

    Raises:
        ValueError: If the filtered DataFrame is empty (no data in window).
    """
    start = window.min.replace(tzinfo=None)
    end = window.max.replace(tzinfo=None)
    df = input_data.time_series.df
    filtered = df.filter(
        (pl.col("timestamp") >= start) & (pl.col("timestamp") <= end)
    )
    if filtered.is_empty():
        raise ValueError(
            f"Mast '{input_data.mast_name}' in dataset '{dataset_name}' has no "
            f"data within analysis window [{start}, {end}]; "
            f"data spans [{df['timestamp'].min()}, {df['timestamp'].max()}]"
        )
    return replace(
        input_data,
        time_series=replace(input_data.time_series, df=filtered),
    )


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

    # Dispatch contract: every SubsectionType member is accounted for — either
    # in this map or in one of the exclusion sets below. Drift fails loudly
    # here instead of producing a silent placeholder section in the report.
    subsection_method_map: dict[SubsectionType, _SubsectionDispatch] = {
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

    # Container-node types: grouping headings handled by _walk_node directly,
    # never dispatched (e.g. "timeseries" = analysis set from mast timeseries).
    _CONTAINER_TYPES: frozenset[str] = frozenset({"timeseries"})
    # Valid config types with no section implementation yet; fall through to a
    # placeholder by design (see test_generate_report: "not in method map yet").
    _UNIMPLEMENTED_TYPES: frozenset[str] = frozenset({
        "iec_standards",
        "fifty_year_method1",
        "fifty_year_method2",
        "fifty_year_method3",
        "fifty_year_summary",
    })
    _renderable = set(get_args(SubsectionType)) - _CONTAINER_TYPES - _UNIMPLEMENTED_TYPES
    assert set(subsection_method_map) == _renderable, (
        f"Dispatch drift: missing={_renderable - set(subsection_method_map)}, "
        f"extra={set(subsection_method_map) - _renderable}"
    )

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

    tree = build_section_tree(config.subsections)
    for node in tree:
        result = _walk_node(node, depth=0)
        if result is not None:
            all_sections.append(result)

    for section in all_sections:
        builder.add_section(section)

    return builder.build()


def _process_flat_timeseries_node(
    node: SectionNode,
    service: ReportGenerationService,
    subsection_method_map: dict[SubsectionType, _SubsectionDispatch],
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
    windows_cache: dict[frozenset[str], dict[str, tuple[TimeRange, str]]] = {}

    def _aggregate(key: frozenset[str]) -> None:
        input_items: list[SingleMastAnalysisInput] = []
        any_has_wd = False
        merged_windows: dict[str, tuple[TimeRange, str]] = {}
        for ds_name in key:
            loaded = loaded_datasets.get(ds_name)
            if loaded is None:
                continue
            for input_data in loaded.mast_data:
                input_items.append(input_data)
                if _has_wind_direction_sensors(input_data.time_series):
                    any_has_wd = True
            merged_windows.update(
                {mast: (tr, ds_name) for mast, tr in loaded.analysis_windows.items()}
            )
        input_cache[key] = input_items
        wd_cache[key] = any_has_wd
        windows_cache[key] = merged_windows

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

        # Clip mast timeseries to their analysis windows (exempt: calibration)
        if subsection_type != "representative_year_calibration":
            child_windows = windows_cache.get(key, {})
            input_items = [
                _clip_input_to_window(i, *child_windows[i.mast_name])
                if i.mast_name in child_windows
                else i
                for i in input_items
            ]

        if subsection_type == "wind_rose" and not any_has_wd_sensors:
            leaf_sections.append(HeadingSection(title="Placeholder"))
            continue

        if subsection_type not in subsection_method_map:
            leaf_sections.append(HeadingSection(title="Placeholder"))
            continue

        # Guarded by the `not in` check above — key is a valid map member.
        method = subsection_method_map[cast(SubsectionType, subsection_type)]
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
