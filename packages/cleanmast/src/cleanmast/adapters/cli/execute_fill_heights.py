"""CLI adapter for fill-heights execution command.

ADR-GUARDRAILS: cli-001-comonicon-cli, structure-001-subdomain-layout
"""


import click

from cleanmast.application.usecases.execute_fill_heights import (
    execute_fill_heights as execute_fill_heights_usecase,
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
    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    except ValueError as e:
        raise click.ClickException(str(e))

    click.echo("\nFill-heights complete!")
