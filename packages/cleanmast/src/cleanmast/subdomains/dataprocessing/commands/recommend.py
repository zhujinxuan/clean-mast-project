"""Recommend command for wt_timeseries.

This module provides the CLI command for generating wt-timeseries.toml
configuration files based on auto-discovering heights from representative-year data.

ADR-GUARDRAILS: structure-001-subdomain-layout, cli-001-click-cli-patterns
Compliance: Subdomain layout ✓ | CLI Pattern ✓ | Command Implementation ✓
"""

import logging
from pathlib import Path

import click
import tomli
import tomli_w

from cleanmast.subdomains.configuration import (
    ProjectConfig,
    WtTimeSeriesConfiguration,
    WtTimeSeriesMast,
)
from cleanmast.subdomains.dataingestion.infrastructure.timeseries_io import load_timeseries
from cleanmast.subdomains.dataingestion.value_objects import SensorColumn
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)

logger = logging.getLogger(__name__)


def _discover_csv_heights(sensors: list[SensorColumn]) -> list[float]:
    """Find heights >=100m with both WS avg and WD avg sensors.

    Args:
        sensors: List of available sensors from parquet metadata

    Returns:
        List of heights (meters) that have both WindSpeed avg and WindDirection avg
    """
    # Get unique heights from all sensors
    all_heights = sorted(set(s.height for s in sensors))

    csv_heights: list[float] = []

    for height in all_heights:
        # Check if we have WindSpeed avg at this height
        has_ws = any(
            s.sensor_type == "WindSpeed"
            and s.stat_type == "avg"
            and s.height == height
            for s in sensors
        )

        # Check if we have WindDirection avg at this height
        has_wd = any(
            s.sensor_type == "WindDirection"
            and s.stat_type == "avg"
            and s.height == height
            for s in sensors
        )

        # Height must be >= 100m and have both WS and WD
        if height >= 100.0 and has_ws and has_wd:
            csv_heights.append(height)

    return csv_heights


def _discover_turbulence_heights(sensors: list[SensorColumn]) -> list[float]:
    """Find heights with both WS avg and WS sd sensors within turbine range (120–160m).

    Args:
        sensors: List of available sensors from parquet metadata

    Returns:
        List of heights (meters) that have both WindSpeed avg and WindSpeed sd
        and fall within the turbine-relevant 120–160m range.
    """
    # Get unique heights from all sensors
    all_heights = sorted(set(s.height for s in sensors))

    turbulence_heights: list[float] = []

    for height in all_heights:
        # Check if we have WindSpeed avg at this height
        has_ws_avg = any(
            s.sensor_type == "WindSpeed"
            and s.stat_type == "avg"
            and s.height == height
            for s in sensors
        )

        # Check if we have WindSpeed sd at this height
        has_ws_sd = any(
            s.sensor_type == "WindSpeed"
            and s.stat_type == "sd"
            and s.height == height
            for s in sensors
        )

        # Need both WS avg and WS sd at same height, within turbine range
        if has_ws_avg and has_ws_sd and 120.0 <= height <= 160.0:
            turbulence_heights.append(height)

    return turbulence_heights


def recommend_wt_timeseries(project_dir: Path) -> Path:
    """Generate wt-timeseries.toml configuration by auto-discovering heights.

    1. Load fill-heights-representative-year.toml config
    2. For each mast in config:
       - Use mast.output.data as input (the fill-height result)
       - Load parquet and read sensor metadata
       - Find CSV heights: heights >=100m with WS avg + WD avg
       - Find turbulence heights: heights with WS avg + WS sd
       - Create WtTimeSeriesMast config
    3. Save to wt-timeseries.toml in project directory

    Args:
        project_dir: Project directory path

    Returns:
        Path to generated config file

    Raises:
        FileNotFoundError: If fill-heights config file not found
    """
    # Load fill-heights config via ProjectConfig discovery
    pc = ProjectConfig(project_dir)
    fill_dc = pc.discover_fill_heights_rep_year_config()
    if fill_dc is None:
        raise FileNotFoundError(
            "fill-heights-representative-year.toml not found in project directory. "
            "Please run fill-heights processing first."
        )
    fill_heights_config = fill_dc.config

    masts: list[WtTimeSeriesMast] = []

    for mast_config in fill_heights_config.masts:
        # Use output.data as input path (the fill-height result)
        input_parquet = mast_config.output.data
        mast_name = mast_config.name

        # Load parquet to get sensor metadata
        source = TimeSeriesSource(data=input_parquet)
        ts_data = load_timeseries(source, str(project_dir))
        sensors = ts_data.sensors

        # Discover CSV heights (>=100m with WS avg + WD avg)
        csv_heights = _discover_csv_heights(sensors)

        # Discover turbulence heights (WS avg + WS sd)
        turbulence_heights = _discover_turbulence_heights(sensors)

        # Only add mast if we have valid heights
        if csv_heights:
            # Use the input_parquet path as-is (already relative or absolute)
            mast = WtTimeSeriesMast(
                name=mast_name,
                input=TimeSeriesSource(data=input_parquet),
                csv_heights=csv_heights,
                turbulence_heights=turbulence_heights,
            )
            masts.append(mast)

            logger.info(
                f"Mast '{mast_name}': "
                f"CSV heights: {csv_heights}, "
                f"Turbulence heights: {turbulence_heights}"
            )

    if not masts:
        raise ValueError(
            "No valid masts found. "
            "Ensure fill-heights output files have proper sensor metadata."
        )

    # Create configuration
    config = WtTimeSeriesConfiguration(masts=masts)

    # Save to wt-timeseries.toml
    output_path = project_dir / "wt-timeseries.toml"

    with open(output_path, "wb") as f:
        tomli_w.dump(config.model_dump(exclude_none=True), f)

    logger.info(f"Generated configuration: {output_path}")

    return output_path


@click.command("wt-timeseries")
@click.argument("project_dir", type=click.Path(exists=True))
def recommend_wt_timeseries_cli(project_dir: str):
    """Generate wt-timeseries.toml configuration file.

    This command:
    1. Reads fill-heights-representative-year.toml config
    2. Uses mast.output.data as input (fill-height results)
    3. Loads sensor metadata from each parquet file
    4. Auto-discovers valid CSV heights (>=100m with WS avg + WD avg)
    5. Auto-discovers valid turbulence heights (WS avg + WS sd)
    6. Generates wt-timeseries.toml with discovered heights

    Prerequisites:
    - fill-heights processing must have been completed

    Outputs:
    - wt-timeseries.toml: Configuration for wt-timeseries processing

    Examples:
        uv run cleanmast recommend wt-timeseries projects/my-project

    Next Steps:
        uv run cleanmast execute wt-timeseries projects/my-project
    """
    project_path = Path(project_dir)

    click.echo("Discovering masts from fill-heights config...")

    try:
        output_path = recommend_wt_timeseries(project_path)
        click.echo(f"\nGenerated: {output_path}")

        # Load config to display details
        with open(output_path, "rb") as f:
            data = tomli.load(f)

        for mast_data in data.get("masts", []):
            click.echo(f"\n  {mast_data['name']}:")
            click.echo(f"    Input: {mast_data['input']['data']}")
            click.echo(f"    CSV heights: {mast_data['csv_heights']}")
            click.echo(f"    Turbulence heights: {mast_data['turbulence_heights']}")

        click.echo("\nNext steps:")
        click.echo(f"  uv run cleanmast execute wt-timeseries {project_dir}")

    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    except ValueError as e:
        raise click.ClickException(str(e))
