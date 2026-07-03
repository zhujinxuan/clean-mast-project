"""CLI adapter for report recommendation command.

ADR-GUARDRAILS: cli-001-comonicon-cli, structure-001-subdomain-layout
"""

from pathlib import Path

import click

from cleanmast.subdomains.configuration import ProjectConfig
from cleanmast.subdomains.configuration.services.recommend_report import (
    recommend_report as recommend_report_usecase,
)


@click.command("timeseries")
@click.argument("project_dir", type=click.Path(exists=True))
def recommend_timeseries_report(project_dir: str):
    """Generate configuration for representative timeseries report."""
    click.echo("Generating rep-ts-report configuration...")

    project_config = ProjectConfig(Path(project_dir))

    try:
        dc = recommend_report_usecase(project_config)
    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    except ValueError as e:
        raise click.ClickException(str(e))

    dc.write_to(project_config.project_dir)

    click.echo(f"\nGenerated: {dc.filename}")
    click.echo("\nNext steps:")
    click.echo(f"  uv run cleanmast report timeseries {dc.filename}")
