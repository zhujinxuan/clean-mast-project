"""Generate report use case.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-a-001-use-case-pattern
Compliance: Subdomain layout ✓ | Use Case ✓ | CLI Adapter Ready ✓
Description: Application use case for generating representative timeseries reports

This module provides the use case for generating representative timeseries reports
from processed mast data.
"""

from pathlib import Path

from cleanmast.infrastructure.path_utils import to_posix_path
from cleanmast.infrastructure.typst_ir.serializer import serialize
from cleanmast.subdomains.assessment.application.services.report_generation_service import (
    ReportGenerationService,
)
from cleanmast.subdomains.assessment.domain.value_objects.rep_ts_report_config import (
    RepTsReportConfig,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.infrastructure.compiler import (
    compile_typst_to_docx,
    compile_typst_to_pdf,
)
from cleanmast.subdomains.assessment.infrastructure.report_builder import (
    AssessmentReportBuilder as ReportBuilder,
)
from cleanmast.subdomains.assessment.infrastructure.report_builder import (
    BuildResult,
)
from cleanmast.subdomains.dataingestion.infrastructure import load_timeseries


def generate_report(
    config_path: str,
    no_pdf: bool = False,
    no_docx: bool = False,
    use_ir_path: bool = True,
) -> BuildResult:
    """Generate representative timeseries report from config.

    This use case:
    1. Reads the TOML config file from the given path
    2. For each mast, loads the parquet file specified in config
    3. Uses ReportGenerationService to process data and create report sections
    4. Generates a complete Typst report with images and tables

    Prerequisites:
    - Config file (rep-ts-report.toml) must exist at the given path
    - Parquet files must exist at paths specified in config

    Args:
        config_path: Path to the TOML config file (e.g., rep-ts-report.toml)
        no_pdf: Skip PDF generation
        no_docx: Skip DOCX generation
        use_ir_path: Use new IR-based path with serialization at boundary
            (default: True). When True, uses build_typst() + serialize().
            When False, uses the legacy build() path.

    Returns:
        Dict with report generation results including paths

    Raises:
        FileNotFoundError: If config file not found
        ValueError: If no masts found in config
    """
    config_file_path = Path(config_path)
    base_dir = config_file_path.parent

    if not config_file_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. "
            "Run 'recommend report timeseries' command first."
        )

    config = RepTsReportConfig.from_toml(config_file_path)

    masts_config = config.masts
    if not masts_config:
        raise ValueError("No masts found in config file")

    output_dir = base_dir / "rep-ts"
    output_dir.mkdir(parents=True, exist_ok=True)

    service = ReportGenerationService()
    builder = ReportBuilder("代表年测风报告", output_dir)

    # Storage for all sections (added in canonical order per mast)
    all_sections: list = []

    for mast in masts_config:
        mast_name = mast.name
        air_density = mast.air_density

        timeseries = load_timeseries(mast.input, to_posix_path(base_dir))

        meta = SingleMastMeta(
            mast_name=mast_name,
            air_density=air_density,
            caption=f"{mast_name} 测风数据分析",
            width="80%",
        )

        # Create input_data once per mast for efficiency
        input_data = service._create_analysis_input(timeseries, meta, air_density)

        # Check for wind direction sensors (needed for wind_rose)
        wd_sensors = [
            s for s in timeseries.sensors
            if s.sensor_type == "WindDirection" and s.stat_type == "avg"
        ]
        has_wd_sensors = len(wd_sensors) > 0

        # 1. Monthly Wind Section
        if config.subsections.monthly_wind:
            wind_section = service.generate_monthly_wind_section(timeseries, meta)
            all_sections.append(wind_section)

        # 2. Monthly Power Section
        if config.subsections.monthly_power:
            power_section = service.generate_monthly_power_section(
                timeseries, meta, air_density
            )
            all_sections.append(power_section)

        # 3. Wind Rose Section (requires wind direction sensors)
        if config.subsections.wind_rose and has_wd_sensors:
            wind_rose_section = service.generate_wind_rose_section(timeseries, meta)
            all_sections.append(wind_rose_section)

        # 4. Vertical Profile Section
        if config.subsections.vertical_profile:
            vertical_profile_section = service.generate_vertical_profile_section(
                input_data, meta
            )
            all_sections.append(vertical_profile_section)

        # 5. Wind Frequency Section
        if config.subsections.wind_frequency:
            wind_frequency_section = service.generate_wind_frequency_section(
                input_data, meta
            )
            all_sections.append(wind_frequency_section)

        # 6. Weibull Section
        if config.subsections.weibull:
            weibull_section = service.generate_weibull_section(input_data, meta)
            all_sections.append(weibull_section)

        # 7. Turbulence Section
        if config.subsections.turbulence:
            turbulence_section = service.generate_turbulence_section(input_data, meta)
            all_sections.append(turbulence_section)

        # 8. Temporal Section
        if config.subsections.temporal:
            temporal_section = service.generate_temporal_section(input_data, meta)
            all_sections.append(temporal_section)

    # Add all sections to builder
    for section in all_sections:
        builder.add_section(section)

    if use_ir_path:
        doc = builder.build_typst(compile_pdf=False, compile_docx=False)
        typst_markup = serialize(doc)

        preamble = '''// Chinese text support
#set text(font: ("Linux Libertine", "Source Han Serif SC"))
#set heading(numbering: "1.")

'''
        full_markup = preamble + typst_markup

        report_path = output_dir / "report.typ"
        report_path.write_text(full_markup, encoding="utf-8")

        results: BuildResult = {"typ": report_path}
        compile_pdf = not no_pdf
        compile_docx = not no_docx

        if compile_pdf:
            try:
                results["pdf"] = compile_typst_to_pdf(report_path, output_dir)
            except RuntimeError as e:
                raise RuntimeError(
                    f"PDF generation failed: {e}\n"
                    f"Typst file created at: {report_path}"
                ) from e

        if compile_docx:
            try:
                results["docx"] = compile_typst_to_docx(report_path, output_dir)
            except (ImportError, RuntimeError) as e:
                results["docx_warning"] = str(e)

        return results

    return builder.build(
        compile_pdf=not no_pdf,
        compile_docx=not no_docx,
    )
