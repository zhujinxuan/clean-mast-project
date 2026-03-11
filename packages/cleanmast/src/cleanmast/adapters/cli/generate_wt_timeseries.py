"""CLI adapter for wt-timeseries execution command.

ADR-GUARDRAILS: cli-001-comonicon-cli, structure-001-subdomain-layout
"""

from pathlib import Path

import click

from cleanmast.application.usecases.generate_wt_timeseries import (
    generate_wt_timeseries as generate_wt_timeseries_usecase,
)


@click.command("wt-timeseries")
@click.argument("config_path", type=click.Path(exists=True))
def execute_wt_timeseries_cli(config_path):
    """Execute wt-timeseries processing from configuration file."""
    config_path_obj = Path(config_path)

    click.echo(f"Processing wt-timeseries from: {config_path}")

    try:
        generate_wt_timeseries_usecase(config_path_obj)
    except FileNotFoundError as e:
        raise click.ClickException(f"File not found: {e}")
    except ValueError as e:
        raise click.ClickException(f"Configuration error: {e}")

    click.echo("\n✓ Processing complete!")
    click.echo(f"Output directory: {config_path_obj.parent / 'wt-timeseries'}")
