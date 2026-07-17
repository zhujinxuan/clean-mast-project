"""Typst IR block type extraction.

Walks a ``TypstDocument`` tree and builds a map from path strings to
block type metadata, used by the DOCX styling pipeline to determine
which style to apply to each block.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from typst_ir.nodes import (
    TypstDocument,
    TypstFigure,
    TypstSection,
    TypstTable,
)


@dataclass(frozen=True)
class TypstBlockType:
    """Type metadata for a block in the Typst IR tree.

    Attributes:
        path: IR path identifier (e.g. ``section0body2table0``).
        block_type: The Python type of the block (e.g. ``TypstTable``).
        heading_level: For heading blocks, the heading level (1-5).
        has_caption: Whether the block has a caption (tables/figures).
    """

    path: str
    block_type: Type
    heading_level: int | None = None
    has_caption: bool = False


def _path_to_id(path: list[tuple[str, int]]) -> str:
    """Convert a structural path into a concatenated identifier string."""
    return "".join(f"{ctx}{idx}" for ctx, idx in path)


def _walk_section(
    section: TypstSection,
    path: list[tuple[str, int]],
    result: dict[str, TypstBlockType],
) -> None:
    """Recursively walk a section and populate the result map."""
    _path_to_id(path)

    # Record heading
    heading_level = min(len(path), 5)
    heading_path = path + [("heading", 0)]
    heading_id = _path_to_id(heading_path)
    result[heading_id] = TypstBlockType(
        path=heading_id,
        block_type=type(section.heading),
        heading_level=heading_level,
        has_caption=False,
    )

    # Walk body blocks
    table_idx = 0
    figure_idx = 0
    for body_idx, block in enumerate(section.body):
        body_path = path + [("body", body_idx)]

        if isinstance(block, TypstTable):
            block_path = body_path + [("table", table_idx)]
            table_idx += 1
        elif isinstance(block, TypstFigure):
            block_path = body_path + [("figure", figure_idx)]
            figure_idx += 1
        else:
            block_path = body_path

        block_id = _path_to_id(block_path)
        result[block_id] = TypstBlockType(
            path=block_id,
            block_type=type(block),
            has_caption=getattr(block, "caption", None) is not None
            and getattr(block, "caption", "") != "",
        )

    # Walk subsections
    for sub_idx, subsection in enumerate(section.subsections):
        sub_path = path + [("section", sub_idx)]
        _walk_section(subsection, sub_path, result)


def build_block_type_map(doc: TypstDocument) -> dict[str, TypstBlockType]:
    """Build a map from IR path to block type metadata.

    Args:
        doc: The TypstDocument to walk.

    Returns:
        Dictionary mapping path strings to ``TypstBlockType`` objects.
    """
    result: dict[str, TypstBlockType] = {}
    for sec_idx, section in enumerate(doc.children):
        path = [("section", sec_idx)]
        _walk_section(section, path, result)
    return result


__all__ = [
    "TypstBlockType",
    "build_block_type_map",
]
