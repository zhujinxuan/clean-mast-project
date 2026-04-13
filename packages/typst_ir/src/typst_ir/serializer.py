"""Typst IR serializer - converts IR nodes to Typst markup strings.

Provides the serialize() function to convert a TypstDocument IR tree
into valid Typst markup that can be compiled with the typst CLI.
"""

from __future__ import annotations

from typing import cast

from typst_ir.nodes import (
    TypstBlock,
    TypstBulletList,
    TypstCodeBlock,
    TypstDocument,
    TypstEquation,
    TypstFigure,
    TypstHeading,
    TypstOrderedList,
    TypstParagraph,
    TypstRawBlock,
    TypstSection,
    TypstTable,
)


def _serialize_block(block: TypstBlock, depth: int = 1) -> str:
    """Serialize a single block to Typst markup.

    Internal helper that dispatches to appropriate serializer
    based on block type.
    """
    if hasattr(block, 'data') and hasattr(block, 'headers'):
        return _serialize_table(cast(TypstTable, block))
    elif hasattr(block, 'content') and hasattr(block, 'caption') and hasattr(block, 'kind'):
        return _serialize_figure(cast(TypstFigure, block))
    elif getattr(block, 'typst_type', None) == 'TypstHeading':
        return _serialize_heading(cast(TypstHeading, block), level=depth)
    elif hasattr(block, 'latex') and hasattr(block, 'display'):
        return _serialize_equation(cast(TypstEquation, block))
    elif hasattr(block, 'text') and hasattr(block, 'language'):
        return _serialize_code_block(cast(TypstCodeBlock, block))
    elif hasattr(block, 'format') and hasattr(block, 'text'):
        return _serialize_raw_block(cast(TypstRawBlock, block))
    elif hasattr(block, 'text'):
        return _serialize_paragraph(cast(TypstParagraph, block))
    elif hasattr(block, 'heading') and hasattr(block, 'body') and hasattr(block, 'subsections'):
        return _serialize_section(cast(TypstSection, block), depth=depth)
    elif hasattr(block, 'items') and hasattr(block, 'start'):
        return _serialize_ordered_list(cast(TypstOrderedList, block), depth=depth)
    elif hasattr(block, 'items'):
        return _serialize_bullet_list(block, depth=depth)
    else:
        raise TypeError(f"Unknown block type: {type(block).__name__}")


def _serialize_document(node: TypstDocument) -> str:
    parts: list[str] = []
    for child in node.children:
        parts.append(_serialize_section(child, depth=1))
    return "\n".join(parts)


def serialize(node: TypstDocument) -> str:
    """Serialize a TypstDocument IR tree to Typst markup string.

    Converts a complete document IR tree into valid Typst markup.

    Example:
        >>> doc = TypstDocument(children=[
        ...     TypstSection(
        ...         heading=TypstHeading(text="Introduction"),
        ...         body=[TypstParagraph(text="This is a test.")],
        ...         subsections=[],
        ...     ),
        ... ])
        >>> print(serialize(doc))
        = Introduction
        This is a test.
        <BLANKLINE>
    """
    if not hasattr(node, 'children'):
        raise TypeError(f"Expected TypstDocument root, got {type(node).__name__}")
    return _serialize_document(node)


def _serialize_table(table: TypstTable) -> str:
    """Serialize a TypstTable to Typst markup.

    Produces output matching the golden snapshot format:
    #table(
      columns: (auto, auto, ...),
      inset: 8pt,
      align: center,
      table.header([...], [...]),
      [...],
      ...
    )

    If caption is present, wraps in #figure().
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

    # Columns spec - all auto
    col_specs = ", ".join(["auto"] * num_cols)
    lines.append(f"  columns: ({col_specs}),")
    lines.append("  inset: 8pt,")
    lines.append("  align: center,")

    # Header row
    header_cells = ", ".join([f"[{h}]" for h in table.headers])
    lines.append("  table.header(")
    lines.append(f"    {header_cells}")
    lines.append("  ),")

    # Data rows
    for row in table.data:
        row_cells = ", ".join([f"[{cell}]" for cell in row])
        lines.append(f"  {row_cells},")

    lines.append(")")
    table_markup = "\n".join(lines)

    if table.caption:
        # Strip leading '#' from table markup when nesting inside figure
        # (in Typst code mode, nested function calls don't use '#')
        nested_table = table_markup.lstrip("#").replace(chr(10), chr(10) + "  ")
        return f"""#figure(
  {nested_table},
  caption: [{table.caption}],
)
"""

    return table_markup + "\n"


def _serialize_figure(fig: TypstFigure) -> str:
    """Serialize a TypstFigure to Typst markup.

    Produces output matching the pattern from renderImageTypst():
    #figure(
      image("path", width: 80%),
      caption: [text],
    ) <fig-hashkey>
    """
    if not fig.content:
        raise ValueError("Figure content (image path) cannot be empty")

    return f"""#figure(
  image("{fig.content}", width: 80%),
  caption: [{fig.caption}],
)
"""


def _serialize_heading(heading: TypstHeading, *, level: int = 1) -> str:
    """Serialize a TypstHeading to Typst markup.

    Normalizes level to a minimum of 1 and produces
    '=' repeated `level` times before the text.
    """
    level = max(1, level)
    marker = "=" * level
    return f"{marker} {heading.text}\n"


def _serialize_paragraph(para: TypstParagraph) -> str:
    """Serialize a TypstParagraph to Typst markup."""
    return f"{para.text}\n\n"


def _serialize_section(section: TypstSection, depth: int = 1) -> str:
    """Serialize a TypstSection to Typst markup.

    Produces output with heading followed by nested content:
    = Heading
    [serialized children]
    """
    parts: list[str] = []
    parts.append(_serialize_heading(section.heading, level=depth))
    for item in section.body:
        parts.append(_serialize_block(item, depth=depth))
    for sub in section.subsections:
        parts.append(_serialize_section(sub, depth=depth + 1))
    return "".join(parts)


def _serialize_bullet_list(bullet_list: TypstBulletList, depth: int = 1) -> str:
    """Serialize a TypstBulletList to Typst markup.

    Produces output with bullet markers:
    - [item content]
    - [item content]
    """
    parts: list[str] = []
    for item in bullet_list.items:
        item_content = " ".join([_serialize_block(block, depth=depth).strip() for block in item])
        parts.append(f"- {item_content}")
    return "\n".join(parts) + "\n"


def _serialize_ordered_list(ordered_list: TypstOrderedList, depth: int = 1) -> str:
    """Serialize a TypstOrderedList to Typst markup.

    Produces output with numbered markers:
    + [item content]
    + [item content]

    Uses the start attribute for numbering offset.
    """
    parts: list[str] = []
    for idx, item in enumerate(ordered_list.items):
        item_content = " ".join([_serialize_block(block, depth=depth).strip() for block in item])
        if ordered_list.start != 1 or idx > 0:
            parts.append(f"+ {item_content}")
        else:
            parts.append(f"+ {item_content}")
    return "\n".join(parts) + "\n"


def _serialize_equation(equation: TypstEquation) -> str:
    """Serialize a TypstEquation to Typst markup.

    Produces output for inline or display equations:
    - Inline: $E = mc^2$
    - Display: $ E = mc^2 $
    """
    if equation.display:
        return f"$ {equation.latex} $"
    return f"${equation.latex}$"


def _serialize_code_block(code_block: TypstCodeBlock) -> str:
    """Serialize a TypstCodeBlock to Typst markup.

    Produces output using Typst's raw function:
    #raw("code", lang: "python")

    If no language is specified, omits the lang parameter.
    """
    if code_block.language:
        return f'#raw("{code_block.text}", lang: "{code_block.language}")'
    return f'#raw("{code_block.text}")'


def _serialize_raw_block(raw_block: TypstRawBlock) -> str:
    """Serialize a TypstRawBlock to Typst markup.

    Produces output as raw content with format specification:
    #raw("content", format: "html")
    """
    return f'#raw("{raw_block.text}", format: "{raw_block.format}")'
