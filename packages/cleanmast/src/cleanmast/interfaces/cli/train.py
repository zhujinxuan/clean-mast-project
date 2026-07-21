"""CLI adapter for the fill-heights training command.

ADR-GUARDRAILS: cli-001-comonicon-cli, structure-001-subdomain-layout
"""

from pathlib import Path

import click

from cleanmast.application.usecases.recommend_fill_heights import (
    DEFAULT_DEG_DIFF_PER_M_LIMIT,
    DEFAULT_FILL_HEIGHTS,
)
from cleanmast.application.usecases.train_fill_heights import (
    train_fill_heights as train_fill_heights_usecase,
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
def train_fill_heights(project_dir: str, heights: str, deg_diff_limit: float):
    """Train fill-height models for all masts in a project.

    Fits shear (wind speed) and deg_diff (wind direction) from
    reconstruct-meso data and persists one model TOML per mast x strategy x
    variable under fill-models/{mast}/{strategy}/{variable}-fit.toml.
    """
    project_config = ProjectConfig(Path(project_dir))

    try:
        train_fill_heights_usecase(
            project_config=project_config,
            heights=heights,
            deg_diff_limit=deg_diff_limit,
        )
    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    except ValueError as e:
        raise click.ClickException(str(e))

    click.echo("Training complete. Models saved to fill-models/")
