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
from typing import Any, cast

from cleanmast.subdomains.configuration import (
    AnalysisWindow,
    DatasetConfig,
    DiscoveredConfig,
    FlatReportConfig,
    FlatSubsectionConfig,
    MastRef,
    MesoRef,
    ProjectConfig,
    RepresentativeYearMast,
    SubsectionType,
)
from cleanmast.subdomains.dataingestion.infrastructure.timeseries_io import (
    load_timeseries,
    load_timeseries_parquet,
)
from cleanmast.subdomains.dataingestion.value_objects.sensor_column import (
    SensorColumn,
)
from cleanmast.subdomains.dataingestion.value_objects.time_range import TimeRange
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)
from cleanmast.subdomains.reporting.compute.air_density import (
    STANDARD_AIR_DENSITY,
    calculate_air_density,
)

_MESO_ANALYSIS_SUBSECTION_TYPES: list[SubsectionType] = [
    "air_density",
    "temporal",
    "wind_rose",
    "vertical_profile",
    "wind_frequency",
    "weibull",
    "turbulence",
]

_REP_ANALYSIS_SUBSECTION_TYPES: list[SubsectionType] = [
    "representative_year_calibration",
    "temporal",
    "wind_rose",
    "wind_frequency",
    "weibull",
]

_FIFTY_YEAR_ANALYSIS_SUBSECTION_TYPES: list[SubsectionType] = [
    "iec_standards",
    "fifty_year_method1",
    "fifty_year_method2",
    "fifty_year_method3",
    "fifty_year_summary",
]


def _discover_turbulence_heights(sensors: list[SensorColumn]) -> list[float]:
    """Heights with both WS avg and WS sd sensors within turbine range (120–160m)."""
    ws_avg = {
        s.height
        for s in sensors
        if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
    }
    ws_sd = {
        s.height
        for s in sensors
        if s.sensor_type == "WindSpeed" and s.stat_type == "sd"
    }
    candidate = ws_avg & ws_sd
    return sorted(h for h in candidate if 120.0 <= h <= 160.0)


def _build_dataset_for_timeseries(
    project_path: Path,
    discovered_config: DiscoveredConfig[Any],
    report_data_subdir: str,
    dataset_name: str,
    fallback_air_density: float | None = None,
) -> DatasetConfig | None:
    """Build a dataset configuration from a discovered fill-heights config.

    Iterates over each mast in the config, loads the corresponding parquet
    timeseries, calculates air density, and returns a DatasetConfig for the
    report catalog.

    Args:
        project_path: Path to the project directory.
        discovered_config: Discovered fill-heights configuration.
        report_data_subdir: Subdirectory name to use for the report data path.
        dataset_name: Name for the dataset in the catalog.
    Returns:
        DatasetConfig or None if the config has no valid masts.

    Raises:
        FileNotFoundError: If a referenced parquet file does not exist.
        ValueError: If no valid masts are found.
    """
    config = discovered_config.config
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
        turbulence_heights = _discover_turbulence_heights(
            time_series_data.sensors
        )

        mast_refs.append(MastRef(
            name=mast_name,
            air_density=round(air_density, 3),
            input=TimeSeriesSource(data=rel_data_path),
            turbulence_heights=turbulence_heights,
        ))

    if not mast_refs:
        return None

    return DatasetConfig(
        name=dataset_name,
        masts=mast_refs,
    )


def _build_subsections(
    filled_meso_dataset: DatasetConfig | None,
    repyear_dataset: DatasetConfig | None,
    calibration_dataset: DatasetConfig | None,
    original_meso_dataset: DatasetConfig | None,
) -> list[FlatSubsectionConfig]:
    """Build flat subsections with hardcoded indices.

    Index scheme:
      2.4 = meso (timeseries)
        2.4.4 vertical_profile and 2.4.7 turbulence use the original-heights
        dataset when available (fill-heights interpolation corrupts shear
        exponents and TI statistics); all other 2.4 children use the
        filled-heights dataset.
      2.5 = repyear (timeseries)
        2.5.1 = calibration (uses repyear_calibration dataset)
        2.5.2+ = other repyear analysis types
      2.6 = fifty_year_max_wind
    """
    subsections: list[FlatSubsectionConfig] = []

    if filled_meso_dataset:
        subsections.append(FlatSubsectionConfig(
            index="2.4",
            type="timeseries",
            title="测风年风资源分析",
            datasets=[filled_meso_dataset.name],
        ))
        for i, subtype in enumerate(_MESO_ANALYSIS_SUBSECTION_TYPES, start=1):
            if subtype in ("turbulence", "vertical_profile") and original_meso_dataset is not None:
                ds_name = original_meso_dataset.name
            else:
                ds_name = filled_meso_dataset.name
            subsections.append(FlatSubsectionConfig(
                index=f"2.4.{i}",
                type=cast(SubsectionType, subtype),
                datasets=[ds_name],
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
                type=cast(SubsectionType, subtype),
                datasets=[repyear_dataset.name],
            ))

    fifty_year_dataset = filled_meso_dataset or repyear_dataset
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
                type=cast(SubsectionType, subtype),
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


def _build_meso_filled_heights_dataset(
    project_config: ProjectConfig,
) -> DatasetConfig | None:
    """Build reconstruct_meso_filled_heights dataset from fill-heights config."""
    fill_heights_meso_dc = project_config.discover_fill_heights_meso_config()
    if fill_heights_meso_dc is None:
        return None
    return _build_dataset_for_timeseries(
        project_config.project_dir,
        fill_heights_meso_dc,
        "reconstruct-meso-fill-heights",
        "reconstruct_meso_filled_heights",
        fallback_air_density=STANDARD_AIR_DENSITY,
    )


def _build_meso_original_heights_dataset(
    project_config: ProjectConfig,
) -> DatasetConfig | None:
    """Build dataset from original reconstruct-meso output (pre-fill-heights).

    Uses mast.output.data directly from reconstruct-meso.toml.
    Discovers turbulence_heights from original sensors (real avg+sd pairs
    in 120–160m, not interpolated columns from fill-heights).
    """
    recon_meso_dc = project_config.discover_reconstruct_meso_config()
    if recon_meso_dc is None:
        return None
    project_path = project_config.project_dir
    masts = recon_meso_dc.config.masts
    mast_refs: list[MastRef] = []

    for mast in masts:
        data_path = mast.output.data
        parquet_path = project_path / data_path

        if not parquet_path.exists():
            raise FileNotFoundError(
                f"Original reconstruct-meso parquet not found for mast "
                f"{mast.name}: {parquet_path}"
            )

        source = TimeSeriesSource(data=data_path, sensors=None)
        time_series_data = load_timeseries(source, str(project_path))

        try:
            air_density = calculate_air_density(time_series_data)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Cannot calculate air density for mast {mast.name}: {e}. "
                f"Using fallback {STANDARD_AIR_DENSITY}"
            )
            air_density = STANDARD_AIR_DENSITY

        turbulence_heights = _discover_turbulence_heights(
            time_series_data.sensors
        )

        mast_refs.append(MastRef(
            name=mast.name,
            air_density=round(air_density, 3),
            input=TimeSeriesSource(data=data_path),
            turbulence_heights=turbulence_heights,
        ))

    if not mast_refs:
        return None

    return DatasetConfig(
        name="reconstruct_meso_original_heights",
        masts=mast_refs,
    )


def _build_repyear_dataset(
    project_config: ProjectConfig,
) -> DatasetConfig | None:
    """Build repyear dataset from fill-heights config enriched with representative-year.toml."""
    fill_heights_rep_year_dc = project_config.discover_fill_heights_rep_year_config()
    if fill_heights_rep_year_dc is None:
        return None
    project_path = project_config.project_dir
    repyear_dataset = _build_dataset_for_timeseries(
        project_path,
        fill_heights_rep_year_dc,
        "representative-year-fill-heights",
        "repyear",
        fallback_air_density=STANDARD_AIR_DENSITY,
    )

    if repyear_dataset is not None:
        rep_year_dc = project_config.discover_representative_year_config()
        if rep_year_dc is not None:
            masts = rep_year_dc.config.masts

            meso_name_to_masts: dict[str, list[str]] = {}
            for mast in masts:
                meso_name_to_masts.setdefault(
                    mast.meso_model.meso_name, []
                ).append(mast.name)

            meso_refs: list[MesoRef] = []
            for meso in rep_year_dc.config.mesos:
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
    filled_meso_dataset: DatasetConfig | None,
    repyear_dataset: DatasetConfig | None,
) -> DatasetConfig | None:
    """Build calibration dataset combining uncalibrated masts with calibrated mesos."""
    if filled_meso_dataset is None or repyear_dataset is None:
        return None
    return DatasetConfig(
        name="repyear_calibration",
        masts=filled_meso_dataset.masts,
        mesos=repyear_dataset.mesos,
        analysis_windows=repyear_dataset.analysis_windows,
    )


def recommend_report(project_config: ProjectConfig) -> DiscoveredConfig[FlatReportConfig]:
    """Generate configuration for representative timeseries report.

    This use case:
    1. Discovers fill-heights and representative-year configs via ProjectConfig
    2. For each mast in each config, loads the corresponding parquet file
    3. Calculates air density from mean temperature/pressure columns
    4. Returns a DiscoveredConfig containing the FlatReportConfig

    Prerequisites:
    - fill-heights-representative-year.toml must exist in project directory
    - Parquet files must exist in the referenced subdirectories
    - fill-heights-reconstruct-meso.toml is optional; if absent, only the
      代表年 subsection is generated

    Args:
        project_config: ProjectConfig for the project directory.

    Returns:
        DiscoveredConfig wrapping the FlatReportConfig.

    Raises:
        FileNotFoundError: If required fill-heights config or parquet files
            are not found
        ValueError: If no valid masts found for report configuration
    """
    filled_meso_dataset = _build_meso_filled_heights_dataset(project_config)
    repyear_dataset = _build_repyear_dataset(project_config)
    original_meso_dataset = _build_meso_original_heights_dataset(project_config)
    calibration_dataset = _build_calibration_dataset(filled_meso_dataset, repyear_dataset)

    if not filled_meso_dataset and not repyear_dataset:
        raise ValueError(
            "No valid masts found for report configuration. "
            "Ensure fill-heights configuration files exist and contain valid masts."
        )

    datasets: list[DatasetConfig] = []
    if filled_meso_dataset:
        datasets.append(filled_meso_dataset)
    if repyear_dataset:
        datasets.append(repyear_dataset)
    if original_meso_dataset:
        datasets.append(original_meso_dataset)
    if calibration_dataset:
        datasets.append(calibration_dataset)

    subsections = _build_subsections(
        filled_meso_dataset, repyear_dataset, calibration_dataset,
        original_meso_dataset=original_meso_dataset,
    )
    report_config = FlatReportConfig(
        datasets=datasets,
        subsections=subsections,
    )

    return DiscoveredConfig(config=report_config, filename="rep-ts-report.toml")
