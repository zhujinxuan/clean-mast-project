"""Tests for path-based section enrichment.

Verifies that ``enrich_with_path`` annotates each section with the correct
``PathMeta`` including depth and hierarchical path tuples.
"""

from __future__ import annotations

from typst_ir import TypstHeading, TypstParagraph, TypstSection
from typst_ir.enriched.docx_types import PathMeta
from typst_ir.enriched.enrich_path import (
    compute_section_index,
    enrich_with_path,
    path_for_section,
)


class TestComputeSectionIndex:
    """Tests for the ``compute_section_index`` helper."""

    def test_compute_section_index_single_section(self) -> None:
        """Single section at index 0 returns '1'."""
        assert compute_section_index([("section", 0)]) == "1"

    def test_compute_section_index_nested_sections(self) -> None:
        """Nested sections return dotted 1-based indices."""
        assert compute_section_index([("section", 0), ("section", 1)]) == "1.2"

    def test_compute_section_index_empty_path(self) -> None:
        """Empty path returns empty string."""
        assert compute_section_index([]) == ""

    def test_compute_section_index_filters_non_section_contexts(self) -> None:
        """Only 'section' contexts contribute to the index."""
        assert compute_section_index([("paragraph", 0), ("section", 2)]) == "3"


class TestPathForSection:
    """Unit tests for the ``path_for_section`` helper."""

    def test_appends_sibling_index(self) -> None:
        parent = PathMeta(depth=1, path=[("section", 0)])
        sec = TypstSection(
            heading=TypstHeading(text="Child"),
            body=[],
            subsections=[],
        )
        result = path_for_section(sec, parent, 2)
        assert result == PathMeta(depth=2, path=[("section", 0), ("section", 2)])


class TestEnrichWithPath:
    """Integration tests for ``enrich_with_path``."""

    def test_single_section_gets_index_zero(self) -> None:
        """First section gets path=[("section", 0)]."""
        root = TypstSection(
            heading=TypstHeading(text="Root"),
            body=[TypstParagraph(text="Hello")],
            subsections=[],
        )
        enriched = enrich_with_path(root)
        assert enriched.unfix.meta == PathMeta(
            depth=1, path=[("section", 0)]
        )
        assert enriched.unfix.heading.text == "Root"
        assert len(enriched.unfix.body) == 1
        assert enriched.unfix.subsections == []

    def test_nested_sections_get_correct_paths(self) -> None:
        """Nested sections get paths like [("section", 0), ("section", 1)]."""
        child_0 = TypstSection(
            heading=TypstHeading(text="Child 0"),
            body=[],
            subsections=[],
        )
        child_1 = TypstSection(
            heading=TypstHeading(text="Child 1"),
            body=[],
            subsections=[],
        )
        root = TypstSection(
            heading=TypstHeading(text="Root"),
            body=[],
            subsections=[child_0, child_1],
        )
        enriched = enrich_with_path(root)

        assert enriched.unfix.meta.path == [("section", 0)]

        sub_0 = enriched.unfix.subsections[0]
        sub_1 = enriched.unfix.subsections[1]

        assert sub_0.unfix.meta == PathMeta(
            depth=2, path=[("section", 0), ("section", 0)]
        )
        assert sub_1.unfix.meta == PathMeta(
            depth=2, path=[("section", 0), ("section", 1)]
        )

    def test_deeply_nested_paths(self) -> None:
        """Test that deep nesting produces correct path chains."""
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
        enriched = enrich_with_path(root)

        assert enriched.unfix.meta.path == [("section", 0)]
        assert enriched.unfix.subsections[0].unfix.meta.path == [
            ("section", 0),
            ("section", 0),
        ]
        assert enriched.unfix.subsections[0].unfix.subsections[0].unfix.meta.path == [
            ("section", 0),
            ("section", 0),
            ("section", 0),
        ]

    def test_body_blocks_preserved_unchanged(self) -> None:
        """Body blocks should pass through unchanged (identity_block behavior)."""
        para = TypstParagraph(text="Keep me")
        root = TypstSection(
            heading=TypstHeading(text="Root"),
            body=[para],
            subsections=[],
        )
        enriched = enrich_with_path(root)
        assert enriched.unfix.body[0] == para
