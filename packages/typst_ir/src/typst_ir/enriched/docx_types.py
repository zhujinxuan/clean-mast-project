"""DOCX-specific enriched types for Typst IR.

Provides metadata structures and helpers for DOCX rendering pipelines,
where structural paths and indexing are needed for cross-referencing.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from typst_ir.nodes import TypstBodyBlock


@dataclass(frozen=True)
class PathMeta:
    """Hierarchical path metadata for a document node.

    -- Haskell:
    -- data PathMeta = PathMeta { depth :: Int, path :: [(String, Int)] }

    Attributes:
        depth: Nesting depth of the node in the document hierarchy.
        path: Structural path as a list of (context, index) pairs.
    """

    depth: int
    path: list[tuple[str, int]]


@dataclass(frozen=True)
class DocxMeta:
    """Full DOCX metadata for enriched blocks.

    -- Haskell:
    -- data DocxMeta = DocxMeta
    --   { depth :: Int
    --   , path :: [(String, Int)]
    --   , section_index :: String
    --   , table_index :: Maybe String
    --   , figure_index :: Maybe String }

    Attributes:
        depth: Nesting depth of the block.
        path: Structural path as a list of (context, index) pairs.
        section_index: Section index string (e.g., "1.2").
        table_index: Optional table index string.
        figure_index: Optional figure index string.
    """

    depth: int
    path: list[tuple[str, int]]
    section_index: str
    table_index: str | None = None
    figure_index: str | None = None


class EnrichedBlock(BaseModel):
    """A body block enriched with DOCX metadata.

    -- Haskell:
    -- data EnrichedBlock = EnrichedBlock
    --   { block :: TypstBodyBlock, meta :: DocxMeta }

    Attributes:
        block: The underlying Typst body block.
        meta: DOCX metadata for the block.
    """

    model_config = ConfigDict(frozen=True)

    block: TypstBodyBlock
    meta: DocxMeta


def path_to_id(path: list[tuple[str, int]]) -> str:
    """Convert a structural path into a concatenated identifier string.

    -- Haskell:
    -- pathToId :: [(String, Int)] -> String
    -- pathToId = concatMap (\\(ctx, idx) -> ctx ++ show idx)

    Args:
        path: List of (context, index) pairs.

    Returns:
        Concatenated identifier like ``"section0body2table0"``.
    """
    return "".join(f"{ctx}{idx}" for ctx, idx in path)
