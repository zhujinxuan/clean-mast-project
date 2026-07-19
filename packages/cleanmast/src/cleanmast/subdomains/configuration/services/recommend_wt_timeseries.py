"""Recommend WT TimeSeries use case.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-a-001-use-case-pattern
Compliance: Subdomain layout ✓ | Use Case ✓ | CLI Adapter Ready ✓

This module provides the use case for generating wt-timeseries.toml
configuration files based on auto-discovering heights from representative-year data.
"""

from cleanmast.shared.timeseries.sensor_column import SensorColumn
from cleanmast.shared.timeseries.time_series_source import (
    TimeSeriesSource,
)
from cleanmast.subdomains.configuration import (
    DiscoveredConfig,
    ProjectConfig,
    WtTimeSeriesConfiguration,
    WtTimeSeriesMast,
)
from cleanmast.subdomains.dataingestion.infrastructure.timeseries_io import load_timeseries


def _discover_csv_heights(sensors: list[SensorColumn]) -> list[float]:
    """Find heights >=100m with both WS avg and WD avg sensors."""
    all_heights = sorted(set(s.height for s in sensors))

    csv_heights: list[float] = []

    for height in all_heights:
        has_ws = any(
            s.sensor_type == "WindSpeed"
            and s.stat_type == "avg"
            and s.height == height
            for s in sensors
        )

        has_wd = any(
            s.sensor_type == "WindDirection"
            and s.stat_type == "avg"
            and s.height == height
            for s in sensors
        )

        if height >= 100.0 and has_ws and has_wd:
            csv_heights.append(height)

    return csv_heights


def _discover_turbulence_heights(sensors: list[SensorColumn]) -> list[float]:
    """Find heights with both WS avg and WS sd sensors within turbine range (120–160m)."""
    all_heights = sorted(set(s.height for s in sensors))

    turbulence_heights: list[float] = []

    for height in all_heights:
        has_ws_avg = any(
            s.sensor_type == "WindSpeed"
            and s.stat_type == "avg"
            and s.height == height
            for s in sensors
        )

        has_ws_sd = any(
            s.sensor_type == "WindSpeed"
            and s.stat_type == "sd"
            and s.height == height
            for s in sensors
        )

        if has_ws_avg and has_ws_sd and 120.0 <= height <= 160.0:
            turbulence_heights.append(height)

    return turbulence_heights


def recommend_wt_timeseries(
    project_config: ProjectConfig,
) -> DiscoveredConfig[WtTimeSeriesConfiguration]:
    """Generate wt-timeseries.toml configuration by auto-discovering heights.

    1. Discover fill-heights-representative-year.toml via ProjectConfig
    2. For each mast in config:
       - Use mast.output.data as input (the fill-height result)
       - Load parquet and read sensor metadata
       - Find CSV heights: heights >=100m with WS avg + WD avg
       - Find turbulence heights: heights with WS avg + WS sd
       - Create WtTimeSeriesMast config

    Args:
        project_config: ProjectConfig for the project directory

    Returns:
        DiscoveredConfig wrapping the generated WtTimeSeriesConfiguration

    Raises:
        FileNotFoundError: If fill-heights config not found
        ValueError: If no valid masts found
    """
    fill_heights_dc = project_config.discover_fill_heights_rep_year_config()
    if fill_heights_dc is None:
        raise FileNotFoundError(
            f"Fill-heights config not found in {project_config.project_dir}. "
            "Please run fill-heights processing first."
        )

    project_dir = project_config.project_dir
    fill_heights_config = fill_heights_dc.config

    masts: list[WtTimeSeriesMast] = []

    for mast_config in fill_heights_config.masts:
        input_parquet = mast_config.output.data
        mast_name = mast_config.name

        source = TimeSeriesSource(data=input_parquet)
        ts_data = load_timeseries(source, str(project_dir))
        sensors = ts_data.sensors

        csv_heights = _discover_csv_heights(sensors)
        turbulence_heights = _discover_turbulence_heights(sensors)

        if csv_heights:
            mast = WtTimeSeriesMast(
                name=mast_name,
                input=TimeSeriesSource(data=input_parquet),
                csv_heights=csv_heights,
                turbulence_heights=turbulence_heights,
            )
            masts.append(mast)

    if not masts:
        raise ValueError(
            "No valid masts found. "
            "Ensure fill-heights output files have proper sensor metadata."
        )

    config = WtTimeSeriesConfiguration(masts=masts)
    return DiscoveredConfig(config=config, filename="wt-timeseries.toml")
