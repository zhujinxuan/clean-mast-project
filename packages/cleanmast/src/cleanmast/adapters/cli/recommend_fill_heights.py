"""CLI adapter for fill-heights recommendation command.

ADR-GUARDRAILS: cli-001-comonicon-cli, structure-001-subdomain-layout
"""

from pathlib import Path

import click

from cleanmast.application.usecases.recommend_fill_heights import (
    DEFAULT_DEG_DIFF_PER_M_LIMIT,
    DEFAULT_FILL_HEIGHTS,
)
from cleanmast.application.usecases.recommend_fill_heights import (
    recommend_fill_heights as recommend_fill_heights_usecase,
)
from cleanmast.subdomains.configuration import ProjectConfig


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
    """
    click.echo(f"Target fill heights: {heights.split(',')} m")

    project_config = ProjectConfig(Path(project_dir))

    try:
        meso_dc, rep_dc = recommend_fill_heights_usecase(
            project_config=project_config,
            heights=heights,
            deg_diff_limit=deg_diff_limit,
        )
    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    except ValueError as e:
        raise click.ClickException(str(e))

    meso_dc.write_to(project_config.project_dir)
    click.echo(f"\nGenerated: {meso_dc.filename}")

    if rep_dc:
        rep_dc.write_to(project_config.project_dir)
        click.echo(f"Generated: {rep_dc.filename}")

    click.echo("\nNext steps:")
    click.echo(f"  uv run cleanmast fill-heights {meso_dc.filename}")
    if rep_dc:
        click.echo(f"  uv run cleanmast fill-heights {rep_dc.filename}")
