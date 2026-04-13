"""Recommend report configuration use case.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-a-001-use-case-pattern
Compliance: Subdomain layout ✓ | Use Case ✓ | CLI Adapter Ready ✓
Description: Application use case for generating report configuration files

This module provides the use case for generating report configuration
files based on fill-heights data from both reconstruct-meso and
representative-year sources.
"""

from pathlib import Path

import tomli
import tomli_w

from cleanmast.subdomains.assessment.domain.value_objects.air_density import (
    calculate_air_density,
)
from cleanmast.subdomains.dataingestion.infrastructure.timeseries_io import (
    load_timeseries_parquet,
)
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)

_MESO_ANALYSIS_SUBSECTION_TYPES = [
    "air_density",
    "temporal",
    "wind_rose",
    "vertical_profile",
    "wind_frequency",
    "weibull",
    "turbulence",
]

_REP_ANALYSIS_SUBSECTION_TYPES = [
    "representative_year_calibration",
    "temporal",
    "wind_rose",
    "wind_frequency",
    "weibull",
]


def _build_analysis_subsections(type_list: list[str]) -> list[dict]:
    return [{"type": t} for t in type_list]


def _build_masts_for_timeseries(
    project_path: Path,
    fill_heights_filename: str,
    report_data_subdir: str,
) -> list[dict]:
    """Build report mast configurations from a fill-heights TOML file.

    Reads the specified fill-heights config, iterates over each mast,
    loads the corresponding parquet timeseries, calculates air density,
    and returns a list of mast dicts ready for report configuration.

    Args:
        project_path: Path to the project directory.
        fill_heights_filename: Name of the fill-heights TOML file.
        report_data_subdir: Subdirectory name to use for the report data path.

    Returns:
        List of mast dictionaries with keys ``name``, ``air_density``,
        and ``input`` (containing the relative data path).

    Raises:
        FileNotFoundError: If a referenced parquet file does not exist.
    """
    fill_heights_path = project_path / fill_heights_filename
    if not fill_heights_path.exists():
        return []

    with open(fill_heights_path, "rb") as f:
        config = tomli.load(f)

    masts = config.get("masts", [])
    report_masts: list[dict] = []
    for mast in masts:
        mast_name = mast.get("name")
        if not mast_name:
            continue

        data_path = mast.get("output", {}).get("data", "")
        if not data_path:
            continue

        parquet_path = project_path / data_path
        if not parquet_path.exists():
            raise FileNotFoundError(
                f"Parquet file not found for mast {mast_name}: {parquet_path}"
            )

        try:
            source = TimeSeriesSource(data=data_path, sensors=None)
            time_series_data = load_timeseries_parquet(source, str(project_path))
            air_density = calculate_air_density(time_series_data)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to calculate air density from timeseries, using default 1.225: {e}"
            )
            air_density = 1.225

        rel_data_path = f"./{report_data_subdir}/{mast_name}.parquet"
        report_masts.append({
            "name": mast_name,
            "air_density": round(air_density, 3),
            "input": {"data": rel_data_path},
        })

    return report_masts


def recommend_report(project_dir: str) -> Path:
    """Generate configuration for representative timeseries report.

    This use case:
    1. Reads fill-heights-reconstruct-meso.toml and
       fill-heights-representative-year.toml from the project directory
    2. For each mast in each config, loads the corresponding parquet file
    3. Calculates air density from mean temperature/pressure columns
    4. Generates rep-ts-report.toml config file in the new nested format
       with a single document.section containing two timeseries subsections
       (测风年 and 代表年), each with masts and all 6 analysis subsections

    Prerequisites:
    - fill-heights-representative-year.toml must exist in project directory
    - Parquet files must exist in the referenced subdirectories
    - fill-heights-reconstruct-meso.toml is optional; if absent, only the
      代表年 subsection is generated

    Args:
        project_dir: Path to project directory containing config files

    Returns:
        Path to generated config file

    Raises:
        FileNotFoundError: If required fill-heights config or parquet files
            are not found
        ValueError: If no valid masts found for report configuration
    """
    project_path = Path(project_dir)

    meso_masts = _build_masts_for_timeseries(
        project_path,
        "fill-heights-reconstruct-meso.toml",
        "reconstruct-meso-fill-heights",
    )
    rep_masts = _build_masts_for_timeseries(
        project_path,
        "fill-heights-representative-year.toml",
        "representative-year-fill-heights",
    )

    if not meso_masts and not rep_masts:
        raise ValueError(
            "No valid masts found for report configuration. "
            "Ensure fill-heights configuration files exist and contain valid masts."
        )

    subsections: list[dict] = []
    if meso_masts:
        subsections.append({
            "type": "timeseries",
            "title": "测风年风资源分析",
            "masts": meso_masts,
            "subsections": _build_analysis_subsections(_MESO_ANALYSIS_SUBSECTION_TYPES),
        })
    if rep_masts:
        subsections.append({
            "type": "timeseries",
            "title": "代表年风资源分析",
            "masts": rep_masts,
            "subsections": _build_analysis_subsections(_REP_ANALYSIS_SUBSECTION_TYPES),
        })

    fifty_year_masts = meso_masts if meso_masts else rep_masts
    if fifty_year_masts:
        subsections.append({
            "type": "fifty_year_max_wind",
            "title": "五十年一遇最大风速",
            "masts": fifty_year_masts,
        })

    report_config = {
        "document": {
            "section": [
                {
                    "title": "风资源分析",
                    "subsections": subsections,
                }
            ],
        },
    }

    output_path = project_path / "rep-ts-report.toml"
    with open(output_path, "wb") as f:
        tomli_w.dump(report_config, f)

    return output_path
