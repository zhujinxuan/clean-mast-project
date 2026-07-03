"""CLI adapter for wt-timeseries recommendation command.

ADR-GUARDRAILS: cli-001-comonicon-cli, structure-001-subdomain-layout
"""

from pathlib import Path

import click

from cleanmast.subdomains.configuration import ProjectConfig
from cleanmast.subdomains.configuration.services.recommend_wt_timeseries import (
    recommend_wt_timeseries as recommend_wt_timeseries_usecase,
)


@click.command("wt-timeseries")
@click.argument("project_dir", type=click.Path(exists=True))
def recommend_wt_timeseries_cli(project_dir: str):
    """Generate wt-timeseries.toml configuration file."""
    project_config = ProjectConfig(Path(project_dir))

    click.echo("Discovering masts from fill-heights config...")

    try:
        dc = recommend_wt_timeseries_usecase(project_config)
    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    except ValueError as e:
        raise click.ClickException(str(e))

    dc.write_to(project_config.project_dir)

    click.echo(f"\nGenerated: {dc.filename}")
    click.echo("\nNext steps:")
    click.echo(f"  uv run cleanmast wt-timeseries {dc.filename}")
