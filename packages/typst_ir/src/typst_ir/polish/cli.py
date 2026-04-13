"""CLI commands for polish operations.

Provides command-line interface for generating and applying Polish IR
to DOCX documents.
"""

from __future__ import annotations

from pathlib import Path

import click

from typst_ir.mapping.builder import MappingBuilder
from typst_ir.mapping.registry import NodeRegistry
from typst_ir.nodes import TypstDocument
from typst_ir.polish.applicator import apply_renumbering, apply_styles
from typst_ir.polish.config import StyleConfig, load_config
from typst_ir.polish.node_locator import locate_nodes
from typst_ir.polish.style_collector import collect_styles
from typst_ir.polish.types import PolishIR, RenumberOp, StyleOp


def _style_config_has_properties(style_cfg: StyleConfig) -> bool:
    return any(
        getattr(style_cfg, attr) is not None
        for attr in (
            "font_name",
            "font_name_chinese",
            "font_name_latin",
            "font_size",
            "font_style",
            "font_color",
            "line_spacing_before",
            "line_spacing_after",
            "line_spacing",
        )
    )


@click.command(name="generate-polish-ir")
@click.option(
    "--docx",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to input DOCX file",
)
@click.option(
    "--config",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to TOML polish configuration file",
)
@click.option(
    "--output-ir",
    required=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path for output Polish IR JSON",
)
def generate_polish_ir(docx: Path, config: Path, output_ir: Path) -> None:
    """Generate a Polish IR JSON from a DOCX and a TOML config.

    Loads the configuration, collects available styles from the DOCX,
    and writes a PolishIR JSON containing style operations (only for
    styles that have configured properties and exist in the DOCX)
    and renumber operations derived from the config.

    Args:
        docx: Path to the source DOCX file.
        config: Path to the TOML configuration file.
        output_ir: Path where the Polish IR JSON will be written.
    """
    cfg = load_config(config)
    collected = collect_styles(docx)

    style_ops: list[StyleOp] = []
    for name, style_cfg in cfg.styles.items():
        if name not in collected:
            continue
        if not _style_config_has_properties(style_cfg):
            continue
        style_ops.append(
            StyleOp(
                style_name=name,
                font_name=style_cfg.font_name,
                font_name_chinese=style_cfg.font_name_chinese,
                font_name_latin=style_cfg.font_name_latin,
                font_size=style_cfg.font_size,
                font_style=style_cfg.font_style,
                font_color=style_cfg.font_color,
                line_spacing_before=style_cfg.line_spacing_before,
                line_spacing_after=style_cfg.line_spacing_after,
                line_spacing=style_cfg.line_spacing,
            )
        )

    renumber_ops: list[RenumberOp] = []
    if cfg.renumber.headings:
        renumber_ops.append(RenumberOp(element_type="heading"))
    if cfg.renumber.figures:
        renumber_ops.append(RenumberOp(element_type="figure"))
    if cfg.renumber.tables:
        renumber_ops.append(RenumberOp(element_type="table"))

    ir = PolishIR(styles=style_ops, renumber=renumber_ops)
    output_ir.parent.mkdir(parents=True, exist_ok=True)
    output_ir.write_text(ir.model_dump_json(indent=2), encoding="utf-8")
    click.echo(f"✓ Polish IR written to {output_ir}")


@click.command(name="apply-polish-ir")
@click.option(
    "--docx",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to input DOCX file",
)
@click.option(
    "--polish-ir",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to Polish IR JSON file",
)
@click.option(
    "--ir-json",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to Typst IR JSON file (required when renumbering is requested)",
)
@click.option(
    "--output-docx",
    required=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path for output DOCX file",
)
def apply_polish_ir(
    docx: Path,
    polish_ir: Path,
    ir_json: Path | None,
    output_docx: Path,
) -> None:
    """Apply a Polish IR to a DOCX file and save the result.

    Loads the Polish IR, applies style operations to the DOCX styles,
    and if renumber operations are present, rebuilds the DOCX-to-IR
    mapping and applies renumbering.

    Args:
        docx: Path to the source DOCX file.
        polish_ir: Path to the Polish IR JSON file.
        ir_json: Path to the original Typst IR JSON file. Required when
            the Polish IR contains renumber operations.
        output_docx: Path where the polished DOCX will be written.
    """
    ir = PolishIR.model_validate_json(polish_ir.read_text(encoding="utf-8"))

    from docx import Document

    doc = Document(str(docx))
    # Styles are applied first because they are non-content-changing;
    # renumbering comes second because it mutates paragraph content.
    apply_styles(doc, ir.styles)

    if ir.renumber:
        if ir_json is None:
            raise click.UsageError(
                "--ir-json is required when polish IR contains renumber operations."
            )
        document = TypstDocument.model_validate_json(
            ir_json.read_text(encoding="utf-8")
        )
        registry = NodeRegistry()
        mapping = MappingBuilder(registry).build(document, str(docx))
        locator = locate_nodes(mapping, docx)
        apply_renumbering(doc, mapping, ir.renumber, locator)

    output_docx.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_docx))
    click.echo(f"✓ Polished DOCX saved to {output_docx}")
