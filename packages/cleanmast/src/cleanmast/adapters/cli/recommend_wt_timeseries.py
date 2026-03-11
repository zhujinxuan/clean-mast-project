"""CLI adapter for wt-timeseries recommendation command.

ADR-GUARDRAILS: cli-001-comonicon-cli, structure-001-subdomain-layout
"""

from pathlib import Path

import click

from cleanmast.application.usecases.recommend_wt_timeseries import (
    recommend_wt_timeseries as recommend_wt_timeseries_usecase,
)


@click.command("wt-timeseries")
@click.argument("project_dir", type=click.Path(exists=True))
def recommend_wt_timeseries_cli(project_dir: str):
    """Generate wt-timeseries.toml configuration file."""
    project_path = Path(project_dir)

    click.echo("Discovering masts from fill-heights config...")

    try:
        output_path = recommend_wt_timeseries_usecase(project_path)
    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    except ValueError as e:
        raise click.ClickException(str(e))

    click.echo(f"\nGenerated: {output_path}")
    click.echo("\nNext steps:")
    click.echo(f"  uv run cleanmast execute wt-timeseries {project_dir}")
