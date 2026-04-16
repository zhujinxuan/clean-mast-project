"""CLI adapter for report recommendation command.

ADR-GUARDRAILS: cli-001-comonicon-cli, structure-001-subdomain-layout
"""


import click

from cleanmast.application.usecases.recommend_report import (
    recommend_report as recommend_report_usecase,
)


@click.command("timeseries")
@click.argument("project_dir", type=click.Path(exists=True))
def recommend_timeseries_report(project_dir: str):
    """Generate configuration for representative timeseries report."""
    click.echo("Generating rep-ts-report configuration...")

    try:
        output_path = recommend_report_usecase(project_dir)
    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    except ValueError as e:
        raise click.ClickException(str(e))

    click.echo(f"\nGenerated: {output_path}")
    click.echo("\nNext steps:")
    click.echo(f"  uv run cleanmast report timeseries {output_path}")
