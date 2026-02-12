"""Recommend fill-heights command.

This module provides the CLI command for generating fill-heights configuration
files based on reconstruct-meso data.
"""

from pathlib import Path

import click
import tomli
import tomli_w

from ..config import MastFillConfig, HeightReference, load_fill_heights_config
from ..recommend.planner import generate_dual_configs
from ...io.timeseries_io import load_timeseries, save_timeseries
from ...models.sensor import SensorColumn
from ...models.reconstruct_meso import ReconstructMesoConfiguration
from ...models.representative_year import (
    RepresentativeYearConfiguration,
    load_representative_year_config,
)

# Default deg_diff_per_m limit (22.5° over 20m = 1.125 deg/m)
DEFAULT_DEG_DIFF_PER_M_LIMIT: float = 22.5 / 20  # 1.125 deg/m

# Default target heights for fill-heights
DEFAULT_FILL_HEIGHTS: str = "125,140,160"


@click.command("fill-heights")
@click.argument("project_dir", type=click.Path(exists=True))
@click.option(
    "--heights", "-h",
    default=DEFAULT_FILL_HEIGHTS,
    show_default=True,
    help="Comma-separated target heights in meters"
)
@click.option(
    "--deg-diff-limit",
    type=float,
    default=DEFAULT_DEG_DIFF_PER_M_LIMIT,
    show_default=True,
    help="Maximum absolute value for deg_diff_per_m (deg/m)"
)
def recommend_fill_heights(project_dir: str, heights: str, deg_diff_limit: float):
    """Generate fill-heights configuration files.

    This command:
    1. Reads reconstruct-meso.toml from the project directory
    2. Loads the reconstructed timeseries data
    3. Fits shear and deg_diff parameters from top 3 layers
    4. Generates fill-heights configuration for each target height
    5. Creates dual configs (reconstruct-meso + representative-year if available)

    Prerequisites:
    - reconstruct-meso.toml must exist in project directory
    - reconstruct-meso processing must have been completed

    Args:
        project_dir: Path to project directory containing config files
        heights: Comma-separated target heights in meters
        deg_diff_limit: Maximum absolute value for deg_diff_per_m in deg/m

    Outputs:
        - fill-heights-reconstruct-meso.toml: Config for reconstruct-meso output
          Output data goes to: reconstruct-meso-fill-heights/
        - fill-heights-representative-year.toml: Config for rep-year output (if exists)
          Output data goes to: representative-year-fill-heights/

    Examples:
        # Use default deg_diff limit (1.125 deg/m)
        uv run cleanmast recommend fill-heights projects/my-project -h 120,140,160

        # Use custom deg_diff limit (0.5 deg/m)
        uv run cleanmast recommend fill-heights projects/my-project -h 120,140,160 --deg-diff-limit 0.5

    Next Steps:
        uv run cleanmast fill-heights {meso_output_path}
    """
    project_path = Path(project_dir)

    # Parse heights
    target_heights = [float(h.strip()) for h in heights.split(",")]
    click.echo(f"Target fill heights: {target_heights} m")

    # Load reconstruct-meso.toml
    reconstruct_meso_path = project_path / "reconstruct-meso.toml"
    if not reconstruct_meso_path.exists():
        raise click.ClickException(
            f"reconstruct-meso.toml not found at {reconstruct_meso_path}. "
            "Run this command after reconstruct-meso step."
        )

    with open(reconstruct_meso_path, "rb") as f:
        reconstruct_data = tomli.load(f)
    reconstruct_config = ReconstructMesoConfiguration(**reconstruct_data)
    click.echo(f"Loaded {len(reconstruct_config.masts)} mast(s) from reconstruct-meso.toml")

    # Load representative-year.toml (optional)
    rep_year_config: RepresentativeYearConfiguration | None = None
    rep_year_path = project_path / "representative-year.toml"

    if rep_year_path.exists():
        rep_year_config = load_representative_year_config(str(rep_year_path))
        click.echo(f"Loaded {len(rep_year_config.masts)} mast(s) from representative-year.toml")
    else:
        click.echo("Note: representative-year.toml not found. "
                   "Only generating reconstruct-meso fill config.")

    # Generate dual configs
    click.echo("\nFitting shear parameters from reconstruct-meso data...")
    meso_config, rep_config = generate_dual_configs(
        reconstruct_meso_config=reconstruct_config,
        representative_year_config=rep_year_config,
        target_heights=target_heights,
        base_dir=str(project_path),
        deg_diff_limit=deg_diff_limit,
    )

    # Write fill-heights-reconstruct-meso.toml
    meso_output_path = project_path / "fill-heights-reconstruct-meso.toml"
    with open(meso_output_path, "wb") as f:
        tomli_w.dump(meso_config.model_dump(), f)
    click.echo(f"\nGenerated: {meso_output_path}")

    # Report reconstruct-meso config details
    for mast in meso_config.masts:
        ws_heights = [
            ws.target_height for ws in mast.windspeed
        ]
        wd_heights = [
            wd.target_height for wd in mast.winddirection
        ]
        click.echo(f"\n  {mast.name}:")
        click.echo(f"    Wind speed fill heights: {ws_heights}")
        click.echo(f"    Wind direction fill heights: {wd_heights}")
        if mast.windspeed:
            click.echo(f"    Fitted shear: {mast.windspeed[0].shear:.4f}")
        if mast.winddirection:
            click.echo(f"    Fitted deg_diff_per_m: {mast.winddirection[0].deg_diff_per_m:.4f}")

    # Write fill-heights-representative-year.toml (if rep year exists)
    if rep_config:
        rep_output_path = project_path / "fill-heights-representative-year.toml"
        with open(rep_output_path, "wb") as f:
            tomli_w.dump(rep_config.model_dump(), f)
        click.echo(f"\nGenerated: {rep_output_path}")

        for mast in rep_config.masts:
            ws_heights = [
                ws.target_height for ws in mast.windspeed
            ]
            wd_heights = [
                wd.target_height for wd in mast.winddirection
            ]
            click.echo(f"\n  {mast.name} (rep-year):")
            click.echo(f"    Wind speed fill heights: {ws_heights}")
            click.echo(f"    Wind direction fill heights: {wd_heights}")

    click.echo("\nNext steps:")
    click.echo(f"  uv run cleanmast fill-heights {meso_output_path}")
    if rep_config:
        click.echo(f"  uv run cleanmast fill-heights {rep_output_path}")
