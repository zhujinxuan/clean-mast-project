"""Tests for document-level enrichment types and functions.

Verifies that ``enrich_document_with_path`` annotates each top-level section
with the correct ``PathMeta``, and that ``map_document_children`` correctly
applies an algebra across document children.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from typst_ir import TypstDocument, TypstHeading, TypstParagraph, TypstSection
from typst_ir.enriched.cata import map_document_children
from typst_ir.enriched.docx_types import PathMeta
from typst_ir.enriched.enrich_path import enrich_document_with_path
from typst_ir.enriched.types import (
    DepthMeta,
    EnrichedDocument,
    EnrichedDocumentF,
    EnrichedDocumentFix,
    EnrichedSectionF,
    EnrichedSectionFFix,
)


class TestEnrichedDocumentTypes:
    """Tests for document-level enriched type instantiation."""

    def test_enriched_document_f_instantiation(self) -> None:
        """EnrichedDocumentF instantiates with generic Meta and A types."""
        doc = EnrichedDocumentF(
            meta=DepthMeta(depth=0),
            children=[1, 2, 3],
        )
        assert doc.meta.depth == 0
        assert doc.children == [1, 2, 3]

    def test_enriched_document_f_with_string_meta(self) -> None:
        """EnrichedDocumentF accepts arbitrary meta types."""
        doc = EnrichedDocumentF(
            meta="root",
            children=["a", "b"],
        )
        assert doc.meta == "root"
        assert doc.children == ["a", "b"]

    def test_enriched_document_instantiation(self) -> None:
        """EnrichedDocument wraps a list of EnrichedSectionFFix children."""
        section = EnrichedSectionFFix(
            unfix=EnrichedSectionF(
                meta=DepthMeta(depth=1),
                heading=TypstHeading(text="Section"),
                body=[],
                subsections=[],
            )
        )
        doc = EnrichedDocument(children=[section])
        assert len(doc.children) == 1
        assert doc.children[0].unfix.heading.text == "Section"

    def test_enriched_document_empty_children(self) -> None:
        """EnrichedDocument accepts an empty children list."""
        doc = EnrichedDocument(children=[])
        assert doc.children == []

    def test_enriched_document_fix_instantiation(self) -> None:
        """EnrichedDocumentFix wraps an EnrichedDocument in a fixed-point layer."""
        section = EnrichedSectionFFix(
            unfix=EnrichedSectionF(
                meta=DepthMeta(depth=1),
                heading=TypstHeading(text="Section"),
                body=[],
                subsections=[],
            )
        )
        inner = EnrichedDocument(children=[section])
        doc_fix = EnrichedDocumentFix(unfix=inner)
        assert doc_fix.unfix.children[0].unfix.meta.depth == 1

    def test_enriched_document_immutability(self) -> None:
        """Frozen EnrichedDocument rejects mutation attempts."""
        doc = EnrichedDocument(children=[])
        with pytest.raises(ValidationError):
            doc.children = []

    def test_enriched_document_fix_immutability(self) -> None:
        """Frozen EnrichedDocumentFix rejects mutation attempts."""
        doc_fix = EnrichedDocumentFix(
            unfix=EnrichedDocument(children=[])
        )
        with pytest.raises(ValidationError):
            doc_fix.unfix = EnrichedDocument(children=[])


class TestEnrichDocumentWithPath:
    """Integration tests for ``enrich_document_with_path``."""

    def _make_section(self, text: str) -> TypstSection:
        """Helper to create a simple TypstSection."""
        return TypstSection(
            heading=TypstHeading(text=text),
            body=[TypstParagraph(text=f"Body of {text}")],
            subsections=[],
        )

    def test_single_section_gets_path_zero(self) -> None:
        """Document with 1 section: path [("section", 0)]."""
        doc = TypstDocument(children=[self._make_section("S1")])
        enriched = enrich_document_with_path(doc)

        assert len(enriched.unfix.children) == 1
        assert enriched.unfix.children[0].unfix.meta == PathMeta(
            depth=1, path=[("section", 0)]
        )

    def test_two_sections_get_paths_zero_and_one(self) -> None:
        """Document with 2 sections: paths [("section", 0)], [("section", 1)]."""
        doc = TypstDocument(children=[
            self._make_section("S1"),
            self._make_section("S2"),
        ])
        enriched = enrich_document_with_path(doc)

        assert len(enriched.unfix.children) == 2
        assert enriched.unfix.children[0].unfix.meta.path == [("section", 0)]
        assert enriched.unfix.children[1].unfix.meta.path == [("section", 1)]

    def test_three_sections_get_paths_zero_one_two(self) -> None:
        """Document with 3 sections: paths [("section", 0)], [("section", 1)], [("section", 2)]."""
        doc = TypstDocument(children=[
            self._make_section("S1"),
            self._make_section("S2"),
            self._make_section("S3"),
        ])
        enriched = enrich_document_with_path(doc)

        assert len(enriched.unfix.children) == 3
        assert enriched.unfix.children[0].unfix.meta.path == [("section", 0)]
        assert enriched.unfix.children[1].unfix.meta.path == [("section", 1)]
        assert enriched.unfix.children[2].unfix.meta.path == [("section", 2)]

    def test_empty_document_returns_empty_children(self) -> None:
        """Empty document returns empty children list."""
        doc = TypstDocument(children=[])
        enriched = enrich_document_with_path(doc)

        assert enriched.unfix.children == []

    def test_body_blocks_preserved_in_document(self) -> None:
        """Body blocks within each section are preserved unchanged."""
        para = TypstParagraph(text="Keep me")
        section = TypstSection(
            heading=TypstHeading(text="S1"),
            body=[para],
            subsections=[],
        )
        doc = TypstDocument(children=[section])
        enriched = enrich_document_with_path(doc)

        assert enriched.unfix.children[0].unfix.body[0] == para

    def test_nested_subsections_in_document(self) -> None:
        """Nested subsections within top-level sections get correct paths."""
        child = TypstSection(
            heading=TypstHeading(text="Child"),
            body=[],
            subsections=[],
        )
        parent = TypstSection(
            heading=TypstHeading(text="Parent"),
            body=[],
            subsections=[child],
        )
        doc = TypstDocument(children=[parent])
        enriched = enrich_document_with_path(doc)

        parent_enriched = enriched.unfix.children[0]
        assert parent_enriched.unfix.meta.path == [("section", 0)]

        child_enriched = parent_enriched.unfix.subsections[0]
        assert child_enriched.unfix.meta.path == [
            ("section", 0),
            ("section", 0),
        ]


class TestMapDocumentChildren:
    """Tests for ``map_document_children``."""

    def test_map_document_children_extracts_depth(self) -> None:
        """Algebra extracting depth is applied to each child section."""
        section1 = EnrichedSectionFFix(
            unfix=EnrichedSectionF(
                meta=DepthMeta(depth=1),
                heading=TypstHeading(text="S1"),
                body=[],
                subsections=[],
            )
        )
        section2 = EnrichedSectionFFix(
            unfix=EnrichedSectionF(
                meta=DepthMeta(depth=2),
                heading=TypstHeading(text="S2"),
                body=[],
                subsections=[],
            )
        )
        doc_fix = EnrichedDocumentFix(
            unfix=EnrichedDocument(children=[section1, section2])
        )

        result = map_document_children(doc_fix, lambda sec: sec.meta.depth)
        assert result == [1, 2]

    def test_map_document_children_extracts_heading_text(self) -> None:
        """Algebra extracting heading text is applied to each child section."""
        section1 = EnrichedSectionFFix(
            unfix=EnrichedSectionF(
                meta=DepthMeta(depth=1),
                heading=TypstHeading(text="Alpha"),
                body=[],
                subsections=[],
            )
        )
        section2 = EnrichedSectionFFix(
            unfix=EnrichedSectionF(
                meta=DepthMeta(depth=1),
                heading=TypstHeading(text="Beta"),
                body=[],
                subsections=[],
            )
        )
        doc_fix = EnrichedDocumentFix(
            unfix=EnrichedDocument(children=[section1, section2])
        )

        result = map_document_children(doc_fix, lambda sec: sec.heading.text)
        assert result == ["Alpha", "Beta"]

    def test_map_document_children_with_nested_subsections(self) -> None:
        """Algebra folds over nested subsection trees."""
        grandchild = EnrichedSectionFFix(
            unfix=EnrichedSectionF(
                meta=DepthMeta(depth=3),
                heading=TypstHeading(text="GC"),
                body=[],
                subsections=[],
            )
        )
        child = EnrichedSectionFFix(
            unfix=EnrichedSectionF(
                meta=DepthMeta(depth=2),
                heading=TypstHeading(text="C"),
                body=[],
                subsections=[grandchild],
            )
        )
        parent = EnrichedSectionFFix(
            unfix=EnrichedSectionF(
                meta=DepthMeta(depth=1),
                heading=TypstHeading(text="P"),
                body=[],
                subsections=[child],
            )
        )
        doc_fix = EnrichedDocumentFix(
            unfix=EnrichedDocument(children=[parent])
        )

        def count_sections(sec: EnrichedSectionF[DepthMeta, list, int]) -> int:
            return 1 + sum(sec.subsections)

        result = map_document_children(doc_fix, count_sections)
        assert result == [3]

    def test_map_document_children_empty_document(self) -> None:
        """Empty document returns empty list."""
        doc_fix = EnrichedDocumentFix(
            unfix=EnrichedDocument(children=[])
        )

        result = map_document_children(doc_fix, lambda sec: sec.meta.depth)
        assert result == []
