"""CLI adapter for report generation command.

ADR-GUARDRAILS: cli-001-comonicon-cli, structure-001-subdomain-layout
"""

from pathlib import Path

import click

from cleanmast.application.usecases.generate_report import (
    generate_report as generate_report_usecase,
)


@click.command("rep-ts")
@click.argument("project_dir", type=click.Path(exists=True))
@click.option(
    "--no-pdf",
    is_flag=True,
    help="Skip PDF generation (not recommended)",
)
@click.option(
    "--no-docx",
    is_flag=True,
    help="Skip DOCX generation",
)
def report_rep_ts(project_dir: str, no_pdf: bool, no_docx: bool):
    """Generate representative timeseries report from config."""
    click.echo(f"Generating report for: {project_dir}")

    try:
        results = generate_report_usecase(
            project_dir=project_dir,
            no_pdf=no_pdf,
            no_docx=no_docx,
        )
    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    except ValueError as e:
        raise click.ClickException(str(e))

    click.echo("\n✓ Report generated successfully!")
    click.echo(f"  Typst: {results.get('typ')}")

    if "pdf" in results:
        click.echo(f"  PDF:   {results['pdf']}")

    if "docx" in results:
        click.echo(f"  DOCX:  {results['docx']}")

    if "docx_warning" in results:
        click.echo(f"\n⚠ Warning: {results['docx_warning']}")
