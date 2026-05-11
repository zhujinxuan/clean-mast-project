"""Recommend report configuration use case.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-a-001-use-case-pattern
Compliance: Subdomain layout ✓ | Use Case ✓ | CLI Adapter Ready ✓
Description: Application use case for generating report configuration files

This module provides the use case for generating report configuration
files based on fill-heights data from both reconstruct-meso and
representative-year sources.
"""

from pathlib import Path

from cleanmast.subdomains.assessment.domain.value_objects.air_density import (
    calculate_air_density,
)
from cleanmast.subdomains.assessment.domain.value_objects.dataset_config import (
    DatasetConfig,
    MastRef,
    MesoRef,
)
from cleanmast.subdomains.assessment.domain.value_objects.flat_report_config import (
    FlatReportConfig,
)
from cleanmast.subdomains.assessment.domain.value_objects.flat_subsection_config import (
    FlatSubsectionConfig,
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
    import tomli

    fill_heights_path = project_path / fill_heights_filename
    if not fill_heights_path.exists():
        return None

    with open(fill_heights_path, "rb") as f:
        config = tomli.load(f)

    masts = config.get("masts", [])
    mast_refs: list[MastRef] = []

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
) -> list[FlatSubsectionConfig]:
    """Build flat subsections with hardcoded indices.

    Index scheme:
      2.4 = meso (timeseries)
      2.5 = repyear (timeseries)
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
        for i, subtype in enumerate(_REP_ANALYSIS_SUBSECTION_TYPES, start=1):
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

    reconstruct_meso_dataset = _build_dataset_for_timeseries(
        project_path,
        "fill-heights-reconstruct-meso.toml",
        "reconstruct-meso-fill-heights",
        "reconstruct_meso",
    )
    repyear_dataset = _build_dataset_for_timeseries(
        project_path,
        "fill-heights-representative-year.toml",
        "representative-year-fill-heights",
        "repyear",
    )

    if repyear_dataset:
        import tomli

        repyear_toml_path = project_path / "representative-year.toml"
        if repyear_toml_path.exists():
            with open(repyear_toml_path, "rb") as f:
                repyear_config = tomli.load(f)

            mesos_config = repyear_config.get("mesos", [])
            masts_config = repyear_config.get("masts", [])

            if mesos_config:
                meso_name_to_masts: dict[str, list[str]] = {}
                for mast in masts_config:
                    mast_name = mast.get("name")
                    meso_name = mast.get("meso_model", {}).get("meso_name")
                    if mast_name and meso_name:
                        meso_name_to_masts.setdefault(meso_name, []).append(mast_name)

                meso_refs: list[MesoRef] = []
                for meso in mesos_config:
                    meso_name = meso.get("name")
                    input_data = meso.get("input", {})
                    meso_data = input_data.get("data")
                    if meso_name and meso_data:
                        target_masts = meso_name_to_masts.get(meso_name, [])
                        if target_masts:
                            source = TimeSeriesSource(
                                data=meso_data,
                                sensors=input_data.get("sensors"),
                            )
                            meso_refs.append(MesoRef(
                                input=source,
                                target_masts=target_masts,
                            ))

                if meso_refs:
                    repyear_dataset.mesos = meso_refs

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

    subsections = _build_subsections(reconstruct_meso_dataset, repyear_dataset)

    report_config = FlatReportConfig(
        datasets=datasets,
        subsections=subsections,
    )

    output_path = project_path / "rep-ts-report.toml"
    report_config.to_toml(output_path)

    return output_path
