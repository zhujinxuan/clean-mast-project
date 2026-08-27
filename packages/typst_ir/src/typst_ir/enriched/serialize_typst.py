"""Enriched section serializer for Typst output."""

from __future__ import annotations

from typing import cast

from typst_ir.enriched.cata import cata_enriched
from typst_ir.enriched.types import DepthMeta, EnrichedSectionF, EnrichedSectionFFix
from typst_ir.nodes import (
    TypstBodyBlock,
    TypstBulletList,
    TypstCodeBlock,
    TypstEquation,
    TypstFigure,
    TypstHeading,
    TypstOrderedList,
    TypstParagraph,
    TypstRawBlock,
    TypstTable,
)


def serialize_block(block: TypstBodyBlock, depth: int) -> str:
    match block.typst_type:
        case "TypstParagraph":
            return serialize_paragraph(cast(TypstParagraph, block))
        case "TypstTable":
            return serialize_table(cast(TypstTable, block))
        case "TypstFigure":
            return serialize_figure(cast(TypstFigure, block))
        case "TypstEquation":
            return serialize_equation(cast(TypstEquation, block))
        case "TypstCodeBlock":
            return serialize_code_block(cast(TypstCodeBlock, block))
        case "TypstRawBlock":
            return serialize_raw_block(cast(TypstRawBlock, block))
        case "TypstHeading":
            return serialize_heading(cast(TypstHeading, block), depth)
        case "TypstBulletList":
            return serialize_bullet_list(cast(TypstBulletList, block), depth)
        case "TypstOrderedList":
            return serialize_ordered_list(cast(TypstOrderedList, block), depth)
        case _:
            raise ValueError(f"Unknown block type: {block.typst_type}")


def serialize_paragraph(block: TypstParagraph) -> str:
    return f"{block.text}\n\n"


def serialize_table(block: TypstTable) -> str:
    if not block.data:
        raise ValueError("Table data cannot be empty")

    num_cols = len(block.headers)
    for row in block.data:
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
    header_cells = ", ".join([f"[{h}]" for h in block.headers])
    lines.append("  table.header(")
    lines.append(f"    {header_cells}")
    lines.append("  ),")
    for row in block.data:
        row_cells = ", ".join([f"[{cell}]" for cell in row])
        lines.append(f"  {row_cells},")
    lines.append(")")
    table_markup = "\n".join(lines)

    if block.caption:
        nested_table = table_markup.lstrip("#").replace("\n", "\n  ")
        return f"""#figure(
  {nested_table},
  caption: [{block.caption}],
)
"""

    return table_markup + "\n"


def serialize_figure(block: TypstFigure) -> str:
    if not block.content:
        raise ValueError("Figure content (image path) cannot be empty")

    return f"""#figure(
  image("{block.content}", width: 80%),
  caption: [{block.caption}],
)
"""


def serialize_equation(block: TypstEquation) -> str:
    if block.display:
        # Display math is a block element: terminate so a following heading
        # or figure starts on its own line (typst headings require line start).
        return f"$ {block.latex} $\n\n"
    return f"${block.latex}$"


def serialize_code_block(block: TypstCodeBlock) -> str:
    if block.language:
        return f'#raw("{block.text}", lang: "{block.language}")'
    return f'#raw("{block.text}")'


def serialize_raw_block(block: TypstRawBlock) -> str:
    return f'#raw("{block.text}", format: "{block.format}")'


def serialize_heading(block: TypstHeading, depth: int) -> str:
    depth = max(1, depth)
    marker = "=" * depth
    return f"{marker} {block.text}\n"


def serialize_bullet_list(block: TypstBulletList, depth: int) -> str:
    parts: list[str] = []
    for item in block.items:
        item_content = " ".join(
            [serialize_block(cast(TypstBodyBlock, b), depth).strip() for b in item]
        )
        parts.append(f"- {item_content}")
    return "\n".join(parts) + "\n"


def serialize_ordered_list(block: TypstOrderedList, depth: int) -> str:
    parts: list[str] = []
    for idx, item in enumerate(block.items):
        item_content = " ".join(
            [serialize_block(cast(TypstBodyBlock, b), depth).strip() for b in item]
        )
        if block.start != 1 or idx > 0:
            parts.append(f"+ {item_content}")
        else:
            parts.append(f"+ {item_content}")
    return "\n".join(parts) + "\n"


def serialize_algebra(
    layer: EnrichedSectionF[DepthMeta, TypstBodyBlock, str],
) -> str:
    parts: list[str] = []
    parts.append(serialize_heading(layer.heading, layer.meta.depth))
    for block in layer.body:
        parts.append(serialize_block(block, layer.meta.depth))
    for subsection in layer.subsections:
        parts.append(subsection)
    return "".join(parts)


def serialize(section: EnrichedSectionFFix[DepthMeta, TypstBodyBlock]) -> str:
    return cata_enriched(section, serialize_algebra)
