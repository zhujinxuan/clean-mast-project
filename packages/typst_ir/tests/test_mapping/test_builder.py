"""Tests for MappingBuilder - orchestrates DOCX to Typst IR mapping creation.

TDD RED phase: MappingBuilder is not yet implemented, all tests marked as xfail.

The MappingBuilder class is responsible for orchestrating the complete mapping
workflow between DOCX source documents and Typst IR:
1. Initialize NodeRegistry with the TypstDocument
2. Use MappingVisitor to traverse IR and create mappings
3. Extract paragraphs from DOCX file using extract_paragraphs()
4. Match Typst IR nodes to DOCX paragraphs
5. Return complete DocxTypstMapping object
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

from typst_ir import (
    TypstBulletList,
    TypstDocument,
    TypstHeading,
    TypstParagraph,
    TypstSection,
    TypstTable,
)
from typst_ir.mapping.registry import NodeRegistry
from typst_ir.mapping.types import DocxTypstMapping

if TYPE_CHECKING:
    pass


class TestMappingBuilderInitialization:
    """Test MappingBuilder initialization and basic attributes."""

    def test_builder_initializes_with_registry(self) -> None:
        """Builder should accept NodeRegistry in constructor."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        assert builder.registry is registry

    def test_builder_initializes_empty_mappings(self) -> None:
        """Builder should start with empty mappings dict."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        assert builder.mappings == {}
        assert isinstance(builder.mappings, dict)


class TestBuildSimpleDocument:
    """Test building mapping from simple document structures."""

    def test_build_returns_docx_typst_mapping(self, tmp_path: Path) -> None:
        """build() should return a DocxTypstMapping object."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Content"),
                    body=[TypstParagraph(text="Hello world")],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")  # Minimal valid ZIP header for DOCX

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        assert isinstance(result, DocxTypstMapping)

    def test_build_simple_document_includes_all_nodes(self, tmp_path: Path) -> None:
        """Mapping should include entries for all nodes in the document."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[
                        TypstParagraph(text="First paragraph"),
                        TypstParagraph(text="Second paragraph"),
                    ],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        # Should have: document, section, heading, 2 paragraphs = 5 entries
        assert len(result.entries) == 5

    def test_build_mapping_includes_full_hash(self, tmp_path: Path) -> None:
        """Mapping should include document-wide full_hash."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Content"),
                    body=[TypstParagraph(text="Content")],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        assert result.full_hash is not None
        assert len(result.full_hash) == 64  # SHA-256 hex


class TestBuildNestedSections:
    """Test building mapping from documents with nested sections."""

    def test_build_nested_sections_all_have_mappings(self, tmp_path: Path) -> None:
        """All nested sections should have mapping entries."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        inner_section = TypstSection(
            heading=TypstHeading(text="Inner Section"),
            body=[TypstParagraph(text="Inner content")],
            subsections=[],
        )
        outer_section = TypstSection(
            heading=TypstHeading(text="Outer Section"),
            body=[TypstParagraph(text="Outer content")],
            subsections=[inner_section],
        )
        doc = TypstDocument(children=[outer_section])
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        # Should have: document, outer section, outer heading, inner section,
        # inner heading, 2 paragraphs = 7 entries
        assert len(result.entries) == 7

    def test_build_complex_document_structure(self, tmp_path: Path) -> None:
        """Complex document should have all node types in mapping."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Document Title"),
                    body=[TypstParagraph(text="Introduction paragraph")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Section 1"),
                    body=[
                        TypstParagraph(text="Section 1 content"),
                        TypstBulletList(
                            items=[
                                [TypstParagraph(text="Bullet item 1")],
                                [TypstParagraph(text="Bullet item 2")],
                            ]
                        ),
                        TypstTable(
                            headers=["A", "B"],
                            data=[["1", "2"], ["3", "4"]],
                        ),
                    ],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Section 2"),
                    body=[TypstParagraph(text="Section 2 content")],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        paths = list(result.entries.keys())

        # Verify all node types are represented in path_index
        assert len(result.path_index) > 0

        # Check specific node types are present
        assert any("Heading" in p for p in paths)
        assert any("Paragraph" in p for p in paths)
        assert any("Section" in p for p in paths)
        assert any("BulletList" in p for p in paths)
        assert any("Table" in p for p in paths)


class TestValidateAllNodesHaveMappings:
    """Test that every node in the IR tree gets a mapping entry."""

    def test_all_paragraphs_have_mappings(self, tmp_path: Path) -> None:
        """Every paragraph should have a mapping entry."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Content"),
                    body=[
                        TypstParagraph(text="Paragraph 1"),
                        TypstParagraph(text="Paragraph 2"),
                        TypstParagraph(text="Paragraph 3"),
                    ],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        paragraph_mappings = [k for k in result.entries.keys() if "Paragraph" in k]
        assert len(paragraph_mappings) == 3

    def test_all_headings_have_mappings(self, tmp_path: Path) -> None:
        """Every heading should have a mapping entry."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="H1"),
                    body=[TypstHeading(text="H2")],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        heading_mappings = [k for k in result.entries.keys() if "Heading" in k]
        assert len(heading_mappings) == 2

    def test_nested_list_items_have_mappings(self, tmp_path: Path) -> None:
        """All items in nested lists should have mappings."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Content"),
                    body=[
                        TypstBulletList(
                            items=[
                                [TypstParagraph(text="Item 1a"), TypstParagraph(text="Item 1b")],
                                [TypstParagraph(text="Item 2")],
                            ]
                        ),
                    ],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        # Should have: document, section, heading, bullet list, 3 paragraphs = 6 entries
        paragraph_mappings = [k for k in result.entries.keys() if "Paragraph" in k]
        assert len(paragraph_mappings) == 3


class TestValidateParagraphIndices:
    """Test that paragraph indices in mappings are correct."""

    def test_paragraph_indices_are_non_negative(self, tmp_path: Path) -> None:
        """All source indices should be non-negative integers."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Content"),
                    body=[
                        TypstParagraph(text="First"),
                        TypstParagraph(text="Second"),
                        TypstParagraph(text="Third"),
                    ],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        for entry in result.entries.values():
            assert entry.source_start >= 0
            assert entry.source_end >= 0

    def test_paragraph_indices_are_ordered(self, tmp_path: Path) -> None:
        """Paragraph indices should reflect document order."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="H1"),
                    body=[
                        TypstParagraph(text="Para 1"),
                        TypstParagraph(text="Para 2"),
                    ],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        # Entries should be sorted by source_start
        sorted_entries = sorted(
            result.entries.values(), key=lambda e: e.source_start
        )
        for i in range(len(sorted_entries) - 1):
            assert sorted_entries[i].source_start <= sorted_entries[i + 1].source_start


class TestValidateRangesConsistent:
    """Test that all source ranges are consistent (from <= to)."""

    def test_all_ranges_have_from_leq_to(self, tmp_path: Path) -> None:
        """All mapping entries should have source_start <= source_end."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[TypstParagraph(text="Content")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Section"),
                    body=[
                        TypstBulletList(
                            items=[
                                [TypstParagraph(text="Item 1")],
                                [TypstParagraph(text="Item 2")],
                            ]
                        ),
                    ],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        for entry in result.entries.values():
            assert entry.source_start <= entry.source_end, (
                f"Range inconsistency: {entry.node_id.canonical} has "
                f"source_start={entry.source_start} > source_end={entry.source_end}"
            )

    def test_ranges_within_parent_constraints(self, tmp_path: Path) -> None:
        """Child ranges should be within parent ranges."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        section = TypstSection(
            heading=TypstHeading(text="Section"),
            body=[
                TypstParagraph(text="Para 1"),
                TypstParagraph(text="Para 2"),
            ],
            subsections=[],
        )
        doc = TypstDocument(children=[section])
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        # Find section entry
        section_entry = None
        for entry in result.entries.values():
            if "Section" in entry.node_id.path and not entry.node_id.path.endswith("[TypstHeading]"):
                section_entry = entry
                break

        assert section_entry is not None

        # All paragraphs should be within section range
        for entry in result.entries.values():
            if "Paragraph" in entry.node_id.path:
                assert entry.source_start >= section_entry.source_start
                assert entry.source_end <= section_entry.source_end


class TestEmptyDocument:
    """Test behavior with empty documents."""

    def test_empty_document_produces_empty_mapping(self, tmp_path: Path) -> None:
        """Empty document should produce empty entries dict."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(children=[])
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        assert result.entries == {}

    def test_empty_document_has_full_hash(self, tmp_path: Path) -> None:
        """Empty document should still have full_hash."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(children=[])
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        # Compute expected hash
        expected_hash = hashlib.sha256(
            doc.model_dump_json().encode("utf-8")
        ).hexdigest()

        assert result.full_hash == expected_hash


class TestMappingFullHash:
    """Test that mapping includes correct full_hash."""

    def test_full_hash_matches_registry(self, tmp_path: Path) -> None:
        """Mapping full_hash should match NodeRegistry.full_hash."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[TypstParagraph(text="Content")],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        # After build, registry should be initialized and have full_hash
        assert result.full_hash == registry.full_hash

    def test_full_hash_consistent_for_same_document(self, tmp_path: Path) -> None:
        """Same document should produce same full_hash across multiple builds."""
        from typst_ir.mapping.builder import MappingBuilder

        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[TypstParagraph(text="Content")],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        registry1 = NodeRegistry()
        builder1 = MappingBuilder(registry1)
        result1 = builder1.build(doc, str(docx_path))

        registry2 = NodeRegistry()
        builder2 = MappingBuilder(registry2)
        result2 = builder2.build(doc, str(docx_path))

        assert result1.full_hash == result2.full_hash


class TestBuilderOrchestration:
    """Test that MappingBuilder correctly orchestrates components."""

    def test_builder_uses_registry_for_ids(self, tmp_path: Path) -> None:
        """Builder should use registry.get_id() to get NodeIDs."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Content"),
                    body=[TypstParagraph(text="Test")],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        # All entries should have valid NodeIDs with full_hash from registry
        for entry in result.entries.values():
            assert entry.node_id.full_hash == result.full_hash

    def test_builder_uses_visitor_for_traversal(self, tmp_path: Path) -> None:
        """Builder should use MappingVisitor to traverse document."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Section"),
                    body=[TypstParagraph(text="Content")],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        # Should have entries for document, section, heading, paragraph
        assert len(result.entries) == 4

    def test_builder_creates_path_index(self, tmp_path: Path) -> None:
        """Builder should create path_index for reverse lookup."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[TypstParagraph(text="Content")],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        # path_index should map paths to canonical node IDs
        assert len(result.path_index) > 0
        for path, canonical_id in result.path_index.items():
            assert isinstance(path, str)
            assert isinstance(canonical_id, str)
            assert canonical_id in result.entries


class TestMappingVersion:
    """Test mapping version field."""

    def test_mapping_has_version(self, tmp_path: Path) -> None:
        """Mapping should have a version field."""
        from typst_ir.mapping.builder import MappingBuilder

        registry = NodeRegistry()
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Content"),
                    body=[TypstParagraph(text="Test")],
                    subsections=[],
                ),
            ]
        )
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"PK")

        builder = MappingBuilder(registry)
        result = builder.build(doc, str(docx_path))

        assert result.version == "1.0.0"
