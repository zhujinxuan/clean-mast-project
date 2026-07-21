"""CLI adapters for fill-heights and wt-timeseries execution commands.

ADR-GUARDRAILS: cli-001-comonicon-cli, structure-001-subdomain-layout
"""

from pathlib import Path

import click

from cleanmast.application.usecases.execute_fill_heights import (
    execute_fill_heights as execute_fill_heights_usecase,
)
from cleanmast.application.usecases.generate_wt_timeseries import (
    generate_wt_timeseries as generate_wt_timeseries_usecase,
)


@click.command()
@click.argument("config_path", type=click.Path(exists=True))
def execute_fill_heights(config_path: str):
    """Execute fill-heights from configuration file.

    This command:
    1. Loads the fill-heights configuration
    2. Loads input timeseries data for each mast
    3. Applies wind speed and direction filling
    4. Saves output with new columns
    """
    click.echo(f"Loading config: {config_path}")

    try:
        execute_fill_heights_usecase(config_path)
        click.echo("\nFill-heights complete!")
    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    except ValueError as e:
        raise click.ClickException(str(e))


@click.command("wt-timeseries")
@click.argument("config_path", type=click.Path(exists=True))
def execute_wt_timeseries_cli(config_path):
    """Execute wt-timeseries processing from configuration file."""
    config_path_obj = Path(config_path)

    click.echo(f"Processing wt-timeseries from: {config_path}")

    try:
        generate_wt_timeseries_usecase(config_path_obj)
        click.echo("\n✓ Processing complete!")
        click.echo(f"Output directory: {config_path_obj.parent / 'wt-timeseries'}")
    except FileNotFoundError as e:
        raise click.ClickException(f"File not found: {e}")
    except ValueError as e:
        raise click.ClickException(f"Configuration error: {e}")
