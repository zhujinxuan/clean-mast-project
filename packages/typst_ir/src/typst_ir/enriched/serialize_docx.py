"""DOCX-specific enriched section serializer.

Provides serialization of DOCX-enriched sections to Typst markup with
cross-reference markers and indexed captions.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import cast

from typst_ir.enriched.cata import cata_enriched
from typst_ir.enriched.docx_types import DocxMeta, EnrichedBlock, path_to_id
from typst_ir.enriched.enrich_docx import enrich_with_docx_meta
from typst_ir.enriched.enrich_path import enrich_document_with_path
from typst_ir.enriched.serialize_typst import (
    serialize_bullet_list,
    serialize_code_block,
    serialize_equation,
    serialize_heading,
    serialize_ordered_list,
    serialize_paragraph,
    serialize_raw_block,
)
from typst_ir.enriched.types import EnrichedSectionF
from typst_ir.nodes import (
    TypstBulletList,
    TypstCodeBlock,
    TypstDocument,
    TypstEquation,
    TypstFigure,
    TypstHeading,
    TypstOrderedList,
    TypstParagraph,
    TypstRawBlock,
    TypstTable,
)


def serialize_table_with_index(table: TypstTable, table_index: str) -> str:
    """Serialize a table with DOCX index caption.

    -- Haskell:
    -- serializeTableWithIndex :: TypstTable -> String -> String
    -- serializeTableWithIndex table idx = tableMarkup ++ "\n表" ++ idx ++ " " ++ caption ++ "\n"

    Args:
        table: The table to serialize.
        table_index: The table index string (e.g., "1.2-1").

    Returns:
        Typst markup for the table followed by its indexed caption.
    """
    if not table.data:
        raise ValueError("Table data cannot be empty")

    num_cols = len(table.headers)
    for row in table.data:
        if len(row) != num_cols:
            raise ValueError(
                f"Header column count ({num_cols}) "
                f"does not match data row column count ({len(row)})"
            )

    lines: list[str] = ["#table("]
    col_specs = ", ".join(["auto"] * num_cols)
    lines.append(f"  columns: ({col_specs}),")
    lines.append("  inset: 8pt,")
    lines.append("  align: center,")
    header_cells = ", ".join([f"[{h}]" for h in table.headers])
    lines.append("  table.header(")
    lines.append(f"    {header_cells}")
    lines.append("  ),")
    for row in table.data:
        row_cells = ", ".join([f"[{cell}]" for cell in row])
        lines.append(f"  {row_cells},")
    lines.append(")")
    table_markup = "\n".join(lines)

    if table.caption:
        nested_table = table_markup.lstrip("#").replace("\n", "\n  ")
        return f"""#figure(
  caption: [表 {table_index} {table.caption}],
  {nested_table},
)
"""

    return table_markup + "\n"


def serialize_figure_with_index(figure: TypstFigure, figure_index: str) -> str:
    """Serialize a figure with DOCX index caption.

    -- Haskell:
    -- serializeFigureWithIndex :: TypstFigure -> String -> String
    -- serializeFigureWithIndex fig idx = figMarkup ++ "\n图" ++ idx ++ " " ++ caption ++ "\n"

    Args:
        figure: The figure to serialize.
        figure_index: The figure index string (e.g., "1.2-1").

    Returns:
        Typst markup for the figure followed by its indexed caption.
    """
    if not figure.content:
        raise ValueError("Figure content (image path) cannot be empty")

    figure_markup = f"""#figure(
  image("{figure.content}", width: 80%),
  caption: [图 {figure_index} {figure.caption}],
)
"""

    return figure_markup


def _serialize_docx_block_inner(block: EnrichedBlock) -> str:
    """Dispatch block serialization for DOCX-enriched blocks.

    Args:
        block: An enriched block with DOCX metadata.

    Returns:
        Typst markup string for the block content (without markers).
    """
    b = block.block
    depth = block.meta.depth

    match b.typst_type:
        case "TypstParagraph":
            return serialize_paragraph(cast(TypstParagraph, b))
        case "TypstTable":
            table_index = block.meta.table_index
            if table_index is None:
                raise ValueError("TypstTable block missing table_index in DocxMeta")
            return serialize_table_with_index(cast(TypstTable, b), table_index)
        case "TypstFigure":
            figure_index = block.meta.figure_index
            if figure_index is None:
                raise ValueError("TypstFigure block missing figure_index in DocxMeta")
            return serialize_figure_with_index(cast(TypstFigure, b), figure_index)
        case "TypstEquation":
            return serialize_equation(cast(TypstEquation, b))
        case "TypstCodeBlock":
            return serialize_code_block(cast(TypstCodeBlock, b))
        case "TypstRawBlock":
            return serialize_raw_block(cast(TypstRawBlock, b))
        case "TypstHeading":
            return serialize_heading(cast(TypstHeading, b), depth)
        case "TypstBulletList":
            return serialize_bullet_list(cast(TypstBulletList, b), depth)
        case "TypstOrderedList":
            return serialize_ordered_list(cast(TypstOrderedList, b), depth)
        case _:
            raise ValueError(f"Unknown block type: {b.typst_type}")


def serialize_docx_algebra(
    layer: EnrichedSectionF[DocxMeta, EnrichedBlock, str],
) -> str:
    """Serialize a DOCX-enriched section layer to Typst markup.

    -- Haskell:
    -- serializeDocxAlgebra :: EnrichedSectionF DocxMeta EnrichedBlock String -> String
    -- serializeDocxAlgebra layer =
    --   let sid = pathToId (path (meta layer))
    --   in  "#raw(\"irstart:" ++ sid ++ "\")\n"
    --       ++ "= " ++ sectionIndex (meta layer) ++ " " ++ headingText (heading layer) ++ "\n"
    --       ++ concatMap serializeBlock (body layer)
    --       ++ concat (subsections layer)
    --       ++ "#raw(\"irend:" ++ sid ++ "\")\n"
    --   where serializeBlock b =
    --           let bid = pathToId (path (meta b))
    --           in  "#raw(\"irstart:" ++ bid ++ "\")\n"
    --               ++ serializeBlockInner b
    --               ++ "#raw(\"irend:" ++ bid ++ "\")\n"

    Args:
        layer: A functorial section layer with DocxMeta, EnrichedBlock body,
            and string subsections (already serialized).

    Returns:
        Typst markup string with cross-reference markers.
    """
    section_id = path_to_id(layer.meta.path)
    heading_id = path_to_id(layer.meta.path + [("heading", 0)])
    parts: list[str] = []

    parts.append(f'#raw("irstart:{section_id}")\n\n')
    parts.append(f'#raw("irstart:{heading_id}")\n\n')
    parts.append(f"= {layer.meta.section_index} {layer.heading.text}\n\n")
    parts.append(f'#raw("irend:{heading_id}")\n\n')

    for block in layer.body:
        block_id = path_to_id(block.meta.path)
        inner = _serialize_docx_block_inner(block).rstrip("\n")
        parts.append(f'#raw("irstart:{block_id}")\n\n')
        parts.append(inner + "\n\n")
        parts.append(f'#raw("irend:{block_id}")\n\n')

    for subsection in layer.subsections:
        parts.append(subsection)

    parts.append(f'#raw("irend:{section_id}")\n\n')

    return "".join(parts)


def draft_docx(input_json: Path, output: Path | None = None) -> Path:
    """Render a TypstDocument JSON file to DOCX via typst and pandoc.

    Loads the document, enriches each section with path and DOCX metadata,
    serializes to Typst markup, writes the .typ file, compiles to PDF for
    validation, then converts the .typ file to DOCX via pandoc. Cleans up
    intermediate files before returning.

    Args:
        input_json: Path to the JSON file containing a TypstDocument.
        output: Optional path for the output DOCX file.

    Returns:
        Path to the generated DOCX file.

    Raises:
        FileNotFoundError: If the input JSON file does not exist.
        RuntimeError: If ``typst`` or ``pandoc`` is not found in PATH,
            or if compilation/conversion fails.
    """
    if not input_json.exists():
        raise FileNotFoundError(f"Input file not found: {input_json}")

    if not shutil.which("typst"):
        raise RuntimeError(
            "typst not found in PATH. DOCX generation requires typst.\n"
            "Install from: https://github.com/typst/typst/releases\n"
            "  macOS: brew install typst\n"
            "  Linux: Download binary from GitHub\n"
            "  Windows: winget install Typst.Typst"
        )
    if not shutil.which("pandoc"):
        raise RuntimeError(
            "pandoc not found in PATH. DOCX generation requires pandoc.\n"
            "Install from: https://pandoc.org/installing.html\n"
            "  Ubuntu/Debian: sudo apt-get install pandoc\n"
            "  macOS: brew install pandoc\n"
            "  Windows: choco install pandoc or winget install JohnMacFarlane.Pandoc"
        )

    doc = TypstDocument.model_validate_json(input_json.read_text(encoding="utf-8"))
    enriched_doc = enrich_document_with_path(doc)
    typst_parts = [
        cata_enriched(
            enrich_with_docx_meta(child),
            serialize_docx_algebra,
        )
        for child in enriched_doc.unfix.children
    ]
    typst_content = "\n".join(typst_parts)

    docx_file = output or input_json.with_name(input_json.stem.replace(".typ", "") + "_draft.docx")
    typ_file = input_json.with_suffix(".typ")
    pdf_file = typ_file.with_suffix(".pdf")

    typ_file.write_text(typst_content, encoding="utf-8")
    try:
        subprocess.run(
            ["typst", "compile", str(typ_file)],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            [
                "pandoc",
                typ_file.name,
                "-o", docx_file.name,
                "-f", "typst",
                "-t", "docx",
            ],
            capture_output=True,
            check=True,
            cwd=typ_file.parent,
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode("utf-8", errors="replace") if e.stderr else "Unknown error"
        raise RuntimeError(f"Compilation or conversion failed: {error_msg}")
    finally:
        if typ_file.exists():
            typ_file.unlink()
        if pdf_file.exists():
            pdf_file.unlink()

    return docx_file
