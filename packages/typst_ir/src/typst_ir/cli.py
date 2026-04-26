"""Typst IR CLI entry point."""

from __future__ import annotations

from pathlib import Path

import typer

from typst_ir.enriched.serialize_docx import draft_docx as draft_docx_impl
from typst_ir.polish_docx import polish_docx
from typst_ir.renderer import render_to_pdf

app = typer.Typer()


@app.command()
def draft_docx(input_json: Path, output: Path | None = None) -> None:
    """Create draft DOCX with round-trip markers."""
    if not input_json.exists():
        typer.echo(f"Error: {input_json} not found", err=True)
        raise typer.Exit(1)
    try:
        result_path = draft_docx_impl(input_json, output)
        typer.echo(f"Created: {result_path}")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def render_pdf(input_json: Path, output_dir: Path) -> None:
    """Render JSON IR to PDF."""
    if not input_json.exists():
        typer.echo(f"Error: {input_json} not found", err=True)
        raise typer.Exit(1)
    try:
        json_str = input_json.read_text(encoding="utf-8")
        result_path = render_to_pdf(json_str, output_dir)
        typer.echo(f"Created: {result_path}")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("polish-docx")
def cli_polish_docx(
    docx_path: Path = typer.Argument(..., help="Input DOCX file with IR markers"),
    ir_json_path: Path = typer.Argument(..., help="Typst IR JSON file"),
    output_path: Path = typer.Argument(..., help="Output polished DOCX file"),
) -> None:
    """Polish a DOCX using Typst IR instructions."""
    if not docx_path.exists():
        typer.echo(f"Error: {docx_path} not found", err=True)
        raise typer.Exit(1)
    if not ir_json_path.exists():
        typer.echo(f"Error: {ir_json_path} not found", err=True)
        raise typer.Exit(1)
    try:
        polish_docx(docx_path, ir_json_path, output_path)
        typer.echo(f"Polished DOCX saved to {output_path}")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
