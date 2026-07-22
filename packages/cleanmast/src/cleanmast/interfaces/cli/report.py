"""CLI adapter for report generation command."""


import click

from cleanmast.bootstrap import build_generate_report


@click.command("timeseries")
@click.argument("config_path", type=click.Path(exists=True))
def report_timeseries(config_path: str):
    """Generate representative timeseries report from config."""
    click.echo(f"Generating report for: {config_path}")

    try:
        results = build_generate_report(config_path)
    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    except ValueError as e:
        raise click.ClickException(str(e))

    click.echo("\n✓ Report generated successfully!")
    click.echo(f"  Typst: {results.get('typ')}")
    click.echo(f"  PDF:   {results.get('pdf')}")
    click.echo(f"  DOCX:  {results.get('docx')}")
