"""Recommend report configuration use case.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-a-001-use-case-pattern
Compliance: Subdomain layout ✓ | Use Case ✓ | CLI Adapter Ready ✓
Description: Application use case for generating report configuration files

This module provides the use case for generating report configuration
files based on fill-heights data from both reconstruct-meso and
representative-year sources.
"""

import logging
from collections.abc import Sequence
from pathlib import Path

from cleanmast.subdomains.configuration.value_objects.fill_height_config import (
    load_fill_heights_config,
)
from cleanmast.subdomains.configuration.value_objects.representative_year import (
    RepresentativeYearMast,
    load_representative_year_config,
)
from cleanmast.subdomains.dataingestion.infrastructure.timeseries_io import (
    load_timeseries_parquet,
)
from cleanmast.subdomains.dataingestion.value_objects.time_range import TimeRange
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)
from cleanmast.subdomains.reporting.compute.air_density import (
    STANDARD_AIR_DENSITY,
    calculate_air_density,
)
from cleanmast.subdomains.reporting.model.report_config import (
    AnalysisWindow,
    DatasetConfig,
    FlatReportConfig,
    FlatSubsectionConfig,
    MastRef,
    MesoRef,
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

_FIFTY_YEAR_ANALYSIS_SUBSECTION_TYPES = [
    "iec_standards",
    "fifty_year_method1",
    "fifty_year_method2",
    "fifty_year_method3",
    "fifty_year_summary",
]


def _build_dataset_for_timeseries(
    project_path: Path,
    fill_heights_filename: str,
    report_data_subdir: str,
    dataset_name: str,
    fallback_air_density: float | None = None,
) -> DatasetConfig | None:
    """Build a dataset configuration from a fill-heights TOML file.

    Reads the specified fill-heights config, iterates over each mast,
    loads the corresponding parquet timeseries, calculates air density,
    and returns a DatasetConfig for the report catalog.

    Args:
        project_path: Path to the project directory.
        fill_heights_filename: Name of the fill-heights TOML file.
        report_data_subdir: Subdirectory name to use for the report data path.
        dataset_name: Name for the dataset in the catalog.
    Returns:
        DatasetConfig or None if the fill-heights file does not exist.

    Raises:
        FileNotFoundError: If a referenced parquet file does not exist.
        ValueError: If no valid masts are found.
    """
    fill_heights_path = project_path / fill_heights_filename
    if not fill_heights_path.exists():
        return None

    config = load_fill_heights_config(str(fill_heights_path))
    masts = config.masts
    mast_refs: list[MastRef] = []

    for mast in masts:
        mast_name = mast.name
        data_path = mast.output.data

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
            logger = logging.getLogger(__name__)
            if fallback_air_density is not None:
                logger.warning(
                    f"Cannot calculate air density for mast {mast_name}: {e}. "
                    f"Using fallback {fallback_air_density}"
                )
                air_density = fallback_air_density
            else:
                raise ValueError(
                    f"Cannot calculate air density for mast '{mast_name}'. "
                    f"Provide --air-density in config or pass a fallback value. "
                    f"Error: {e}"
                ) from e

        rel_data_path = f"./{report_data_subdir}/{mast_name}.parquet"

        mast_refs.append(MastRef(
            name=mast_name,
            air_density=round(air_density, 3),
            input=TimeSeriesSource(data=rel_data_path),
        ))

    if not mast_refs:
        return None

    return DatasetConfig(
        name=dataset_name,
        masts=mast_refs,
    )


def _build_subsections(
    reconstruct_meso_dataset: DatasetConfig | None,
    repyear_dataset: DatasetConfig | None,
    calibration_dataset: DatasetConfig | None,
) -> list[FlatSubsectionConfig]:
    """Build flat subsections with hardcoded indices.

    Index scheme:
      2.4 = meso (timeseries)
      2.5 = repyear (timeseries)
        2.5.1 = calibration (uses repyear_calibration dataset)
        2.5.2+ = other repyear analysis types
      2.6 = fifty_year_max_wind
    """
    subsections: list[FlatSubsectionConfig] = []

    if reconstruct_meso_dataset:
        subsections.append(FlatSubsectionConfig(
            index="2.4",
            type="timeseries",
            title="测风年风资源分析",
            datasets=[reconstruct_meso_dataset.name],
        ))
        for i, subtype in enumerate(_MESO_ANALYSIS_SUBSECTION_TYPES, start=1):
            subsections.append(FlatSubsectionConfig(
                index=f"2.4.{i}",
                type=subtype,
                datasets=[reconstruct_meso_dataset.name],
            ))

    if repyear_dataset:
        subsections.append(FlatSubsectionConfig(
            index="2.5",
            type="timeseries",
            title="代表年风资源分析",
            datasets=[repyear_dataset.name],
        ))
        # 2.5.1 = calibration (uncalibrated masts + calibrated mesos)
        if calibration_dataset:
            subsections.append(FlatSubsectionConfig(
                index="2.5.1",
                type="representative_year_calibration",
                datasets=[calibration_dataset.name],
            ))
        # 2.5.2+ = other repyear analysis types (skip first which is calibration)
        start_idx = 2 if calibration_dataset else 1
        for i, subtype in enumerate(
            _REP_ANALYSIS_SUBSECTION_TYPES[1:], start=start_idx,
        ):
            subsections.append(FlatSubsectionConfig(
                index=f"2.5.{i}",
                type=subtype,
                datasets=[repyear_dataset.name],
            ))

    fifty_year_dataset = reconstruct_meso_dataset or repyear_dataset
    if fifty_year_dataset:
        subsections.append(FlatSubsectionConfig(
            index="2.6",
            type="fifty_year_max_wind",
            title="五十年一遇最大风速",
            datasets=[fifty_year_dataset.name],
        ))
        for i, subtype in enumerate(_FIFTY_YEAR_ANALYSIS_SUBSECTION_TYPES, start=1):
            subsections.append(FlatSubsectionConfig(
                index=f"2.6.{i}",
                type=subtype,
                datasets=[fifty_year_dataset.name],
            ))

    return subsections


def _build_analysis_windows(
    masts: Sequence[RepresentativeYearMast],
) -> list[AnalysisWindow]:
    """Group masts with identical TimeRange into AnalysisWindow entries."""
    groups: dict[TimeRange, list[str]] = {}
    for m in masts:
        groups.setdefault(m.time_range, []).append(m.name)
    return [
        AnalysisWindow(target_masts=mast_names, time_range=tr)
        for tr, mast_names in groups.items()
    ]


def _build_reconstruct_meso_dataset(project_path: Path) -> DatasetConfig | None:
    """Build reconstruct_meso dataset from fill-heights config."""
    return _build_dataset_for_timeseries(
        project_path,
        "fill-heights-reconstruct-meso.toml",
        "reconstruct-meso-fill-heights",
        "reconstruct_meso",
        fallback_air_density=STANDARD_AIR_DENSITY,
    )


def _build_repyear_dataset(project_path: Path) -> DatasetConfig | None:
    """Build repyear dataset from fill-heights config enriched with representative-year.toml."""
    repyear_dataset = _build_dataset_for_timeseries(
        project_path,
        "fill-heights-representative-year.toml",
        "representative-year-fill-heights",
        "repyear",
        fallback_air_density=STANDARD_AIR_DENSITY,
    )

    if repyear_dataset:
        repyear_toml_path = project_path / "representative-year.toml"
        if repyear_toml_path.exists():
            repyear_config = load_representative_year_config(str(repyear_toml_path))
            masts = repyear_config.masts

            meso_name_to_masts: dict[str, list[str]] = {}
            for mast in masts:
                meso_name_to_masts.setdefault(
                    mast.meso_model.meso_name, []
                ).append(mast.name)

            meso_refs: list[MesoRef] = []
            for meso in repyear_config.mesos:
                target_masts = meso_name_to_masts.get(meso.name, [])
                if target_masts:
                    meso_refs.append(MesoRef(
                        input=meso.input,
                        target_masts=target_masts,
                        meso_name=meso.name,
                    ))

            if meso_refs:
                repyear_dataset = repyear_dataset.model_copy(update={"mesos": meso_refs})

            analysis_windows = _build_analysis_windows(masts)
            if analysis_windows:
                repyear_dataset = repyear_dataset.model_copy(update={"analysis_windows": analysis_windows})

    return repyear_dataset


def _build_calibration_dataset(
    reconstruct_meso_dataset: DatasetConfig | None,
    repyear_dataset: DatasetConfig | None,
) -> DatasetConfig | None:
    """Build calibration dataset combining uncalibrated masts with calibrated mesos."""
    if reconstruct_meso_dataset is None or repyear_dataset is None:
        return None
    return DatasetConfig(
        name="repyear_calibration",
        masts=reconstruct_meso_dataset.masts,
        mesos=repyear_dataset.mesos,
        analysis_windows=repyear_dataset.analysis_windows,
    )


def recommend_report(project_dir: str) -> Path:
    """Generate configuration for representative timeseries report.

    This use case:
    1. Reads fill-heights-reconstruct-meso.toml and
       fill-heights-representative-year.toml from the project directory
    2. For each mast in each config, loads the corresponding parquet file
    3. Calculates air density from mean temperature/pressure columns
    4. Generates rep-ts-report.toml config file in the flat format
       with [[datasets]] catalog and [[subsections]] with hierarchical indices

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

    reconstruct_meso_dataset = _build_reconstruct_meso_dataset(project_path)
    repyear_dataset = _build_repyear_dataset(project_path)
    calibration_dataset = _build_calibration_dataset(reconstruct_meso_dataset, repyear_dataset)

    if not reconstruct_meso_dataset and not repyear_dataset:
        raise ValueError(
            "No valid masts found for report configuration. "
            "Ensure fill-heights configuration files exist and contain valid masts."
        )

    datasets: list[DatasetConfig] = []
    if reconstruct_meso_dataset:
        datasets.append(reconstruct_meso_dataset)
    if repyear_dataset:
        datasets.append(repyear_dataset)
    if calibration_dataset:
        datasets.append(calibration_dataset)

    subsections = _build_subsections(
        reconstruct_meso_dataset, repyear_dataset, calibration_dataset,
    )
    report_config = FlatReportConfig(
        datasets=datasets,
        subsections=subsections,
    )

    output_path = project_path / "rep-ts-report.toml"
    report_config.to_toml(output_path)

    return output_path
