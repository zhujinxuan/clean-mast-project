"""CLI commands for mapping operations.

Provides command-line interface for building and exporting DOCX-to-Typst IR mappings.
"""

from __future__ import annotations

import logging
from pathlib import Path

import click

from typst_ir.mapping.builder import MappingBuilder
from typst_ir.mapping.injector import inject_ids
from typst_ir.mapping.registry import NodeRegistry
from typst_ir.nodes import TypstDocument
from typst_ir.polish.cli import apply_polish_ir, generate_polish_ir


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """
    Typst IR - Intermediate Representation for document processing.

    Commands for working with Typst IR and DOCX mappings:
    - export-mapping: Build and export DOCX-to-IR mapping to JSON
    """
    pass


main.add_command(generate_polish_ir)
main.add_command(apply_polish_ir)


@main.command(name="export-mapping")
@click.option(
    "--ir-json",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to IR JSON file",
)
@click.option(
    "--docx",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to DOCX file",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path for output mapping JSON",
)
@click.option(
    "--inject/--no-inject",
    default=True,
    help="Inject w:customIRID attributes into the DOCX file",
)
@click.option(
    "--output-docx",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path for output DOCX file (default: modify in-place)",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="WARNING",
    help="Logging level for mapping output",
)
def export_mapping(
    ir_json: Path,
    docx: Path,
    output: Path,
    inject: bool,
    output_docx: Path | None,
    log_level: str,
) -> None:
    """Build and export DOCX-to-Typst IR mapping to JSON.

    Loads a TypstDocument from JSON, builds a mapping to the source DOCX file,
    and exports the mapping as a JSON file.

    Args:
        ir_json: Path to the IR JSON file containing TypstDocument
        docx: Path to the source DOCX file
        output: Path where the mapping JSON will be written
        inject: Whether to inject w:customIRID attributes into the DOCX file
        output_docx: Path where the output DOCX file will be written
        log_level: Logging level for mapping output
    """
    level = getattr(logging, log_level.upper())
    logging.basicConfig(level=level)
    logging.getLogger("typst_ir.mapping").setLevel(level)

    # Step 1: Load TypstDocument from JSON
    click.echo(f"Loading IR from {ir_json}...")
    json_content = ir_json.read_text(encoding="utf-8")
    document = TypstDocument.model_validate_json(json_content)

    # Step 2: Create NodeRegistry and initialize
    click.echo("Initializing node registry...")
    registry = NodeRegistry()

    # Step 3: Create MappingBuilder
    builder = MappingBuilder(registry)

    # Step 4: Build mapping
    click.echo(f"Building mapping to {docx}...")
    mapping = builder.build(document, str(docx))

    # Step 5: Export mapping to JSON
    click.echo(f"Exporting mapping to {output}...")
    output.parent.mkdir(parents=True, exist_ok=True)
    mapping_json = mapping.model_dump_json(indent=2)
    output.write_text(mapping_json, encoding="utf-8")

    if inject:
        target_docx = output_docx if output_docx is not None else docx
        click.echo(f"Injecting IDs into DOCX ({target_docx})...")
        inject_ids(docx, target_docx, mapping)
        click.echo("✓ DOCX updated with custom IR IDs")

    click.echo(f"✓ Mapping exported successfully: {len(mapping.entries)} entries")


if __name__ == "__main__":
    main()
