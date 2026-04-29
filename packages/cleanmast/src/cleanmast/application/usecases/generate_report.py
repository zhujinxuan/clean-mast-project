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

from cleanmast.infrastructure.path_utils import to_posix_path
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
from cleanmast.subdomains.assessment.domain.value_objects.rep_ts_report_config import (
    CONTAINER_SUBSECTION_TYPES,
    RepTsReportConfig,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.infrastructure.report_builder import (
    AssessmentReportBuilder as ReportBuilder,
)
from cleanmast.subdomains.assessment.infrastructure.report_builder import (
    BuildResult,
)
from cleanmast.subdomains.dataingestion.entities.time_series_data import TimeSeriesData
from cleanmast.subdomains.dataingestion.infrastructure import load_timeseries


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
    base_dir = config_file_path.parent

    if not config_file_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. "
            "Run 'recommend report timeseries' command first."
        )

    config = RepTsReportConfig.from_toml(config_file_path)

    output_dir = base_dir / "rep-ts"
    output_dir.mkdir(parents=True, exist_ok=True)

    service = ReportGenerationService(project_dir=base_dir)
    report_title = (
        config.document.sections[0].title
        if config.document.sections
        else "风资源评估报告"
    )
    builder = ReportBuilder(report_title, output_dir)

    # Storage for all sections (added in canonical order per leaf subsection)
    all_sections: list = []

    # Build subsection type → method mapping
    # Each entry is a tuple of (requires_input_data, method)
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

    # Process each document section
    for section in config.document.sections:
        for subsection in section.subsections:
            if subsection.type not in CONTAINER_SUBSECTION_TYPES:
                raise ValueError(
                    f"Document sections may only contain container subsections ("
                    f"{', '.join(sorted(CONTAINER_SUBSECTION_TYPES))}), "
                    f"got '{subsection.type}'. Move analysis subsections inside a timeseries container."
                )
            if not subsection.masts:
                continue

            if subsection.type == "fifty_year_max_wind":
                fifty_input_items: list[tuple[SingleMastAnalysisInput, SingleMastMeta]] = []
                for mast in subsection.masts:
                    timeseries = load_timeseries(mast.input, to_posix_path(base_dir))
                    meta = SingleMastMeta(
                        mast_name=mast.name,
                        air_density=mast.air_density,
                        width="80%",
                    )
                    input_data = service._create_analysis_input(timeseries, meta, mast.air_density)
                    fifty_input_items.append((input_data, meta))

                section_result = service.generate_fifty_year_max_wind_section(fifty_input_items)
                if section_result is not None:
                    all_sections.append(section_result)
                continue

            if not subsection.subsections:
                continue

            leaf_sections: list[TypstSection] = []

            # Collect data from all masts for multi-mast subsection generation
            ts_items: list[tuple[TimeSeriesData, SingleMastMeta]] = []
            input_items = []
            any_has_wd_sensors = False

            for mast in subsection.masts:
                timeseries = load_timeseries(mast.input, to_posix_path(base_dir))
                meta = SingleMastMeta(
                    mast_name=mast.name,
                    air_density=mast.air_density,
                    width="80%",
                )
                input_data = service._create_analysis_input(timeseries, meta, mast.air_density)
                if _has_wind_direction_sensors(timeseries):
                    any_has_wd_sensors = True

                ts_items.append((timeseries, meta))
                input_items.append((input_data, meta))

            for leaf_subsection in subsection.subsections:
                subsection_type = leaf_subsection.type

                # Special case: wind_rose requires wind direction sensors
                if subsection_type == "wind_rose" and not any_has_wd_sensors:
                    continue

                if subsection_type not in subsection_method_map:
                    continue

                requires_input_data, method = subsection_method_map[subsection_type]

                if requires_input_data:
                    section_result = method(input_items)
                else:
                    section_result = method(ts_items)

                if section_result is not None:
                    leaf_sections.append(section_result)

            if leaf_sections:
                all_sections.append(HeadingSection(
                    title=subsection.title or "",
                    subsections=leaf_sections,
                ))

    # Add all sections to builder
    for section in all_sections:
        builder.add_section(section)

    return builder.build()


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
