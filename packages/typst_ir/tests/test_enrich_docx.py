"""Tests for DOCX enrichment catamorphism.

Verifies that ``enrich_with_docx_meta`` and ``annotate_body_blocks``
produce correct ``DocxMeta`` and local table/figure indices.
"""

from __future__ import annotations

from typst_ir import (
    TypstBulletList,
    TypstFigure,
    TypstHeading,
    TypstParagraph,
    TypstSection,
    TypstTable,
)
from typst_ir.enriched.docx_types import DocxMeta, EnrichedBlock
from typst_ir.enriched.enrich_docx import annotate_body_blocks, enrich_with_docx_meta
from typst_ir.enriched.enrich_path import enrich_with_path


class TestAnnotateBodyBlocks:
    """Unit tests for ``annotate_body_blocks``."""

    def test_all_blocks_get_enriched(self) -> None:
        """Every block receives an EnrichedBlock wrapper with DocxMeta."""
        blocks: list = [
            TypstParagraph(text="Hello"),
            TypstTable(data=[["a"]], headers=["h"]),
            TypstFigure(content="img.png", caption="A figure"),
        ]
        result = annotate_body_blocks(blocks, "1", [("section", 0)])

        assert len(result) == 3
        assert all(isinstance(r, EnrichedBlock) for r in result)

    def test_table_gets_indexed(self) -> None:
        """Tables receive a table_index in "section-ordinal" format."""
        blocks: list = [TypstTable(data=[["a"]], headers=["h"])]
        result = annotate_body_blocks(blocks, "1.2", [("section", 0), ("section", 1)])

        meta = result[0].meta
        assert meta.table_index == "1.2-1"
        assert meta.figure_index is None
        assert meta.path == [
            ("section", 0),
            ("section", 1),
            ("body", 0),
            ("table", 0),
        ]

    def test_figure_gets_indexed(self) -> None:
        """Figures receive a figure_index in "section-ordinal" format."""
        blocks: list = [TypstFigure(content="img.png", caption="A figure")]
        result = annotate_body_blocks(blocks, "2", [("section", 1)])

        meta = result[0].meta
        assert meta.figure_index == "2-1"
        assert meta.table_index is None
        assert meta.path == [
            ("section", 1),
            ("body", 0),
            ("figure", 0),
        ]

    def test_other_blocks_get_no_indices(self) -> None:
        """Non-table/figure blocks get None for both indices."""
        blocks: list = [TypstParagraph(text="Hello")]
        result = annotate_body_blocks(blocks, "1", [("section", 0)])

        meta = result[0].meta
        assert meta.table_index is None
        assert meta.figure_index is None
        assert meta.path == [("section", 0), ("body", 0)]

    def test_counters_increment_locally(self) -> None:
        """Table and figure counters increase independently within a section."""
        blocks: list = [
            TypstTable(data=[["a"]], headers=["h"]),
            TypstParagraph(text="Spacer"),
            TypstTable(data=[["b"]], headers=["h"]),
            TypstFigure(content="1.png", caption="Fig 1"),
            TypstFigure(content="2.png", caption="Fig 2"),
        ]
        result = annotate_body_blocks(blocks, "1", [("section", 0)])

        assert result[0].meta.table_index == "1-1"
        assert result[2].meta.table_index == "1-2"
        assert result[3].meta.figure_index == "1-1"
        assert result[4].meta.figure_index == "1-2"

    def test_body_positions_in_path(self) -> None:
        """The body index is reflected in the path for all blocks."""
        blocks: list = [
            TypstParagraph(text="First"),
            TypstParagraph(text="Second"),
        ]
        result = annotate_body_blocks(blocks, "1", [("section", 0)])

        assert result[0].meta.path == [("section", 0), ("body", 0)]
        assert result[1].meta.path == [("section", 0), ("body", 1)]

    def test_lists_are_atomic(self) -> None:
        """List blocks are treated as atomic (no traversal into items)."""
        blocks: list = [
            TypstBulletList(items=[[TypstParagraph(text="Item")]]),
        ]
        result = annotate_body_blocks(blocks, "1", [("section", 0)])

        assert len(result) == 1
        assert result[0].meta.path == [("section", 0), ("body", 0)]
        assert result[0].meta.table_index is None
        assert result[0].meta.figure_index is None


class TestEnrichWithDocxMeta:
    """Integration tests for ``enrich_with_docx_meta``."""

    def test_single_section_meta_transformed(self) -> None:
        """PathMeta on a single section is converted to DocxMeta."""
        root = TypstSection(
            heading=TypstHeading(text="Root"),
            body=[TypstParagraph(text="Hello")],
            subsections=[],
        )
        path_enriched = enrich_with_path(root)
        docx_enriched = enrich_with_docx_meta(path_enriched)

        meta = docx_enriched.unfix.meta
        assert isinstance(meta, DocxMeta)
        assert meta.section_index == "1"
        assert meta.depth == 1
        assert meta.path == [("section", 0)]

    def test_body_blocks_are_enriched(self) -> None:
        """Body blocks inside the section become EnrichedBlock instances."""
        root = TypstSection(
            heading=TypstHeading(text="Root"),
            body=[
                TypstParagraph(text="Hello"),
                TypstTable(data=[["a"]], headers=["h"]),
            ],
            subsections=[],
        )
        path_enriched = enrich_with_path(root)
        docx_enriched = enrich_with_docx_meta(path_enriched)

        body = docx_enriched.unfix.body
        assert len(body) == 2
        assert isinstance(body[0], EnrichedBlock)
        assert body[0].meta.section_index == "1"
        assert isinstance(body[1], EnrichedBlock)
        assert body[1].meta.table_index == "1-1"

    def test_nested_sections_get_independent_counters(self) -> None:
        """Each subsection resets its own table/figure counters."""
        child = TypstSection(
            heading=TypstHeading(text="Child"),
            body=[TypstTable(data=[["child"]], headers=["h"])],
            subsections=[],
        )
        root = TypstSection(
            heading=TypstHeading(text="Root"),
            body=[TypstTable(data=[["root"]], headers=["h"])],
            subsections=[child],
        )
        path_enriched = enrich_with_path(root)
        docx_enriched = enrich_with_docx_meta(path_enriched)

        root_table = docx_enriched.unfix.body[0]
        child_table = docx_enriched.unfix.subsections[0].unfix.body[0]

        assert root_table.meta.table_index == "1-1"
        assert child_table.meta.table_index == "1.1-1"

    def test_section_index_computed_from_path(self) -> None:
        """Section indices reflect the hierarchical path."""
        grandchild = TypstSection(
            heading=TypstHeading(text="Grandchild"),
            body=[],
            subsections=[],
        )
        child = TypstSection(
            heading=TypstHeading(text="Child"),
            body=[],
            subsections=[grandchild],
        )
        root = TypstSection(
            heading=TypstHeading(text="Root"),
            body=[],
            subsections=[child],
        )
        path_enriched = enrich_with_path(root)
        docx_enriched = enrich_with_docx_meta(path_enriched)

        assert docx_enriched.unfix.meta.section_index == "1"
        assert docx_enriched.unfix.subsections[0].unfix.meta.section_index == "1.1"
        assert (
            docx_enriched.unfix.subsections[0].unfix.subsections[0].unfix.meta.section_index
            == "1.1.1"
        )

    def test_mixed_body_block_types(self) -> None:
        """A mixture of block types all receive correct metadata."""
        root = TypstSection(
            heading=TypstHeading(text="Root"),
            body=[
                TypstParagraph(text="Intro"),
                TypstTable(data=[["a"]], headers=["h"]),
                TypstFigure(content="fig.png", caption="A fig"),
                TypstBulletList(items=[[TypstParagraph(text="Item")]]),
            ],
            subsections=[],
        )
        path_enriched = enrich_with_path(root)
        docx_enriched = enrich_with_docx_meta(path_enriched)

        body = docx_enriched.unfix.body
        assert body[0].meta.table_index is None
        assert body[0].meta.figure_index is None
        assert body[1].meta.table_index == "1-1"
        assert body[2].meta.figure_index == "1-1"
        assert body[3].meta.table_index is None
        assert body[3].meta.figure_index is None
