"""DOCX enrichment catamorphism for Typst IR sections.

Provides `enrich_with_docx_meta` for transforming path-enriched section
trees into DOCX-enriched trees with local table/figure indexing.
"""

from __future__ import annotations

from typst_ir.enriched.cata import cata_enriched
from typst_ir.enriched.docx_types import DocxMeta, EnrichedBlock, PathMeta
from typst_ir.enriched.enrich_path import compute_section_index
from typst_ir.enriched.types import EnrichedSectionF, EnrichedSectionFFix
from typst_ir.nodes import TypstBodyBlock, TypstFigure, TypstTable


def annotate_body_blocks(
    blocks: list[TypstBodyBlock],
    section_idx: str,
    base_path: list[tuple[str, int]],
) -> list[EnrichedBlock]:
    """Annotate each body block with DocxMeta, counting tables/figures locally.

    -- Haskell:
    -- annotateBodyBlocks :: [TypstBodyBlock] -> String -> [(String, Int)] -> [EnrichedBlock]
    -- annotateBodyBlocks blocks sectionIdx basePath = foldl' step [] (zip blocks [0..])
    --   where step acc (block, bodyIdx) = ...

    Args:
        blocks: The body blocks to annotate.
        section_idx: Dotted section index string (e.g., "1.2").
        base_path: The section's structural path prefix.

    Returns:
        A list of ``EnrichedBlock`` values with ``DocxMeta``.
        Tables and figures receive incremented local indices;
        other blocks get ``table_index=None`` and ``figure_index=None``.
    """
    enriched: list[EnrichedBlock] = []
    table_idx = 0
    figure_idx = 0

    for body_idx, block in enumerate(blocks):
        body_path = base_path + [("body", body_idx)]

        if isinstance(block, TypstTable):
            path = body_path + [("table", table_idx)]
            meta = DocxMeta(
                depth=len(path),
                path=path,
                section_index=section_idx,
                table_index=f"{section_idx}-{table_idx + 1}",
                figure_index=None,
            )
            table_idx += 1
        elif isinstance(block, TypstFigure):
            path = body_path + [("figure", figure_idx)]
            meta = DocxMeta(
                depth=len(path),
                path=path,
                section_index=section_idx,
                table_index=None,
                figure_index=f"{section_idx}-{figure_idx + 1}",
            )
            figure_idx += 1
        else:
            path = body_path
            meta = DocxMeta(
                depth=len(path),
                path=path,
                section_index=section_idx,
                table_index=None,
                figure_index=None,
            )

        enriched.append(EnrichedBlock(block=block, meta=meta))

    return enriched


def enrich_with_docx_meta(
    section: EnrichedSectionFFix[PathMeta, TypstBodyBlock],
) -> EnrichedSectionFFix[DocxMeta, EnrichedBlock]:
    """Transform a path-enriched section tree into a DOCX-enriched tree.

    -- Haskell:
    -- enrichWithDocxMeta :: EnrichedSectionFFix PathMeta TypstBodyBlock
    --                      -> EnrichedSectionFFix DocxMeta EnrichedBlock
    -- enrichWithDocxMeta = cata alg
    --   where alg layer = ...

    Args:
        section: A section tree enriched with ``PathMeta``.

    Returns:
        A section tree enriched with ``DocxMeta`` and ``EnrichedBlock`` body items.
    """

    def algebra(
        layer: EnrichedSectionF[
            PathMeta,
            TypstBodyBlock,
            EnrichedSectionFFix[DocxMeta, EnrichedBlock],
        ],
    ) -> EnrichedSectionFFix[DocxMeta, EnrichedBlock]:
        section_idx = compute_section_index(layer.meta.path)
        enriched_body = annotate_body_blocks(
            layer.body,
            section_idx,
            layer.meta.path,
        )
        docx_meta = DocxMeta(
            depth=layer.meta.depth,
            path=layer.meta.path,
            section_index=section_idx,
        )
        return EnrichedSectionFFix(
            unfix=EnrichedSectionF(
                meta=docx_meta,
                heading=layer.heading,
                body=enriched_body,
                subsections=layer.subsections,
            )
        )

    return cata_enriched(section, algebra)
