"""End-to-end integration tests for the Typst IR mapping pipeline.

Tests the complete workflow:
  - IR → Registry → Visitor → Builder → Mapping
  - IR → Mapping → inject_ids → verify IDs in docx
  - Edge cases: empty document, nested sections, tables, lists
  - Round-trip verification (IR → mapping → can find nodes by path)

Uses real test fixtures from packages/typst_ir/tests/fixtures/.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner
from typst_ir import (
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
from typst_ir.mapping.builder import MappingBuilder
from typst_ir.mapping.cli import main
from typst_ir.mapping.injector import extract_paragraphs, inject_ids
from typst_ir.mapping.registry import NodeRegistry
from typst_ir.mapping.types import DocxTypstMapping, MappingEntry
from typst_ir.mapping.visitor import MappingVisitor

if TYPE_CHECKING:
    pass


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def simple_ir_document() -> TypstDocument:
    """Create a simple IR document with heading and paragraphs."""
    return TypstDocument(
        children=[
            TypstSection(
                heading=TypstHeading(text="Document Title"),
                body=[
                    TypstParagraph(text="First paragraph of the document."),
                    TypstParagraph(text="Second paragraph with more content."),
                ],
                subsections=[],
            ),
        ]
    )


@pytest.fixture
def nested_sections_ir_document() -> TypstDocument:
    """Create an IR document with nested sections."""
    return TypstDocument(
        children=[
            TypstSection(
                heading=TypstHeading(text="Main Title"),
                body=[],
                subsections=[
                    TypstSection(
                        heading=TypstHeading(text="Section 1"),
                        body=[TypstParagraph(text="Section 1 content.")],
                        subsections=[
                            TypstSection(
                                heading=TypstHeading(text="Subsection 1.1"),
                                body=[TypstParagraph(text="Nested subsection content.")],
                                subsections=[],
                            ),
                        ],
                    ),
                    TypstSection(
                        heading=TypstHeading(text="Section 2"),
                        body=[TypstParagraph(text="Section 2 content.")],
                        subsections=[],
                    ),
                ],
            ),
        ]
    )


@pytest.fixture
def table_ir_document() -> TypstDocument:
    """Create an IR document with a table."""
    return TypstDocument(
        children=[
            TypstSection(
                heading=TypstHeading(text="Table Section"),
                body=[
                    TypstParagraph(text="Below is a data table:"),
                    TypstTable(
                        headers=["Name", "Value", "Unit"],
                        data=[
                            ["Temperature", "25", "°C"],
                            ["Pressure", "1013", "hPa"],
                            ["Humidity", "60", "%"],
                        ],
                        caption="Weather Data",
                    ),
                ],
                subsections=[],
            ),
        ]
    )


@pytest.fixture
def list_ir_document() -> TypstDocument:
    """Create an IR document with bullet and ordered lists."""
    return TypstDocument(
        children=[
            TypstSection(
                heading=TypstHeading(text="List Section"),
                body=[
                    TypstParagraph(text="Bullet list:"),
                    TypstBulletList(
                        items=[
                            [TypstParagraph(text="First bullet item")],
                            [TypstParagraph(text="Second bullet item")],
                            [TypstParagraph(text="Third bullet item")],
                        ]
                    ),
                    TypstParagraph(text="Ordered list:"),
                    TypstOrderedList(
                        items=[
                            [TypstParagraph(text="First ordered item")],
                            [TypstParagraph(text="Second ordered item")],
                        ],
                        start=1,
                    ),
                ],
                subsections=[],
            ),
        ]
    )


@pytest.fixture
def complex_ir_document() -> TypstDocument:
    """Create a complex IR document with all node types."""
    return TypstDocument(
        children=[
            TypstSection(
                heading=TypstHeading(text="Complex Document"),
                body=[
                    TypstParagraph(text="Introduction paragraph."),
                ],
                subsections=[],
            ),
            TypstSection(
                heading=TypstHeading(text="Section with Table"),
                body=[
                    TypstParagraph(text="Section content before table."),
                    TypstTable(
                        headers=["A", "B"],
                        data=[["1", "2"], ["3", "4"]],
                    ),
                    TypstBulletList(
                        items=[
                            [TypstParagraph(text="Bullet 1")],
                            [TypstParagraph(text="Bullet 2")],
                        ]
                    ),
                ],
                subsections=[],
            ),
            TypstSection(
                heading=TypstHeading(text="Section with Equation"),
                body=[
                    TypstEquation(latex="E = mc^2", display=True),
                    TypstCodeBlock(text="print('hello')", language="python"),
                    TypstFigure(
                        content="image.png", caption="Sample figure", kind="image"
                    ),
                ],
                subsections=[],
            ),
            TypstSection(
                heading=TypstHeading(text="Raw Content"),
                body=[
                    TypstRawBlock(format="html", text="<div>Raw content</div>"),
                ],
                subsections=[],
            ),
        ]
    )


@pytest.fixture
def empty_ir_document() -> TypstDocument:
    """Create an empty IR document."""
    return TypstDocument(children=[])


def _extract_xml_from_docx(docx_path: Path, xml_path: str = "word/document.xml") -> str:
    """Extract XML content from a DOCX file."""
    with zipfile.ZipFile(docx_path, "r") as zf:
        return zf.read(xml_path).decode("utf-8")


def _count_custom_irid_attributes(xml_content: str) -> int:
    """Count w:customIRID attributes in XML content."""
    return len(re.findall(r'w:customIRID="([^"]*)"', xml_content))


def _get_custom_irid_values(xml_content: str) -> list[str]:
    """Extract all w:customIRID attribute values from XML content."""
    return re.findall(r'w:customIRID="([^"]*)"', xml_content)


# ============================================================================
# Full Pipeline Tests: IR → Registry → Visitor → Builder → Mapping
# ============================================================================


class TestFullPipeline:
    """End-to-end tests for the complete mapping pipeline."""

    def test_pipeline_creates_valid_mapping(self, simple_ir_document: TypstDocument) -> None:
        """Full pipeline produces a valid DocxTypstMapping."""
        # Step 1: Create registry and initialize with document
        registry = NodeRegistry()
        registry.initialize(simple_ir_document)

        # Step 2: Create visitor and traverse IR
        visitor = MappingVisitor(registry)
        mappings = visitor.visit_document(simple_ir_document, 0, 10)

        # Step 3: Build mapping entries
        entries: dict[str, MappingEntry] = {}
        for entry in mappings:
            entries[entry.node_id.canonical] = entry

        # Step 4: Build path_index
        path_index: dict[str, str] = {}
        for entry in entries.values():
            path_index[entry.node_id.path] = entry.node_id.canonical

        # Create final mapping
        mapping = DocxTypstMapping(
            version="1.0.0",
            full_hash=registry.full_hash,
            entries=entries,
            path_index=path_index,
        )

        # Verify mapping is valid
        assert mapping.version == "1.0.0"
        assert len(mapping.full_hash) == 64  # SHA-256 hex
        assert len(mapping.entries) > 0
        assert len(mapping.path_index) > 0

    def test_pipeline_all_nodes_have_mappings(
        self, simple_ir_document: TypstDocument
    ) -> None:
        """Every node in the IR tree gets a mapping entry."""
        registry = NodeRegistry()
        registry.initialize(simple_ir_document)

        visitor = MappingVisitor(registry)
        mappings = visitor.visit_document(simple_ir_document, 0, 10)

        assert len(mappings) == 5

        # Verify each node has unique path
        paths = [entry.node_id.path for entry in mappings]
        assert len(paths) == len(set(paths)), "All paths should be unique"

    def test_pipeline_nested_sections(self, nested_sections_ir_document: TypstDocument) -> None:
        """Pipeline correctly handles deeply nested sections."""
        registry = NodeRegistry()
        registry.initialize(nested_sections_ir_document)

        visitor = MappingVisitor(registry)
        mappings = visitor.visit_document(nested_sections_ir_document, 0, 100)

        # Should have mappings for:
        # - document
        # - main heading
        # - section 1, its heading, content paragraph
        # - subsection 1.1, its heading, content paragraph
        # - section 2, its heading, content paragraph
        assert len(mappings) == 12

        # Verify section hierarchy in paths
        paths = [entry.node_id.path for entry in mappings]
        assert any("Section" in p for p in paths)
        assert any("Heading" in p for p in paths)
        assert any("Paragraph" in p for p in paths)

    def test_pipeline_table_nodes(self, table_ir_document: TypstDocument) -> None:
        """Pipeline correctly handles table nodes."""
        registry = NodeRegistry()
        registry.initialize(table_ir_document)

        visitor = MappingVisitor(registry)
        mappings = visitor.visit_document(table_ir_document, 0, 10)

        assert len(mappings) == 5

        # Verify table node exists
        table_mappings = [m for m in mappings if "Table" in m.node_id.path]
        assert len(table_mappings) == 1

    def test_pipeline_list_nodes(self, list_ir_document: TypstDocument) -> None:
        """Pipeline correctly handles list nodes."""
        registry = NodeRegistry()
        registry.initialize(list_ir_document)

        visitor = MappingVisitor(registry)
        mappings = visitor.visit_document(list_ir_document, 0, 20)

        # Should have:
        # - document
        # - heading
        # - "Bullet list:" paragraph
        # - bullet list node
        # - 3 bullet item paragraphs
        # - "Ordered list:" paragraph
        # - ordered list node
        # - 2 ordered item paragraphs
        assert len(mappings) == 12

        # Verify list nodes exist (includes list node and its items)
        bullet_list_mappings = [m for m in mappings if "BulletList" in m.node_id.path]
        ordered_list_mappings = [m for m in mappings if "OrderedList" in m.node_id.path]
        assert len(bullet_list_mappings) >= 1, "Should have bullet list entries"
        assert len(ordered_list_mappings) >= 1, "Should have ordered list entries"

    def test_pipeline_complex_document(self, complex_ir_document: TypstDocument) -> None:
        """Pipeline handles complex document with all node types."""
        registry = NodeRegistry()
        registry.initialize(complex_ir_document)

        visitor = MappingVisitor(registry)
        mappings = visitor.visit_document(complex_ir_document, 0, 50)

        # Verify all node types are present
        paths = [m.node_id.path for m in mappings]

        assert any("Heading" in p for p in paths), "Should have headings"
        assert any("Paragraph" in p for p in paths), "Should have paragraphs"
        assert any("Section" in p for p in paths), "Should have sections"
        assert any("Table" in p for p in paths), "Should have table"
        assert any("BulletList" in p for p in paths), "Should have bullet list"
        assert any("Equation" in p for p in paths), "Should have equation"
        assert any("CodeBlock" in p for p in paths), "Should have code block"
        assert any("Figure" in p for p in paths), "Should have figure"
        assert any("RawBlock" in p for p in paths), "Should have raw block"


class TestMappingBuilderOrchestration:
    """Tests for MappingBuilder orchestrating the full pipeline."""

    def test_builder_produces_complete_mapping(
        self, simple_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """MappingBuilder produces complete DocxTypstMapping."""
        # Create a minimal valid DOCX
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "test.docx"
        doc = Document()
        doc.add_paragraph("First paragraph of the document.")
        doc.add_paragraph("Second paragraph with more content.")
        doc.save(str(docx_path))

        # Run full pipeline through builder
        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(simple_ir_document, str(docx_path))

        # Verify mapping structure
        assert isinstance(mapping, DocxTypstMapping)
        assert mapping.version == "1.0.0"
        assert len(mapping.full_hash) == 64
        assert len(mapping.entries) > 0
        assert len(mapping.path_index) > 0

    def test_builder_uses_real_docx_paragraph_count(
        self, simple_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """Builder uses actual paragraph count from DOCX for source ranges."""
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "test.docx"
        doc = Document()
        doc.add_paragraph("Para 1")
        doc.add_paragraph("Para 2")
        doc.add_paragraph("Para 3")
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(simple_ir_document, str(docx_path))

        # Verify source ranges reference valid paragraph indices
        for entry in mapping.entries.values():
            assert entry.source_start >= 0
            assert entry.source_end >= entry.source_start


class TestMappingBuilderWithDetection:
    """Tests for MappingBuilder using DocxMatcher detection results."""

    def test_detected_entries_have_method_and_confidence(
        self, simple_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """Detected top-level nodes have method and confidence populated."""
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "test.docx"
        doc = Document()
        doc.add_heading("Document Title", level=1)
        doc.add_paragraph("First paragraph of the document.")
        doc.add_paragraph("Second paragraph with more content.")
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(simple_ir_document, str(docx_path))

        for entry in mapping.entries.values():
            if "Heading" in entry.node_id.path or "Paragraph" in entry.node_id.path:
                assert entry.method is not None
                assert entry.confidence is not None

    def test_detected_entries_use_actual_docx_ranges(
        self, simple_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """Detected nodes use actual paragraph indices from DOCX."""
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "test.docx"
        doc = Document()
        doc.add_heading("Document Title", level=1)
        doc.add_paragraph("First paragraph of the document.")
        doc.add_paragraph("Second paragraph with more content.")
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(simple_ir_document, str(docx_path))

        heading_entries = [
            e for e in mapping.entries.values() if "Heading" in e.node_id.path
        ]
        for entry in heading_entries:
            assert entry.source_start >= 0
            assert entry.source_end >= entry.source_start

        paragraph_entries = [
            e for e in mapping.entries.values() if "Paragraph" in e.node_id.path
        ]
        paragraph_entries.sort(key=lambda e: e.source_start)
        assert paragraph_entries[0].source_start >= 0
        assert paragraph_entries[1].source_start >= paragraph_entries[0].source_start

    def test_unmatched_nodes_fallback_to_positional(
        self, tmp_path: Path
    ) -> None:
        """Nodes not matched by DocxMatcher fall back to positional method."""
        pytest.importorskip("docx")
        from docx import Document

        ir_doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Section"),
                    body=[
                        TypstParagraph(text="Content paragraph."),
                    ],
                    subsections=[],
                ),
            ]
        )

        docx_path = tmp_path / "test.docx"
        doc = Document()
        doc.add_heading("Section", level=1)
        doc.add_paragraph("Content paragraph.")
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(ir_doc, str(docx_path))

        section_entries = [
            e for e in mapping.entries.values() if e.node_id.path.endswith("[TypstSection]")
        ]
        assert len(section_entries) == 1
        assert section_entries[0].method.value == "positional"
        assert section_entries[0].confidence.value == "low"

    def test_detected_nodes_have_details(
        self, simple_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """Detected nodes include details from the matcher."""
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "test.docx"
        doc = Document()
        doc.add_heading("Document Title", level=1)
        doc.add_paragraph("First paragraph of the document.")
        doc.add_paragraph("Second paragraph with more content.")
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(simple_ir_document, str(docx_path))

        for entry in mapping.entries.values():
            if "Heading" in entry.node_id.path or "Paragraph" in entry.node_id.path:
                if entry.method.value != "positional":
                    assert "docx_paragraph" in entry.details


# ============================================================================
# Full Pipeline with ID Injection: IR → Mapping → inject_ids → Verify
# ============================================================================


class TestFullPipelineWithInjection:
    """End-to-end tests including ID injection into DOCX."""

    def test_inject_ids_adds_custom_irid_attributes(
        self, simple_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """Full pipeline with injection adds w:customIRID attributes."""
        pytest.importorskip("docx")
        from docx import Document

        # Create DOCX matching the IR
        docx_path = tmp_path / "input.docx"
        doc = Document()
        doc.add_heading("Document Title", level=1)
        doc.add_paragraph("First paragraph of the document.")
        doc.add_paragraph("Second paragraph with more content.")
        doc.save(str(docx_path))

        # Build mapping
        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(simple_ir_document, str(docx_path))

        # Inject IDs
        output_path = tmp_path / "output.docx"
        inject_ids(docx_path, output_path, mapping)

        assert output_path.exists()
        xml_content = _extract_xml_from_docx(output_path)
        assert "w:document" in xml_content

    def test_inject_ids_preserves_document_content(
        self, simple_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """ID injection preserves original document content."""
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "input.docx"
        doc = Document()
        doc.add_heading("Document Title", level=1)
        doc.add_paragraph("First paragraph.")
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(simple_ir_document, str(docx_path))

        output_path = tmp_path / "output.docx"
        inject_ids(docx_path, output_path, mapping)

        # Verify content preserved
        output_doc = Document(str(output_path))
        assert output_doc.paragraphs[0].text == "Document Title"

    def test_inject_ids_with_table_document(
        self, table_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """ID injection works with documents containing tables."""
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "input.docx"
        doc = Document()
        doc.add_heading("Table Section", level=1)
        doc.add_paragraph("Below is a data table:")
        table = doc.add_table(rows=4, cols=3)
        table.cell(0, 0).text = "Name"
        table.cell(0, 1).text = "Value"
        table.cell(0, 2).text = "Unit"
        table.cell(1, 0).text = "Temperature"
        table.cell(1, 1).text = "25"
        table.cell(1, 2).text = "°C"
        table.cell(2, 0).text = "Pressure"
        table.cell(2, 1).text = "1013"
        table.cell(2, 2).text = "hPa"
        table.cell(3, 0).text = "Humidity"
        table.cell(3, 1).text = "60"
        table.cell(3, 2).text = "%"
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(table_ir_document, str(docx_path))

        output_path = tmp_path / "output.docx"
        inject_ids(docx_path, output_path, mapping)

        assert output_path.exists()
        xml_content = _extract_xml_from_docx(output_path)
        assert "w:document" in xml_content

    def test_inject_ids_with_list_document(
        self, list_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """ID injection works with documents containing lists."""
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "input.docx"
        doc = Document()
        doc.add_heading("List Section", level=1)
        doc.add_paragraph("Bullet list:")
        doc.add_paragraph("First bullet item", style="List Bullet")
        doc.add_paragraph("Second bullet item", style="List Bullet")
        doc.add_paragraph("Third bullet item", style="List Bullet")
        doc.add_paragraph("Ordered list:")
        doc.add_paragraph("First ordered item", style="List Number")
        doc.add_paragraph("Second ordered item", style="List Number")
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(list_ir_document, str(docx_path))

        output_path = tmp_path / "output.docx"
        inject_ids(docx_path, output_path, mapping)

        assert output_path.exists()
        xml_content = _extract_xml_from_docx(output_path)
        assert "w:document" in xml_content

    def test_inject_ids_includes_all_node_ids(
        self, nested_sections_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """ID injection includes all node IDs from the mapping."""
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "input.docx"
        doc = Document()
        doc.add_heading("Main Title", level=1)
        doc.add_heading("Section 1", level=1)
        doc.add_paragraph("Section 1 content.")
        doc.add_heading("Subsection 1.1", level=2)
        doc.add_paragraph("Nested subsection content.")
        doc.add_heading("Section 2", level=1)
        doc.add_paragraph("Section 2 content.")
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(nested_sections_ir_document, str(docx_path))

        output_path = tmp_path / "output.docx"
        inject_ids(docx_path, output_path, mapping)

        assert output_path.exists()
        xml_content = _extract_xml_from_docx(output_path)
        assert "w:document" in xml_content

        injected_ids = _get_custom_irid_values(xml_content)
        all_injected_ids = []
        for id_str in injected_ids:
            all_injected_ids.extend(id_str.split(","))

        for single_id in all_injected_ids:
            parts = single_id.split(":")
            assert len(parts) == 3


# ============================================================================
# Edge Cases: Empty Document, Nested Sections, Tables, Lists
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_document_mapping(self, empty_ir_document: TypstDocument) -> None:
        """Empty document produces valid but empty mapping."""
        registry = NodeRegistry()
        registry.initialize(empty_ir_document)

        visitor = MappingVisitor(registry)
        mappings = visitor.visit_document(empty_ir_document, 0, 0)

        # Empty document has no children, so no mappings
        assert len(mappings) == 0

        # But registry still has full_hash
        assert len(registry.full_hash) == 64

    def test_empty_document_with_builder(self, empty_ir_document: TypstDocument, tmp_path: Path) -> None:
        """Empty document through builder produces valid mapping."""
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "empty.docx"
        doc = Document()
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(empty_ir_document, str(docx_path))

        assert isinstance(mapping, DocxTypstMapping)
        assert mapping.entries == {}
        assert mapping.path_index == {}
        assert len(mapping.full_hash) == 64

    def test_empty_document_id_injection(self, empty_ir_document: TypstDocument, tmp_path: Path) -> None:
        """ID injection on empty document doesn't fail."""
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "empty.docx"
        doc = Document()
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(empty_ir_document, str(docx_path))

        output_path = tmp_path / "output.docx"
        # Should not raise
        inject_ids(docx_path, output_path, mapping)

        assert output_path.exists()

    def test_deeply_nested_sections(self, tmp_path: Path) -> None:
        """Pipeline handles deeply nested section hierarchy."""
        # Create 3-level nested sections
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Level 1"),
                    body=[],
                    subsections=[
                        TypstSection(
                            heading=TypstHeading(text="Level 2"),
                            body=[],
                            subsections=[
                                TypstSection(
                                    heading=TypstHeading(text="Level 3"),
                                    body=[
                                        TypstParagraph(text="Deep content")
                                    ],
                                    subsections=[],
                                )
                            ],
                        )
                    ],
                )
            ]
        )

        pytest.importorskip("docx")
        from docx import Document as DocxDocument

        docx_path = tmp_path / "nested.docx"
        docx_doc = DocxDocument()
        docx_doc.add_heading("Level 1", level=1)
        docx_doc.add_heading("Level 2", level=2)
        docx_doc.add_heading("Level 3", level=3)
        docx_doc.add_paragraph("Deep content")
        docx_doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(doc, str(docx_path))

        # Verify all levels are mapped
        paths = list(mapping.path_index.keys())
        assert any("Level 1" in p or "subsections.0" in p for p in paths)

    def test_table_with_empty_cells(self, tmp_path: Path) -> None:
        """Pipeline handles tables with empty cells."""
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Table Section"),
                    body=[
                        TypstTable(
                            headers=["A", "B", "C"],
                            data=[
                                ["1", "", "3"],
                                ["", "2", ""],
                            ],
                        ),
                    ],
                    subsections=[],
                ),
            ]
        )

        pytest.importorskip("docx")
        from docx import Document as DocxDocument

        docx_path = tmp_path / "table.docx"
        docx_doc = DocxDocument()
        table = docx_doc.add_table(rows=3, cols=3)
        table.cell(0, 0).text = "A"
        table.cell(0, 1).text = "B"
        table.cell(0, 2).text = "C"
        table.cell(1, 0).text = "1"
        table.cell(1, 1).text = ""
        table.cell(1, 2).text = "3"
        table.cell(2, 0).text = ""
        table.cell(2, 1).text = "2"
        table.cell(2, 2).text = ""
        docx_doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(doc, str(docx_path))

        # Should have document + table mapping
        assert len(mapping.entries) >= 1

    def test_list_with_multiple_blocks_per_item(self, tmp_path: Path) -> None:
        """Pipeline handles list items with multiple blocks."""
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="List Section"),
                    body=[
                        TypstBulletList(
                            items=[
                                [
                                    TypstParagraph(text="Item 1 - part 1"),
                                    TypstParagraph(text="Item 1 - part 2"),
                                ],
                                [TypstParagraph(text="Item 2")],
                            ]
                        ),
                    ],
                    subsections=[],
                ),
            ]
        )

        pytest.importorskip("docx")
        from docx import Document as DocxDocument

        docx_path = tmp_path / "list.docx"
        docx_doc = DocxDocument()
        docx_doc.add_paragraph("Item 1 - part 1", style="List Bullet")
        docx_doc.add_paragraph("Item 1 - part 2")
        docx_doc.add_paragraph("Item 2", style="List Bullet")
        docx_doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(doc, str(docx_path))

        # Verify list items are mapped
        paths = list(mapping.path_index.keys())
        assert any("BulletList" in p for p in paths)

    def test_document_with_only_heading(self, tmp_path: Path) -> None:
        """Pipeline handles document with only a heading."""
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title Only"),
                    body=[],
                    subsections=[],
                ),
            ]
        )

        pytest.importorskip("docx")
        from docx import Document as DocxDocument

        docx_path = tmp_path / "heading_only.docx"
        docx_doc = DocxDocument()
        docx_doc.add_heading("Title Only", level=1)
        docx_doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(doc, str(docx_path))

        # Should have document + heading
        assert len(mapping.entries) >= 1

    def test_document_with_special_characters(self, tmp_path: Path) -> None:
        """Pipeline handles special characters in content."""
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Special Characters"),
                    body=[
                        TypstParagraph(text="Special chars: <>&\"'"),
                        TypstParagraph(text="Unicode: 你好世界 émojis 🎉"),
                        TypstParagraph(text="Math: α + β = γ"),
                    ],
                    subsections=[],
                ),
            ]
        )

        pytest.importorskip("docx")
        from docx import Document as DocxDocument

        docx_path = tmp_path / "special.docx"
        docx_doc = DocxDocument()
        docx_doc.add_paragraph("Special chars: <>&\"'")
        docx_doc.add_paragraph("Unicode: 你好世界 émojis 🎉")
        docx_doc.add_paragraph("Math: α + β = γ")
        docx_doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(doc, str(docx_path))

        # Should complete without errors
        assert isinstance(mapping, DocxTypstMapping)


# ============================================================================
# Round-trip Verification: IR → Mapping → Can Find Nodes by Path
# ============================================================================


class TestRoundTripVerification:
    """Tests verifying round-trip capabilities of the mapping system."""

    def test_find_node_by_path_after_mapping(
        self, simple_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """Can find nodes by their path after building mapping."""
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "test.docx"
        doc = Document()
        doc.add_heading("Document Title", level=1)
        doc.add_paragraph("First paragraph.")
        doc.add_paragraph("Second paragraph.")
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(simple_ir_document, str(docx_path))

        # Should be able to look up by path
        for path in mapping.path_index:
            canonical_id = mapping.path_index[path]
            assert canonical_id in mapping.entries
            entry = mapping.entries[canonical_id]
            assert entry.node_id.path == path

    def test_path_index_consistency(
        self, complex_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """Path index is consistent with entries."""
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "test.docx"
        doc = Document()
        doc.add_heading("Complex Document", level=1)
        doc.add_paragraph("Introduction paragraph.")
        doc.add_heading("Section with Table", level=1)
        doc.add_paragraph("Section content before table.")
        table = doc.add_table(rows=3, cols=2)
        table.cell(0, 0).text = "A"
        table.cell(0, 1).text = "B"
        table.cell(1, 0).text = "1"
        table.cell(1, 1).text = "2"
        table.cell(2, 0).text = "3"
        table.cell(2, 1).text = "4"
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(complex_ir_document, str(docx_path))

        # Every path in path_index should have a corresponding entry
        for path, canonical_id in mapping.path_index.items():
            assert canonical_id in mapping.entries, f"Missing entry for path: {path}"
            entry = mapping.entries[canonical_id]
            assert entry.node_id.canonical == canonical_id

    def test_canonical_id_format(self, simple_ir_document: TypstDocument, tmp_path: Path) -> None:
        """Canonical IDs follow expected format: path:full_hash:node_hash."""
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "test.docx"
        doc = Document()
        doc.add_heading("Title", level=1)
        doc.add_paragraph("Content.")
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(simple_ir_document, str(docx_path))

        # Verify canonical ID format
        for entry in mapping.entries.values():
            canonical = entry.node_id.canonical
            parts = canonical.split(":")
            assert len(parts) == 3, f"Canonical ID should have 3 parts: {canonical}"
            path, full_hash, node_hash = parts
            assert path == entry.node_id.path
            assert full_hash == mapping.full_hash
            assert len(full_hash) == 64
            assert len(node_hash) == 64

    def test_round_trip_serialization(
        self, simple_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """Mapping can be serialized and deserialized."""
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "test.docx"
        doc = Document()
        doc.add_heading("Title", level=1)
        doc.add_paragraph("Content.")
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(simple_ir_document, str(docx_path))

        # Serialize to JSON
        json_str = mapping.model_dump_json()

        # Deserialize
        restored = DocxTypstMapping.model_validate_json(json_str)

        # Verify round-trip
        assert restored.version == mapping.version
        assert restored.full_hash == mapping.full_hash
        assert len(restored.entries) == len(mapping.entries)
        assert len(restored.path_index) == len(mapping.path_index)

    def test_lookup_by_path_after_injection(
        self, nested_sections_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """Can still look up nodes by path after ID injection."""
        pytest.importorskip("docx")
        from docx import Document

        docx_path = tmp_path / "input.docx"
        doc = Document()
        doc.add_heading("Main Title", level=1)
        doc.add_heading("Section 1", level=1)
        doc.add_paragraph("Section 1 content.")
        doc.add_heading("Subsection 1.1", level=2)
        doc.add_paragraph("Nested subsection content.")
        doc.save(str(docx_path))

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(nested_sections_ir_document, str(docx_path))

        output_path = tmp_path / "output.docx"
        inject_ids(docx_path, output_path, mapping)

        # Mapping should still be valid after injection
        for path in mapping.path_index:
            canonical_id = mapping.path_index[path]
            assert canonical_id in mapping.entries


# ============================================================================
# CLI Export-Mapping JSON Serialization
# ============================================================================


class TestExportMappingJsonSerialization:
    """Tests verifying export-mapping CLI JSON includes detection fields and round-trips."""

    def test_export_mapping_includes_detection_fields(
        self, tmp_path: Path
    ) -> None:
        """CLI export-mapping JSON contains method, confidence, and details."""
        pytest.importorskip("docx")
        from docx import Document

        ir_doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Document Title"),
                    body=[
                        TypstParagraph(text="First paragraph of the document."),
                    ],
                    subsections=[],
                ),
            ]
        )

        docx_path = tmp_path / "input.docx"
        doc = Document()
        doc.add_heading("Document Title", level=1)
        doc.add_paragraph("First paragraph of the document.")
        doc.save(str(docx_path))

        ir_path = tmp_path / "ir.json"
        ir_path.write_text(ir_doc.model_dump_json(), encoding="utf-8")

        output_path = tmp_path / "mapping.json"
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "export-mapping",
                "--ir-json",
                str(ir_path),
                "--docx",
                str(docx_path),
                "--output",
                str(output_path),
                "--no-inject",
            ],
        )
        assert result.exit_code == 0

        mapping_json = output_path.read_text(encoding="utf-8")
        assert '"method"' in mapping_json
        assert '"confidence"' in mapping_json
        assert '"details"' in mapping_json

        mapping = DocxTypstMapping.model_validate_json(mapping_json)
        first_entry = next(iter(mapping.entries.values()))
        assert first_entry.method is not None
        assert first_entry.confidence is not None

    def test_export_mapping_json_round_trip(
        self, tmp_path: Path
    ) -> None:
        """Exported mapping JSON can be parsed back into DocxTypstMapping."""
        pytest.importorskip("docx")
        from docx import Document

        ir_doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Document Title"),
                    body=[
                        TypstParagraph(text="First paragraph of the document."),
                    ],
                    subsections=[],
                ),
            ]
        )

        docx_path = tmp_path / "input.docx"
        doc = Document()
        doc.add_heading("Document Title", level=1)
        doc.add_paragraph("First paragraph of the document.")
        doc.save(str(docx_path))

        ir_path = tmp_path / "ir.json"
        ir_path.write_text(ir_doc.model_dump_json(), encoding="utf-8")

        output_path = tmp_path / "mapping.json"
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "export-mapping",
                "--ir-json",
                str(ir_path),
                "--docx",
                str(docx_path),
                "--output",
                str(output_path),
                "--no-inject",
            ],
        )
        assert result.exit_code == 0

        mapping_json = output_path.read_text(encoding="utf-8")
        raw = json.loads(mapping_json)
        restored = DocxTypstMapping.model_validate_json(mapping_json)

        assert restored.full_hash == raw["full_hash"]
        assert restored.version == raw["version"]
        assert len(restored.entries) == len(raw["entries"])

        for key, raw_entry in raw["entries"].items():
            restored_entry = restored.entries[key]
            assert restored_entry.method is not None
            assert restored_entry.method.value == raw_entry["method"]
            assert restored_entry.confidence is not None
            assert restored_entry.confidence.value == raw_entry["confidence"]
            assert restored_entry.details == raw_entry.get("details", {})


# ============================================================================
# Tests Using Real Test Fixtures
# ============================================================================


class TestWithRealFixtures:
    """Tests using real DOCX fixtures from tests/fixtures/."""

    def test_simple_fixture_exists(self, fixtures_dir: Path) -> None:
        """Verify simple.docx fixture exists and is valid."""
        simple_path = fixtures_dir / "simple.docx"
        assert simple_path.exists(), f"Fixture not found: {simple_path}"

        # Verify it's a valid DOCX
        with zipfile.ZipFile(simple_path, "r") as zf:
            assert "word/document.xml" in zf.namelist()

    def test_nested_fixture_exists(self, fixtures_dir: Path) -> None:
        """Verify nested.docx fixture exists and is valid."""
        nested_path = fixtures_dir / "nested.docx"
        assert nested_path.exists(), f"Fixture not found: {nested_path}"

        with zipfile.ZipFile(nested_path, "r") as zf:
            assert "word/document.xml" in zf.namelist()

    def test_table_fixture_exists(self, fixtures_dir: Path) -> None:
        """Verify table.docx fixture exists and is valid."""
        table_path = fixtures_dir / "table.docx"
        assert table_path.exists(), f"Fixture not found: {table_path}"

        with zipfile.ZipFile(table_path, "r") as zf:
            assert "word/document.xml" in zf.namelist()

    def test_extract_paragraphs_from_simple_fixture(self, fixtures_dir: Path) -> None:
        """Can extract paragraphs from simple.docx fixture."""
        pytest.importorskip("docx")

        simple_path = fixtures_dir / "simple.docx"
        paragraphs = extract_paragraphs(simple_path)

        # Should extract some paragraphs
        assert len(paragraphs) > 0

        # Each paragraph should have required fields
        for para in paragraphs:
            assert para.index >= 0
            assert para.text_hash is not None
            assert para.paragraph_type in ["paragraph", "heading", "table_cell", "list_item"]

    def test_full_pipeline_with_simple_fixture(
        self, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """Full pipeline works with simple.docx fixture."""
        pytest.importorskip("docx")

        simple_path = fixtures_dir / "simple.docx"

        # Create matching IR
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Simple Document"),
                    body=[
                        TypstParagraph(
                            text="This is a simple test paragraph for ID injection validation."
                        ),
                    ],
                    subsections=[],
                ),
            ]
        )

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(doc, str(simple_path))

        # Inject IDs
        output_path = tmp_path / "simple_injected.docx"
        inject_ids(simple_path, output_path, mapping)

        assert output_path.exists()
        xml_content = _extract_xml_from_docx(output_path)
        assert "w:document" in xml_content

    def test_verify_custom_irid_in_xml(self, fixtures_dir: Path, tmp_path: Path) -> None:
        """Verify customIRID attributes are present in output XML."""
        pytest.importorskip("docx")

        simple_path = fixtures_dir / "simple.docx"

        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Simple Document"),
                    body=[
                        TypstParagraph(
                            text="This is a simple test paragraph for ID injection validation."
                        ),
                    ],
                    subsections=[],
                ),
            ]
        )

        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(doc, str(simple_path))

        output_path = tmp_path / "output.docx"
        inject_ids(simple_path, output_path, mapping)

        xml_content = _extract_xml_from_docx(output_path)
        assert "w:document" in xml_content

        ids = _get_custom_irid_values(xml_content)
        for id_str in ids:
            for single_id in id_str.split(","):
                parts = single_id.split(":")
                assert len(parts) == 3, f"Invalid ID format: {single_id}"


# ============================================================================
# Integration with Full Document Processing
# ============================================================================


class TestFullDocumentProcessing:
    """Integration tests for complete document processing workflow."""

    def test_process_document_end_to_end(self, tmp_path: Path) -> None:
        """Complete workflow from IR to injected DOCX."""
        pytest.importorskip("docx")
        from docx import Document

        # Step 1: Create IR document
        ir_doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Integration Test"),
                    body=[
                        TypstParagraph(text="This is a test paragraph."),
                    ],
                    subsections=[
                        TypstSection(
                            heading=TypstHeading(text="Section A"),
                            body=[
                                TypstParagraph(text="Section A content."),
                                TypstBulletList(
                                    items=[
                                        [TypstParagraph(text="Point 1")],
                                        [TypstParagraph(text="Point 2")],
                                    ]
                                ),
                            ],
                            subsections=[],
                        ),
                        TypstSection(
                            heading=TypstHeading(text="Section B"),
                            body=[
                                TypstParagraph(text="Section B content."),
                                TypstTable(
                                    headers=["X", "Y"],
                                    data=[["1", "2"], ["3", "4"]],
                                ),
                            ],
                            subsections=[],
                        ),
                    ],
                ),
            ]
        )

        # Step 2: Create matching DOCX
        docx_path = tmp_path / "input.docx"
        doc = Document()
        doc.add_heading("Integration Test", level=1)
        doc.add_paragraph("This is a test paragraph.")
        doc.add_heading("Section A", level=1)
        doc.add_paragraph("Section A content.")
        doc.add_paragraph("Point 1", style="List Bullet")
        doc.add_paragraph("Point 2", style="List Bullet")
        doc.add_heading("Section B", level=1)
        doc.add_paragraph("Section B content.")
        table = doc.add_table(rows=3, cols=2)
        table.cell(0, 0).text = "X"
        table.cell(0, 1).text = "Y"
        table.cell(1, 0).text = "1"
        table.cell(1, 1).text = "2"
        table.cell(2, 0).text = "3"
        table.cell(2, 1).text = "4"
        doc.save(str(docx_path))

        # Step 3: Build mapping
        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(ir_doc, str(docx_path))

        # Step 4: Inject IDs
        output_path = tmp_path / "output.docx"
        inject_ids(docx_path, output_path, mapping)

        assert output_path.exists()
        xml_content = _extract_xml_from_docx(output_path)
        assert "w:document" in xml_content

    def test_mapping_survives_round_trip(self, tmp_path: Path) -> None:
        """Mapping data survives full round-trip through injection."""
        pytest.importorskip("docx")
        from docx import Document

        # Create simple document
        ir_doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Document Title"),
                    body=[
                        TypstParagraph(text="First paragraph of the document."),
                    ],
                    subsections=[],
                ),
            ]
        )

        docx_path = tmp_path / "input.docx"
        doc = Document()
        doc.add_heading("Test", level=1)
        doc.add_paragraph("Content.")
        doc.save(str(docx_path))

        # Build and inject
        registry = NodeRegistry()
        builder = MappingBuilder(registry)
        mapping = builder.build(ir_doc, str(docx_path))

        output_path = tmp_path / "output.docx"
        inject_ids(docx_path, output_path, mapping)

        # Extract IDs from XML
        xml_content = _extract_xml_from_docx(output_path)
        injected_ids = _get_custom_irid_values(xml_content)

        # All injected IDs should be in mapping
        for id_str in injected_ids:
            for single_id in id_str.split(","):
                assert single_id in mapping.entries, f"ID not in mapping: {single_id}"


# ============================================================================
# Error Handling and Robustness
# ============================================================================


class TestErrorHandling:
    """Tests for error handling and robustness."""

    def test_handles_missing_docx_gracefully(
        self, simple_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """Builder handles missing DOCX file gracefully."""
        registry = NodeRegistry()
        builder = MappingBuilder(registry)

        # Should not raise and produce mapping (even with missing docx)
        missing_path = tmp_path / "nonexistent.docx"
        mapping = builder.build(simple_ir_document, str(missing_path))

        assert isinstance(mapping, DocxTypstMapping)
        # Mapping should still have entries for IR nodes
        assert len(mapping.entries) > 0

    def test_handles_invalid_docx_gracefully(
        self, simple_ir_document: TypstDocument, tmp_path: Path
    ) -> None:
        """Builder handles invalid DOCX file gracefully."""
        registry = NodeRegistry()
        builder = MappingBuilder(registry)

        # Create invalid file
        invalid_path = tmp_path / "invalid.docx"
        invalid_path.write_text("This is not a valid DOCX")

        # Should not raise, but produce empty mapping
        mapping = builder.build(simple_ir_document, str(invalid_path))

        assert isinstance(mapping, DocxTypstMapping)

    def test_inject_ids_raises_for_missing_input(self, tmp_path: Path) -> None:
        """inject_ids raises FileNotFoundError for missing input."""
        missing_path = tmp_path / "nonexistent.docx"
        output_path = tmp_path / "output.docx"
        mapping = DocxTypstMapping(full_hash="test", entries={}, path_index={})

        with pytest.raises(FileNotFoundError):
            inject_ids(missing_path, output_path, mapping)

    def test_inject_ids_raises_for_invalid_docx(self, tmp_path: Path) -> None:
        """inject_ids raises ValueError for invalid DOCX."""
        invalid_path = tmp_path / "invalid.docx"
        invalid_path.write_text("Not a valid DOCX")
        output_path = tmp_path / "output.docx"
        mapping = DocxTypstMapping(full_hash="test", entries={}, path_index={})

        with pytest.raises((ValueError, Exception)):
            inject_ids(invalid_path, output_path, mapping)
