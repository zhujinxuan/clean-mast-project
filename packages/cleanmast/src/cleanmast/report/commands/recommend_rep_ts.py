"""Recommend rep-ts-report command.

This module provides the CLI command for generating rep-ts-report configuration
files based on fill-heights-representative-year data.
"""

from pathlib import Path

import click
import polars as pl
import tomli
import tomli_w

from ..meta import calculate_air_density


@click.command("rep-ts-report")
@click.argument("project_dir", type=click.Path(exists=True))
def recommend_rep_ts_report(project_dir: str):
    """Generate configuration for representative timeseries report.

    This command:
    1. Reads fill-heights-representative-year.toml from the project directory
    2. For each mast, loads the parquet file from representative-year-fill-heights/
    3. Calculates air density from mean temperature/pressure columns
    4. Generates rep-ts-report.toml config file

    Prerequisites:
    - fill-heights-representative-year.toml must exist in project directory
    - Parquet files must exist in representative-year-fill-heights/ subdirectory

    Args:
        project_dir: Path to project directory containing config files

    Outputs:
        - rep-ts-report.toml: Configuration file for representative timeseries report

    Example:
        uv run cleanmast recommend rep-ts-report projects/my-project

    Next Steps:
        uv run cleanmast report rep-ts {project_dir}
    """
    project_path = Path(project_dir)

    # Load fill-heights-representative-year.toml
    fill_heights_path = project_path / "fill-heights-representative-year.toml"
    if not fill_heights_path.exists():
        raise click.ClickException(
            f"fill-heights-representative-year.toml not found at {fill_heights_path}. "
            "Run 'recommend fill-heights' command first."
        )

    with open(fill_heights_path, "rb") as f:
        fill_heights_config = tomli.load(f)

    # Extract mast configurations
    masts_config = fill_heights_config.get("masts", [])
    if not masts_config:
        raise click.ClickException(
            "No masts found in fill-heights-representative-year.toml"
        )

    click.echo(f"Found {len(masts_config)} mast(s) in fill-heights config")

    # Process each mast
    report_masts = []
    for mast in masts_config:
        mast_name = mast.get("name")
        if not mast_name:
            click.echo("Warning: Skipping mast without name")
            continue

        # Get output path from fill-heights config (this is the filled data)
        output_config = mast.get("output", {})
        data_path = output_config.get("data", "")

        if not data_path:
            click.echo(f"Warning: No output data path for mast {mast_name}, skipping")
            continue

        # Resolve parquet path (relative to project directory)
        parquet_path = project_path / data_path
        if not parquet_path.exists():
            raise click.ClickException(
                f"Parquet file not found for mast {mast_name}: {parquet_path}"
            )

        click.echo(f"Processing {mast_name}...")

        # Load parquet and calculate air density
        try:
            df = pl.read_parquet(parquet_path)
            air_density = calculate_air_density(df)
            click.echo(f"  Calculated air density: {air_density:.3f} kg/m³")
        except Exception as e:
            click.echo(f"  Warning: Failed to calculate air density: {e}")
            air_density = 1.225  # Fallback to standard value
            click.echo(f"  Using fallback air density: {air_density:.3f} kg/m³")

        # Build mast entry for report config
        # Convert to relative path for the config
        rel_data_path = f"./representative-year-fill-heights/{mast_name}.parquet"
        report_masts.append({
            "name": mast_name,
            "air_density": round(air_density, 3),
            "input": {
                "data": rel_data_path,
                # No sensors field - metadata is embedded in parquet
            },
        })

    # Generate report config
    report_config = {"masts": report_masts}

    # Write rep-ts-report.toml
    output_path = project_path / "rep-ts-report.toml"
    with open(output_path, "wb") as f:
        tomli_w.dump(report_config, f)

    click.echo(f"\nGenerated: {output_path}")
    click.echo(f"  Masts configured: {len(report_masts)}")
    for mast_entry in report_masts:
        click.echo(f"    - {mast_entry['name']}: air_density={mast_entry['air_density']}")

    click.echo("\nNext steps:")
    click.echo(f"  uv run cleanmast report rep-ts {project_dir}")
