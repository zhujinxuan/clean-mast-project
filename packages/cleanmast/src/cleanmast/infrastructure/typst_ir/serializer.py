"""Typst IR serializer - converts IR nodes to Typst markup strings.

Provides the serialize() function to convert a TypstDocument IR tree
into valid Typst markup that can be compiled with the typst CLI.
"""

from __future__ import annotations

from cleanmast.subdomains.assessment.domain.types import (
    TypstDocument,
    TypstFigure,
    TypstHeading,
    TypstParagraph,
    TypstTable,
)


def serialize(node: TypstDocument) -> str:
    """Serialize a TypstDocument IR tree to Typst markup string.

    Converts a complete document IR tree into valid Typst markup.
    Validates the structure and produces output that compiles with typst CLI.

    Args:
        node: The root TypstDocument to serialize

    Returns:
        Valid Typst markup string

    Raises:
        TypeError: If node is not a TypstDocument or contains invalid children
        ValueError: If node validation fails (empty data, mismatched columns, etc.)

    Example:
        >>> doc = TypstDocument(children=[
        ...     TypstHeading(text="Introduction", level=1),
        ...     TypstParagraph(text="This is a test."),
        ... ])
        >>> print(serialize(doc))
        = Introduction

        This is a test.
    """
    if not isinstance(node, TypstDocument):
        raise TypeError(f"Expected TypstDocument root, got {type(node).__name__}")

    parts: list[str] = []
    for child in node.children:
        if isinstance(child, TypstTable):
            parts.append(_serialize_table(child))
        elif isinstance(child, TypstFigure):
            parts.append(_serialize_figure(child))
        elif isinstance(child, TypstHeading):
            parts.append(_serialize_heading(child))
        elif isinstance(child, TypstParagraph):
            parts.append(_serialize_paragraph(child))
        else:
            raise TypeError(f"Invalid child type: {type(child).__name__}")
    return "\n".join(parts)


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


def _serialize_heading(heading: TypstHeading) -> str:
    """Serialize a TypstHeading to Typst markup.

    Normalizes level to 1-3 range and produces:
    = text      (level 1)
    == text     (level 2)
    === text    (level 3)
    """
    level = max(1, min(3, heading.level))
    marker = "=" * level
    return f"{marker} {heading.text}\n"


def _serialize_paragraph(para: TypstParagraph) -> str:
    """Serialize a TypstParagraph to Typst markup."""
    return f"{para.text}\n"
