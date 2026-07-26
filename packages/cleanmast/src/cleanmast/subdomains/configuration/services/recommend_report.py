"""Recommend report configuration use case.

Description: Application use case for generating report configuration files

This module provides the use case for generating report configuration
files based on fill-heights data from both reconstruct-meso and
representative-year sources.
"""

import logging
from collections.abc import Collection, Sequence
from pathlib import Path
from typing import Any, cast

from cleanmast.shared.timeseries.io import TimeSeriesRepository
from cleanmast.shared.timeseries.sensor_column import (
    SensorColumn,
)
from cleanmast.shared.timeseries.time_range import TimeRange
from cleanmast.shared.timeseries.time_series_source import (
    TimeSeriesSource,
)
from cleanmast.subdomains.configuration import (
    AnalysisWindow,
    DatasetConfig,
    DiscoveredConfig,
    ExtremeWindGustFactor,
    FlatReportConfig,
    FlatSubsectionConfig,
    MastRef,
    MesoRef,
    ProjectConfig,
    RepresentativeYearMast,
    SubsectionType,
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


def _discover_analysis_heights(sensors: list[SensorColumn]) -> list[float]:
    """WindSpeed avg sensor heights within the turbine range (120–160m)."""
    return sorted(
        s.height
        for s in sensors
        if s.sensor_type == "WindSpeed"
        and s.stat_type == "avg"
        and 120.0 <= s.height <= 160.0
    )


def _discover_temporal_heights(sensors: list[SensorColumn]) -> list[float]:
    """All WindSpeed avg sensor heights (no height-band filter)."""
    return sorted(
        s.height
        for s in sensors
        if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
    )


def _discover_extreme_wind_heights(
    sensors: list[SensorColumn],
) -> tuple[list[float], list[float], list[ExtremeWindGustFactor]]:
    """Discover extreme-wind heights and gust factors from mast sensor columns.

    Args:
        sensors: Sensor metadata columns for a single mast.

    Returns:
        Tuple of (10min_heights, 3s_heights, gust_factors).
        - 10min_heights: sorted heights 120–160m with WindSpeed avg sensors.
          Interpolated (内插) fill heights are excluded when a real (非内插)
          height with BOTH avg AND max sensors exists within ≤10m.
        - 3s_heights: sorted heights 120–160m with WindSpeed max sensors.
        - gust_factors: one ExtremeWindGustFactor per 10min height (default 1.4).
    """
    # Collect WindSpeed sensors in 120–160m
    ws_sensors = [
        s for s in sensors
        if s.sensor_type == "WindSpeed" and 120.0 <= s.height <= 160.0
    ]

    # Candidate 10min heights: all WindSpeed/avg
    ten_min_candidates: list[SensorColumn] = [
        s for s in ws_sensors if s.stat_type == "avg"
    ]

    # 3s heights: all WindSpeed/max (no exclusion)
    three_sec = sorted(
        s.height for s in ws_sensors if s.stat_type == "max"
    )

    # Real both-sensor heights: non-interpolated heights with BOTH avg AND max
    real_avg_heights = {
        s.height for s in ten_min_candidates
        if s.detect_interpolation_marker() != "内插"
    }
    real_max_heights = {
        s.height for s in ws_sensors
        if s.stat_type == "max" and s.detect_interpolation_marker() != "内插"
    }
    real_both_sensor_heights = sorted(real_avg_heights & real_max_heights)

    # Filter: exclude fill heights bracketed by a real both-sensor neighbor
    # within ≤10m (inclusive)
    def _is_fill_excluded(fill_height: float) -> bool:
        return any(
            abs(fill_height - real_h) <= 10.0
            for real_h in real_both_sensor_heights
        )

    ten_min = sorted(
        s.height for s in ten_min_candidates
        if s.detect_interpolation_marker() != "内插"
        or not _is_fill_excluded(s.height)
    )

    gust_factors = [ExtremeWindGustFactor(height=h) for h in ten_min]
    return ten_min, three_sec, gust_factors


def _build_dataset_for_timeseries(
    project_path: Path,
    discovered_config: DiscoveredConfig[Any],
    report_data_subdir: str,
    dataset_name: str,
    analysis_windows: list[AnalysisWindow],
    repo: TimeSeriesRepository,
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

        source = TimeSeriesSource(data=data_path, sensors=None)
        time_series_data = repo.load(source, str(project_path))
        try:
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
        analysis_heights = _discover_analysis_heights(
            time_series_data.sensors
        )
        temporal_heights = _discover_temporal_heights(
            time_series_data.sensors
        )
        ew_10min, ew_3s, ew_gust = _discover_extreme_wind_heights(
            time_series_data.sensors
        )

        mast_refs.append(MastRef(
            name=mast_name,
            air_density=round(air_density, 3),
            input=TimeSeriesSource(data=rel_data_path),
            turbulence_heights=turbulence_heights,
            analysis_heights=analysis_heights,
            temporal_heights=temporal_heights,
            extreme_wind_10min_heights=ew_10min,
            extreme_wind_3s_heights=ew_3s,
            extreme_wind_gust_factors=ew_gust,
        ))

    if not mast_refs:
        return None
    return DatasetConfig(
        name=dataset_name,
        masts=mast_refs,
        analysis_windows=analysis_windows,
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
        2.5.1 = calibration (uses receive_repyear_calibration_input dataset)
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


def _windows_for_mast_names(
    rep_year_masts: Sequence[RepresentativeYearMast],
    mast_names: Collection[str],
) -> list[AnalysisWindow]:
    """Filter rep_year_masts to those named in mast_names, then build analysis windows."""
    filtered = [m for m in rep_year_masts if m.name in mast_names]
    return _build_analysis_windows(filtered)


def _build_meso_filled_heights_dataset(
    project_config: ProjectConfig,
    rep_year_masts: Sequence[RepresentativeYearMast],
    repo: TimeSeriesRepository,
) -> DatasetConfig | None:
    """Build reconstruct_meso_filled_heights dataset from fill-heights config."""
    fill_heights_meso_dc = project_config.discover_fill_heights_meso_config()
    if fill_heights_meso_dc is None:
        return None
    mast_names = [m.name for m in fill_heights_meso_dc.config.masts]
    return _build_dataset_for_timeseries(
        project_config.project_dir,
        fill_heights_meso_dc,
        "reconstruct-meso-fill-heights",
        "reconstruct_meso_filled_heights",
        fallback_air_density=STANDARD_AIR_DENSITY,
        analysis_windows=_windows_for_mast_names(rep_year_masts, mast_names),
        repo=repo,
    )


def _build_meso_original_heights_dataset(
    project_config: ProjectConfig,
    rep_year_masts: Sequence[RepresentativeYearMast],
    repo: TimeSeriesRepository,
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
        time_series_data = repo.load(source, str(project_path))

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
        analysis_heights = _discover_analysis_heights(
            time_series_data.sensors
        )
        temporal_heights = _discover_temporal_heights(
            time_series_data.sensors
        )
        ew_10min, ew_3s, ew_gust = _discover_extreme_wind_heights(
            time_series_data.sensors
        )

        mast_refs.append(MastRef(
            name=mast.name,
            air_density=round(air_density, 3),
            input=TimeSeriesSource(data=data_path),
            turbulence_heights=turbulence_heights,
            analysis_heights=analysis_heights,
            temporal_heights=temporal_heights,
            extreme_wind_10min_heights=ew_10min,
            extreme_wind_3s_heights=ew_3s,
            extreme_wind_gust_factors=ew_gust,
        ))

    if not mast_refs:
        return None

    mast_names = [m.name for m in mast_refs]
    return DatasetConfig(
        name="reconstruct_meso_original_heights",
        masts=mast_refs,
        analysis_windows=_windows_for_mast_names(rep_year_masts, mast_names),
    )


def _build_repyear_dataset(
    project_config: ProjectConfig,
    rep_year_masts: Sequence[RepresentativeYearMast],
    repo: TimeSeriesRepository,
) -> DatasetConfig | None:
    """Build repyear dataset from fill-heights config enriched with representative-year.toml."""
    fill_heights_rep_year_dc = project_config.discover_fill_heights_rep_year_config()
    if fill_heights_rep_year_dc is None:
        raise FileNotFoundError(
            "fill-heights-representative-year.toml is required for report generation"
        )
    project_path = project_config.project_dir
    mast_names = [m.name for m in fill_heights_rep_year_dc.config.masts]
    repyear_dataset = _build_dataset_for_timeseries(
        project_path,
        fill_heights_rep_year_dc,
        "representative-year-fill-heights",
        "repyear",
        fallback_air_density=STANDARD_AIR_DENSITY,
        analysis_windows=_windows_for_mast_names(rep_year_masts, mast_names),
        repo=repo,
    )

    if repyear_dataset is not None:
        rep_year_dc = project_config.discover_representative_year_config()
        # representative-year.toml is guaranteed to exist (recommend_report checks first)
        assert rep_year_dc is not None
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

    return repyear_dataset


def _build_calibration_dataset(
    filled_meso_dataset: DatasetConfig | None,
    repyear_dataset: DatasetConfig | None,
    rep_year_masts: Sequence[RepresentativeYearMast],
) -> DatasetConfig | None:
    """Build calibration dataset combining uncalibrated masts with calibrated mesos."""
    if filled_meso_dataset is None or repyear_dataset is None:
        return None
    filled_names = [m.name for m in filled_meso_dataset.masts] if filled_meso_dataset.masts else []
    return DatasetConfig(
        name="receive_repyear_calibration_input",
        masts=filled_meso_dataset.masts,
        mesos=repyear_dataset.mesos,
        analysis_windows=_windows_for_mast_names(rep_year_masts, filled_names),
    )


def recommend_report(
    project_config: ProjectConfig,
    repo: TimeSeriesRepository,
) -> DiscoveredConfig[FlatReportConfig]:
    """Generate configuration for representative timeseries report.

    This use case:
    1. Discovers fill-heights and representative-year configs via ProjectConfig
    2. For each mast in each config, loads the corresponding parquet file
    3. Calculates air density from mean temperature/pressure columns
    4. Returns a DiscoveredConfig containing the FlatReportConfig

    Prerequisites:
    - representative-year.toml must exist in project directory
    - fill-heights-representative-year.toml must exist in project directory
    - Parquet files must exist in the referenced subdirectories
    - fill-heights-reconstruct-meso.toml is optional; if absent, only the
      代表年 subsection is generated

    Args:
        project_config: ProjectConfig for the project directory.
        repo: TimeSeriesRepository used to load mast timeseries.

    Returns:
        DiscoveredConfig wrapping the FlatReportConfig.

    Raises:
        FileNotFoundError: If required representative-year.toml,
            fill-heights-representative-year.toml, or parquet files
            are not found
        ValueError: If no valid masts found for report configuration
    """
    rep_year_dc = project_config.discover_representative_year_config()
    if rep_year_dc is None:
        raise FileNotFoundError(
            "representative-year.toml is required for report generation. "
            "Meso-only reports are not supported."
        )
    rep_year_masts = rep_year_dc.config.masts

    filled_meso_dataset = _build_meso_filled_heights_dataset(project_config, rep_year_masts, repo)
    repyear_dataset = _build_repyear_dataset(project_config, rep_year_masts, repo)
    original_meso_dataset = _build_meso_original_heights_dataset(project_config, rep_year_masts, repo)
    calibration_dataset = _build_calibration_dataset(filled_meso_dataset, repyear_dataset, rep_year_masts)

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
