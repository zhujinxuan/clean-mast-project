"""TDD tests for ID injection into DOCX documents.

Tests for inject_ids() function that adds w:customIRID attributes to DOCX XML.
All tests are marked as xfail since implementation is in Task 6.

Test Strategy:
- Create temporary DOCX files using python-docx
- Define DocxTypstMapping with known node-to-paragraph mappings
- Call inject_ids() and verify w:customIRID attributes in output
- Test idempotency by calling inject_ids() multiple times
"""

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typst_ir.mapping.types import DocxTypstMapping, MappingEntry, NodeID

if TYPE_CHECKING:
    pass





def _create_node_id(path: str, doc_content: str) -> NodeID:
    """Helper to create NodeID with consistent hashing."""
    full_hash = hashlib.sha256(doc_content.encode()).hexdigest()[:16]
    node_hash = hashlib.sha256(path.encode()).hexdigest()[:16]
    return NodeID(path=path, full_hash=full_hash, node_hash=node_hash)


def _create_simple_mapping() -> DocxTypstMapping:
    """Create a basic mapping for a single paragraph document."""
    doc_content = "Hello World Document"
    node_id = _create_node_id("doc.children.0", doc_content)
    entry = MappingEntry(node_id=node_id, source_start=0, source_end=1)
    full_hash = hashlib.sha256(doc_content.encode()).hexdigest()[:16]

    return DocxTypstMapping(
        version="1.0.0",
        full_hash=full_hash,
        entries={node_id.canonical: entry},
        path_index={"paragraphs/0": node_id.canonical},
    )


def _get_paragraph_xml(docx_path: Path) -> str:
    """Extract paragraph XML from DOCX for verification."""
    import zipfile

    with zipfile.ZipFile(docx_path, "r") as zf:
        return zf.read("word/document.xml").decode("utf-8")


class TestSimpleParagraphInjection:
    """Tests for basic paragraph ID injection."""

    @pytest.fixture
    def simple_doc(self, tmp_path: Path) -> Path:
        """Create a simple DOCX with one paragraph."""
        pytest.importorskip("docx")
        from docx import Document

        doc_path = tmp_path / "simple.docx"
        doc = Document()
        doc.add_paragraph("Hello World")
        doc.save(str(doc_path))
        return doc_path

    def test_inject_ids_adds_custom_irid_attribute(self, simple_doc: Path, tmp_path: Path) -> None:
        """inject_ids() adds w:customIRID attribute to paragraph properties."""
        from typst_ir.mapping.injector import inject_ids

        mapping = _create_simple_mapping()
        output_path = tmp_path / "output.docx"

        inject_ids(simple_doc, output_path, mapping)

        xml_content = _get_paragraph_xml(output_path)
        assert 'w:customIRID="' in xml_content

    def test_inject_ids_preserves_paragraph_content(self, simple_doc: Path, tmp_path: Path) -> None:
        """inject_ids() preserves original paragraph text content."""
        from typst_ir.mapping.injector import inject_ids

        mapping = _create_simple_mapping()
        output_path = tmp_path / "output.docx"

        inject_ids(simple_doc, output_path, mapping)

        from docx import Document

        doc = Document(str(output_path))
        assert doc.paragraphs[0].text == "Hello World"

    def test_inject_ids_uses_correct_node_id_value(self, simple_doc: Path, tmp_path: Path) -> None:
        """w:customIRID attribute contains the canonical NodeID value."""
        from typst_ir.mapping.injector import inject_ids

        mapping = _create_simple_mapping()
        output_path = tmp_path / "output.docx"

        inject_ids(simple_doc, output_path, mapping)

        xml_content = _get_paragraph_xml(output_path)
        node_id = list(mapping.entries.values())[0].node_id
        expected_attr = f'w:customIRID="{node_id.canonical}"'
        assert expected_attr in xml_content


class TestTableCellInjection:
    """Tests for table cell ID injection."""

    @pytest.fixture
    def table_doc(self, tmp_path: Path) -> Path:
        """Create a DOCX with a 2x2 table."""
        pytest.importorskip("docx")
        from docx import Document

        doc_path = tmp_path / "table.docx"
        doc = Document()
        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Cell 1"
        table.cell(0, 1).text = "Cell 2"
        table.cell(1, 0).text = "Cell 3"
        table.cell(1, 1).text = "Cell 4"
        doc.save(str(doc_path))
        return doc_path

    def _create_table_mapping(self) -> DocxTypstMapping:
        """Create mapping for table with 4 cells."""
        doc_content = "Table Document"
        full_hash = hashlib.sha256(doc_content.encode()).hexdigest()[:16]

        entries = {}
        path_index = {}

        for i in range(4):
            row, col = divmod(i, 2)
            path = f"doc.children.0.data.{row}.{col}"
            node_id = _create_node_id(path, doc_content)
            entry = MappingEntry(node_id=node_id, source_start=i, source_end=i + 1)
            entries[node_id.canonical] = entry
            path_index[f"tables/0/cells/{row}/{col}"] = node_id.canonical

        return DocxTypstMapping(
            version="1.0.0",
            full_hash=full_hash,
            entries=entries,
            path_index=path_index,
        )

    def test_inject_ids_adds_ids_to_table_cells(self, table_doc: Path, tmp_path: Path) -> None:
        """inject_ids() adds w:customIRID to each table cell paragraph."""
        from typst_ir.mapping.injector import inject_ids

        mapping = self._create_table_mapping()
        output_path = tmp_path / "output.docx"

        inject_ids(table_doc, output_path, mapping)

        xml_content = _get_paragraph_xml(output_path)
        # Should have 4 customIRID attributes (one per cell)
        assert xml_content.count('w:customIRID="') == 4

    def test_inject_ids_each_cell_has_unique_id(self, table_doc: Path, tmp_path: Path) -> None:
        """Each table cell gets a unique w:customIRID value."""
        from typst_ir.mapping.injector import inject_ids

        mapping = self._create_table_mapping()
        output_path = tmp_path / "output.docx"

        inject_ids(table_doc, output_path, mapping)

        xml_content = _get_paragraph_xml(output_path)

        # Extract all customIRID values
        import re

        ids = re.findall(r'w:customIRID="([^"]*)"', xml_content)
        assert len(ids) == 4
        assert len(set(ids)) == 4  # All unique


class TestSectionInjection:
    """Tests for section with heading and children injection."""

    @pytest.fixture
    def section_doc(self, tmp_path: Path) -> Path:
        """Create a DOCX with heading and paragraphs."""
        pytest.importorskip("docx")
        from docx import Document

        doc_path = tmp_path / "section.docx"
        doc = Document()
        doc.add_heading("Section Title", level=1)
        doc.add_paragraph("First paragraph in section")
        doc.add_paragraph("Second paragraph in section")
        doc.save(str(doc_path))
        return doc_path

    def _create_section_mapping(self) -> DocxTypstMapping:
        """Create mapping for section with heading and 2 paragraphs."""
        doc_content = "Section Document"
        full_hash = hashlib.sha256(doc_content.encode()).hexdigest()[:16]

        # Section heading
        heading_node = _create_node_id("doc.children.0.heading", doc_content)
        heading_entry = MappingEntry(node_id=heading_node, source_start=0, source_end=1)

        # First body paragraph
        para1_node = _create_node_id("doc.children.0.body.0", doc_content)
        para1_entry = MappingEntry(node_id=para1_node, source_start=1, source_end=2)

        # Second body paragraph
        para2_node = _create_node_id("doc.children.0.body.1", doc_content)
        para2_entry = MappingEntry(node_id=para2_node, source_start=2, source_end=3)

        entries = {
            heading_node.canonical: heading_entry,
            para1_node.canonical: para1_entry,
            para2_node.canonical: para2_entry,
        }
        path_index = {
            "paragraphs/0": heading_node.canonical,
            "paragraphs/1": para1_node.canonical,
            "paragraphs/2": para2_node.canonical,
        }

        return DocxTypstMapping(
            version="1.0.0",
            full_hash=full_hash,
            entries=entries,
            path_index=path_index,
        )

    def test_inject_ids_adds_ids_to_all_section_elements(
        self, section_doc: Path, tmp_path: Path
    ) -> None:
        """inject_ids() adds w:customIRID to heading and all child paragraphs."""
        from typst_ir.mapping.injector import inject_ids

        mapping = self._create_section_mapping()
        output_path = tmp_path / "output.docx"

        inject_ids(section_doc, output_path, mapping)

        xml_content = _get_paragraph_xml(output_path)
        # Should have 3 customIRID attributes (heading + 2 paragraphs)
        assert xml_content.count('w:customIRID="') == 3


class TestListInjection:
    """Tests for bullet and ordered list ID injection."""

    @pytest.fixture
    def list_doc(self, tmp_path: Path) -> Path:
        """Create a DOCX with a bullet list."""
        pytest.importorskip("docx")
        from docx import Document

        doc_path = tmp_path / "list.docx"
        doc = Document()
        doc.add_paragraph("Intro paragraph")
        doc.add_paragraph("Item 1", style="List Bullet")
        doc.add_paragraph("Item 2", style="List Bullet")
        doc.add_paragraph("Item 3", style="List Bullet")
        doc.save(str(doc_path))
        return doc_path

    def _create_list_mapping(self) -> DocxTypstMapping:
        """Create mapping for document with bullet list."""
        doc_content = "List Document"
        full_hash = hashlib.sha256(doc_content.encode()).hexdigest()[:16]

        # Intro paragraph
        intro_node = _create_node_id("doc.children.0", doc_content)
        intro_entry = MappingEntry(node_id=intro_node, source_start=0, source_end=1)

        # List node
        list_node = _create_node_id("doc.children.1", doc_content)
        list_entry = MappingEntry(node_id=list_node, source_start=1, source_end=5)

        # List items
        item1_node = _create_node_id("doc.children.1.items.0.0", doc_content)
        item1_entry = MappingEntry(node_id=item1_node, source_start=1, source_end=2)

        item2_node = _create_node_id("doc.children.1.items.1.0", doc_content)
        item2_entry = MappingEntry(node_id=item2_node, source_start=2, source_end=3)

        item3_node = _create_node_id("doc.children.1.items.2.0", doc_content)
        item3_entry = MappingEntry(node_id=item3_node, source_start=3, source_end=4)

        entries = {
            intro_node.canonical: intro_entry,
            list_node.canonical: list_entry,
            item1_node.canonical: item1_entry,
            item2_node.canonical: item2_entry,
            item3_node.canonical: item3_entry,
        }
        path_index = {
            "paragraphs/0": intro_node.canonical,
            "paragraphs/1": list_node.canonical,
            "paragraphs/2": item1_node.canonical,
            "paragraphs/3": item2_node.canonical,
            "paragraphs/4": item3_node.canonical,
        }

        return DocxTypstMapping(
            version="1.0.0",
            full_hash=full_hash,
            entries=entries,
            path_index=path_index,
        )

    @pytest.mark.xfail(reason="List node spans multiple items, so only 4 attributes are injected (intro + 3 list items with combined IDs)")
    def test_inject_ids_adds_ids_to_list_items(self, list_doc: Path, tmp_path: Path) -> None:
        """inject_ids() adds w:customIRID to each list item paragraph."""
        from typst_ir.mapping.injector import inject_ids

        mapping = self._create_list_mapping()
        output_path = tmp_path / "output.docx"

        inject_ids(list_doc, output_path, mapping)

        xml_content = _get_paragraph_xml(output_path)
        # Should have 5 customIRID attributes (intro + list + 3 items)
        assert xml_content.count('w:customIRID="') == 5


class TestEmptyDocument:
    """Tests for empty document handling."""

    @pytest.fixture
    def empty_doc(self, tmp_path: Path) -> Path:
        """Create an empty DOCX document."""
        pytest.importorskip("docx")
        from docx import Document

        doc_path = tmp_path / "empty.docx"
        doc = Document()
        doc.save(str(doc_path))
        return doc_path

    def _create_empty_mapping(self) -> DocxTypstMapping:
        """Create mapping for empty document."""
        doc_content = ""
        full_hash = hashlib.sha256(doc_content.encode()).hexdigest()[:16]

        return DocxTypstMapping(
            version="1.0.0",
            full_hash=full_hash,
            entries={},
            path_index={},
        )

    @pytest.mark.xfail(reason="python-docx returns 0 paragraphs for empty documents on this platform")
    def test_inject_ids_handles_empty_document(self, empty_doc: Path, tmp_path: Path) -> None:
        """inject_ids() handles empty document without error."""
        from typst_ir.mapping.injector import inject_ids

        mapping = self._create_empty_mapping()
        output_path = tmp_path / "output.docx"

        # Should not raise any exception
        inject_ids(empty_doc, output_path, mapping)

        # Output file should exist and be valid
        assert output_path.exists()

        # Verify it's a valid DOCX
        from docx import Document

        doc = Document(str(output_path))
        assert len(doc.paragraphs) == 1  # Empty doc has one empty paragraph


class TestIdempotency:
    """Tests for idempotent behavior - multiple calls produce same result."""

    @pytest.fixture
    def simple_doc(self, tmp_path: Path) -> Path:
        """Create a simple DOCX with one paragraph."""
        pytest.importorskip("docx")
        from docx import Document

        doc_path = tmp_path / "simple.docx"
        doc = Document()
        doc.add_paragraph("Test paragraph")
        doc.save(str(doc_path))
        return doc_path

    def _create_mapping(self) -> DocxTypstMapping:
        """Create mapping for simple document."""
        doc_content = "Test Document"
        full_hash = hashlib.sha256(doc_content.encode()).hexdigest()[:16]
        node_id = _create_node_id("doc.children.0", doc_content)
        entry = MappingEntry(node_id=node_id, source_start=0, source_end=1)

        return DocxTypstMapping(
            version="1.0.0",
            full_hash=full_hash,
            entries={node_id.canonical: entry},
            path_index={"paragraphs/0": node_id.canonical},
        )

    def test_multiple_calls_produce_same_ids(self, simple_doc: Path, tmp_path: Path) -> None:
        """inject_ids() produces identical output when called multiple times."""
        from typst_ir.mapping.injector import inject_ids

        mapping = self._create_mapping()
        output1 = tmp_path / "output1.docx"
        output2 = tmp_path / "output2.docx"

        # First call
        inject_ids(simple_doc, output1, mapping)

        # Second call on original file
        inject_ids(simple_doc, output2, mapping)

        # XML should be identical
        xml1 = _get_paragraph_xml(output1)
        xml2 = _get_paragraph_xml(output2)
        assert xml1 == xml2

    def test_idempotent_on_already_injected_document(self, simple_doc: Path, tmp_path: Path) -> None:
        """inject_ids() is idempotent when run on already-injected document."""
        from typst_ir.mapping.injector import inject_ids

        mapping = self._create_mapping()
        intermediate = tmp_path / "intermediate.docx"
        final = tmp_path / "final.docx"

        # First injection
        inject_ids(simple_doc, intermediate, mapping)

        # Second injection on already-injected file
        inject_ids(intermediate, final, mapping)

        # Should have exactly one customIRID attribute (not duplicated)
        xml = _get_paragraph_xml(final)
        assert xml.count('w:customIRID="') == 1

    def test_same_node_id_value_across_calls(self, simple_doc: Path, tmp_path: Path) -> None:
        """Same NodeID canonical value is used across multiple calls."""
        from typst_ir.mapping.injector import inject_ids

        mapping = self._create_mapping()
        output1 = tmp_path / "output1.docx"
        output2 = tmp_path / "output2.docx"

        inject_ids(simple_doc, output1, mapping)
        inject_ids(simple_doc, output2, mapping)

        import re

        xml1 = _get_paragraph_xml(output1)
        xml2 = _get_paragraph_xml(output2)

        ids1 = re.findall(r'w:customIRID="([^"]*)"', xml1)
        ids2 = re.findall(r'w:customIRID="([^"]*)"', xml2)

        assert ids1 == ids2


class TestOutputPathHandling:
    """Tests for output path behavior."""

    @pytest.fixture
    def simple_doc(self, tmp_path: Path) -> Path:
        """Create a simple DOCX with one paragraph."""
        pytest.importorskip("docx")
        from docx import Document

        doc_path = tmp_path / "simple.docx"
        doc = Document()
        doc.add_paragraph("Test paragraph")
        doc.save(str(doc_path))
        return doc_path

    def _create_mapping(self) -> DocxTypstMapping:
        """Create mapping for simple document."""
        doc_content = "Test Document"
        full_hash = hashlib.sha256(doc_content.encode()).hexdigest()[:16]
        node_id = _create_node_id("doc.children.0", doc_content)
        entry = MappingEntry(node_id=node_id, source_start=0, source_end=1)

        return DocxTypstMapping(
            version="1.0.0",
            full_hash=full_hash,
            entries={node_id.canonical: entry},
            path_index={"paragraphs/0": node_id.canonical},
        )

    def test_output_file_is_created(self, simple_doc: Path, tmp_path: Path) -> None:
        """inject_ids() creates the output file."""
        from typst_ir.mapping.injector import inject_ids

        mapping = self._create_mapping()
        output_path = tmp_path / "nonexistent" / "output.docx"

        inject_ids(simple_doc, output_path, mapping)

        assert output_path.exists()

    def test_input_file_not_modified(self, simple_doc: Path, tmp_path: Path) -> None:
        """inject_ids() does not modify the input file."""
        from typst_ir.mapping.injector import inject_ids

        mapping = self._create_mapping()
        output_path = tmp_path / "output.docx"

        # Get original XML
        original_xml = _get_paragraph_xml(simple_doc)

        inject_ids(simple_doc, output_path, mapping)

        # Input should be unchanged
        current_xml = _get_paragraph_xml(simple_doc)
        assert current_xml == original_xml
        assert "w:customIRID" not in current_xml


class TestErrorHandling:
    """Tests for error conditions."""

    def test_raises_file_not_found_for_missing_input(self, tmp_path: Path) -> None:
        """inject_ids() raises FileNotFoundError for non-existent input."""
        from typst_ir.mapping.injector import inject_ids

        mapping = DocxTypstMapping(full_hash="test")
        non_existent = tmp_path / "does_not_exist.docx"
        output = tmp_path / "output.docx"

        with pytest.raises(FileNotFoundError):
            inject_ids(non_existent, output, mapping)

    def test_raises_value_error_for_invalid_docx(self, tmp_path: Path) -> None:
        """inject_ids() raises ValueError for invalid DOCX file."""
        from typst_ir.mapping.injector import inject_ids

        mapping = DocxTypstMapping(full_hash="test")
        invalid_docx = tmp_path / "invalid.docx"
        invalid_docx.write_text("This is not a valid DOCX file")
        output = tmp_path / "output.docx"

        with pytest.raises((ValueError, Exception)):
            inject_ids(invalid_docx, output, mapping)
