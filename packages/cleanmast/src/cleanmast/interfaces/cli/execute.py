"""CLI adapters for fill-heights and wt-timeseries execution commands."""

from pathlib import Path

import click

from cleanmast.bootstrap import (
    build_execute_fill_heights,
    build_generate_wt_timeseries,
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
        build_execute_fill_heights(config_path)
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
        build_generate_wt_timeseries(config_path)
        click.echo("\n✓ Processing complete!")
        click.echo(f"Output directory: {config_path_obj.parent / 'wt-timeseries'}")
    except FileNotFoundError as e:
        raise click.ClickException(f"File not found: {e}")
    except ValueError as e:
        raise click.ClickException(f"Configuration error: {e}")
