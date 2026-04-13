"""Tests for mapping types - NodeID and MappingEntry.

Verifies frozen Pydantic models for IR to source document mapping.
"""

import pytest
from pydantic import ValidationError
from typst_ir.mapping.types import (
    ConfidenceLevel,
    DetectionMethod,
    DocxParagraph,
    DocxTypstMapping,
    MappingEntry,
    NodeID,
)


class TestNodeID:
    """Tests for NodeID model."""

    def test_node_id_creation(self) -> None:
        """NodeID can be created with required fields."""
        node_id = NodeID(path="doc.children.0", full_hash="abc123", node_hash="def456")
        assert node_id.path == "doc.children.0"
        assert node_id.full_hash == "abc123"
        assert node_id.node_hash == "def456"

    def test_node_id_is_frozen(self) -> None:
        """NodeID is immutable (frozen model)."""
        node_id = NodeID(path="doc.children.0", full_hash="abc123", node_hash="def456")
        with pytest.raises(ValidationError):
            node_id.path = "doc.children.1"

    def test_node_id_canonical_property(self) -> None:
        """canonical property returns colon-separated format."""
        node_id = NodeID(path="doc.children.0", full_hash="abc123", node_hash="def456")
        assert node_id.canonical == "doc.children.0:abc123:def456"

    def test_node_id_canonical_different_values(self) -> None:
        """canonical property works with different field values."""
        node_id = NodeID(path="root.section.heading", full_hash="hash1", node_hash="hash2")
        assert node_id.canonical == "root.section.heading:hash1:hash2"

    def test_node_id_missing_fields(self) -> None:
        """NodeID requires all three fields."""
        with pytest.raises(ValidationError):
            NodeID(path="doc.children.0", full_hash="abc123")

    def test_node_id_wrong_types(self) -> None:
        """NodeID validates field types."""
        with pytest.raises(ValidationError):
            NodeID(path=123, full_hash="abc123", node_hash="def456")

    def test_node_id_is_hashable(self) -> None:
        """NodeID can be used as dictionary key."""
        node_id = NodeID(path="doc.children.0", full_hash="abc123", node_hash="def456")
        d = {node_id: "value"}
        assert d[node_id] == "value"

    def test_node_id_equality(self) -> None:
        """NodeID instances with same values are equal."""
        node_id1 = NodeID(path="doc.children.0", full_hash="abc123", node_hash="def456")
        node_id2 = NodeID(path="doc.children.0", full_hash="abc123", node_hash="def456")
        assert node_id1 == node_id2

    def test_node_id_inequality(self) -> None:
        """NodeID instances with different values are not equal."""
        node_id1 = NodeID(path="doc.children.0", full_hash="abc123", node_hash="def456")
        node_id2 = NodeID(path="doc.children.1", full_hash="abc123", node_hash="def456")
        assert node_id1 != node_id2


class TestMappingEntry:
    """Tests for MappingEntry model."""

    def test_mapping_entry_creation(self) -> None:
        """MappingEntry can be created with required fields."""
        node_id = NodeID(path="doc.children.0", full_hash="abc123", node_hash="def456")
        entry = MappingEntry(node_id=node_id, source_start=0, source_end=5)
        assert entry.node_id == node_id
        assert entry.source_start == 0
        assert entry.source_end == 5

    def test_mapping_entry_is_frozen(self) -> None:
        """MappingEntry is immutable (frozen model)."""
        node_id = NodeID(path="doc.children.0", full_hash="abc123", node_hash="def456")
        entry = MappingEntry(node_id=node_id, source_start=0, source_end=5)
        with pytest.raises(ValidationError):
            entry.source_start = 10

    def test_mapping_entry_missing_fields(self) -> None:
        """MappingEntry requires all three fields."""
        node_id = NodeID(path="doc.children.0", full_hash="abc123", node_hash="def456")
        with pytest.raises(ValidationError):
            MappingEntry(node_id=node_id, source_start=0)

    def test_mapping_entry_wrong_types(self) -> None:
        """MappingEntry validates field types."""
        node_id = NodeID(path="doc.children.0", full_hash="abc123", node_hash="def456")
        with pytest.raises(ValidationError):
            MappingEntry(node_id=node_id, source_start="zero", source_end=5)

    def test_mapping_entry_is_hashable(self) -> None:
        """MappingEntry can be used as dictionary key."""
        node_id = NodeID(path="doc.children.0", full_hash="abc123", node_hash="def456")
        entry = MappingEntry(node_id=node_id, source_start=0, source_end=5)
        d = {entry: "paragraph"}
        assert d[entry] == "paragraph"

    def test_mapping_entry_equality(self) -> None:
        """MappingEntry instances with same values are equal."""
        node_id = NodeID(path="doc.children.0", full_hash="abc123", node_hash="def456")
        entry1 = MappingEntry(node_id=node_id, source_start=0, source_end=5)
        entry2 = MappingEntry(node_id=node_id, source_start=0, source_end=5)
        assert entry1 == entry2

    def test_mapping_entry_inequality(self) -> None:
        """MappingEntry instances with different values are not equal."""
        node_id = NodeID(path="doc.children.0", full_hash="abc123", node_hash="def456")
        entry1 = MappingEntry(node_id=node_id, source_start=0, source_end=5)
        entry2 = MappingEntry(node_id=node_id, source_start=0, source_end=6)
        assert entry1 != entry2

    def test_mapping_entry_nested_node_id(self) -> None:
        """MappingEntry properly nests NodeID."""
        node_id = NodeID(path="root", full_hash="h1", node_hash="h2")
        entry = MappingEntry(node_id=node_id, source_start=10, source_end=20)
        assert entry.node_id.canonical == "root:h1:h2"

    def test_mapping_entry_negative_indices(self) -> None:
        """MappingEntry accepts negative indices for source positions."""
        node_id = NodeID(path="doc", full_hash="h1", node_hash="h2")
        entry = MappingEntry(node_id=node_id, source_start=-1, source_end=-5)
        assert entry.source_start == -1
        assert entry.source_end == -5

    def test_mapping_entry_zero_width_range(self) -> None:
        """MappingEntry allows zero-width source range."""
        node_id = NodeID(path="doc", full_hash="h1", node_hash="h2")
        entry = MappingEntry(node_id=node_id, source_start=5, source_end=5)
        assert entry.source_start == entry.source_end

    def test_mapping_entry_defaults(self) -> None:
        """MappingEntry has safe defaults for new detection fields."""
        node_id = NodeID(path="doc", full_hash="h1", node_hash="h2")
        entry = MappingEntry(node_id=node_id, source_start=0, source_end=5)
        assert entry.method is None
        assert entry.confidence is None
        assert entry.details == {}

    def test_mapping_entry_with_detection_fields(self) -> None:
        """MappingEntry accepts detection metadata fields."""
        node_id = NodeID(path="doc", full_hash="h1", node_hash="h2")
        entry = MappingEntry(
            node_id=node_id,
            source_start=0,
            source_end=5,
            method=DetectionMethod.fingerprint,
            confidence=ConfidenceLevel.high,
            details={"matched_text": "hello"},
        )
        assert entry.method == DetectionMethod.fingerprint
        assert entry.confidence == ConfidenceLevel.high
        assert entry.details == {"matched_text": "hello"}

    def test_mapping_entry_json_roundtrip(self) -> None:
        """MappingEntry serializes and deserializes correctly."""
        node_id = NodeID(path="doc", full_hash="h1", node_hash="h2")
        entry = MappingEntry(
            node_id=node_id,
            source_start=10,
            source_end=50,
            method=DetectionMethod.positional,
            confidence=ConfidenceLevel.medium,
            details={"reason": "adjacent paragraph"},
        )
        json_str = entry.model_dump_json()
        restored = MappingEntry.model_validate_json(json_str)
        assert restored == entry

    def test_mapping_entry_json_roundtrip_defaults(self) -> None:
        """MappingEntry round-trips with default detection fields."""
        node_id = NodeID(path="doc", full_hash="h1", node_hash="h2")
        entry = MappingEntry(node_id=node_id, source_start=0, source_end=5)
        json_str = entry.model_dump_json()
        restored = MappingEntry.model_validate_json(json_str)
        assert restored == entry
        assert restored.method is None
        assert restored.confidence is None
        assert restored.details == {}

    def test_mapping_entry_legacy_json_without_detection_fields(self) -> None:
        """Legacy JSON without method/confidence/details deserializes correctly."""
        legacy_json = (
            '{"node_id": {"path": "doc", "full_hash": "h1", "node_hash": "h2"}, '
            '"source_start": 0, "source_end": 5}'
        )
        restored = MappingEntry.model_validate_json(legacy_json)
        assert restored.source_start == 0
        assert restored.source_end == 5
        assert restored.method is None
        assert restored.confidence is None
        assert restored.details == {}


class TestDetectionMethod:
    """Tests for DetectionMethod enum."""

    def test_detection_method_values(self) -> None:
        """DetectionMethod contains all expected values."""
        assert DetectionMethod.fingerprint == "fingerprint"
        assert DetectionMethod.style == "style"
        assert DetectionMethod.structure == "structure"
        assert DetectionMethod.drawing == "drawing"
        assert DetectionMethod.positional == "positional"
        assert DetectionMethod.xpath == "xpath"
        assert DetectionMethod.caption == "caption"


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""

    def test_confidence_level_values(self) -> None:
        """ConfidenceLevel contains all expected values."""
        assert ConfidenceLevel.high == "high"
        assert ConfidenceLevel.medium == "medium"
        assert ConfidenceLevel.low == "low"


class TestDocxParagraph:
    """Tests for DocxParagraph model."""

    def test_docx_paragraph_creation(self) -> None:
        """DocxParagraph can be created with required fields."""
        para = DocxParagraph(
            index=0,
            text_preview="First paragraph text...",
            text_hash="abc123def456",
        )
        assert para.index == 0
        assert para.text_preview == "First paragraph text..."
        assert para.text_hash == "abc123def456"
        assert para.paragraph_type == "paragraph"  # default value

    def test_docx_paragraph_with_type(self) -> None:
        """DocxParagraph accepts custom paragraph_type."""
        para = DocxParagraph(
            index=5,
            text_preview="Heading text",
            text_hash="hash789",
            paragraph_type="heading",
        )
        assert para.paragraph_type == "heading"

    def test_docx_paragraph_is_frozen(self) -> None:
        """DocxParagraph is immutable (frozen model)."""
        para = DocxParagraph(
            index=1,
            text_preview="Immutable test",
            text_hash="hash123",
        )
        with pytest.raises(ValidationError):
            para.index = 2

    def test_docx_paragraph_missing_index(self) -> None:
        """DocxParagraph requires index field."""
        with pytest.raises(ValidationError):
            DocxParagraph(
                text_preview="No index",
                text_hash="hash",
            )

    def test_docx_paragraph_missing_preview(self) -> None:
        """DocxParagraph requires text_preview field."""
        with pytest.raises(ValidationError):
            DocxParagraph(
                index=0,
                text_hash="hash",
            )

    def test_docx_paragraph_missing_hash(self) -> None:
        """DocxParagraph requires text_hash field."""
        with pytest.raises(ValidationError):
            DocxParagraph(
                index=0,
                text_preview="No hash",
            )

    def test_docx_paragraph_paragraph_types(self) -> None:
        """Various paragraph_type values work correctly."""
        types = ["paragraph", "heading", "table_cell", "list_item", "custom"]
        for i, ptype in enumerate(types):
            para = DocxParagraph(
                index=i,
                text_preview=f"Type {ptype}",
                text_hash=f"hash{i}",
                paragraph_type=ptype,
            )
            assert para.paragraph_type == ptype


class TestDocxTypstMapping:
    """Tests for DocxTypstMapping container."""

    def test_docx_typst_mapping_empty(self) -> None:
        """DocxTypstMapping can be created with just full_hash."""
        mapping = DocxTypstMapping(full_hash="doc_hash_123")
        assert mapping.version == "1.0.0"  # default
        assert mapping.full_hash == "doc_hash_123"
        assert mapping.entries == {}
        assert mapping.path_index == {}

    def test_docx_typst_mapping_with_entries(self) -> None:
        """DocxTypstMapping can be created with entries."""
        node_id = NodeID(path="doc.children.0", full_hash="doc_hash", node_hash="node_hash")
        entry = MappingEntry(node_id=node_id, source_start=0, source_end=100)
        mapping = DocxTypstMapping(
            version="1.0.0",
            full_hash="doc_hash_456",
            entries={node_id.canonical: entry},
            path_index={"paragraphs/0": node_id.canonical},
        )
        assert mapping.full_hash == "doc_hash_456"
        assert len(mapping.entries) == 1
        assert node_id.canonical in mapping.entries

    def test_docx_typst_mapping_is_frozen(self) -> None:
        """DocxTypstMapping is immutable (frozen model)."""
        mapping = DocxTypstMapping(full_hash="hash")
        with pytest.raises(ValidationError):
            mapping.full_hash = "new_hash"

    def test_docx_typst_mapping_missing_full_hash(self) -> None:
        """DocxTypstMapping requires full_hash field."""
        with pytest.raises(ValidationError):
            DocxTypstMapping()

    def test_docx_typst_mapping_entry_lookup(self) -> None:
        """Can look up entries by node_id canonical."""
        node_id = NodeID(path="doc.children.0", full_hash="doc_hash", node_hash="node_hash")
        entry = MappingEntry(node_id=node_id, source_start=10, source_end=50)
        mapping = DocxTypstMapping(
            full_hash="doc_hash",
            entries={node_id.canonical: entry},
        )
        assert mapping.entries[node_id.canonical] == entry

    def test_docx_typst_mapping_path_index(self) -> None:
        """Can use path_index for reverse lookup."""
        node_id = NodeID(path="doc.children.0", full_hash="doc_hash", node_hash="node_hash")
        mapping = DocxTypstMapping(
            full_hash="doc_hash",
            path_index={"paragraphs/5": node_id.canonical},
        )
        assert mapping.path_index["paragraphs/5"] == node_id.canonical

    def test_docx_typst_mapping_serialization(self) -> None:
        """DocxTypstMapping serializes and deserializes correctly."""
        node_id = NodeID(path="doc.children.0", full_hash="doc_hash", node_hash="node_hash")
        entry = MappingEntry(node_id=node_id, source_start=10, source_end=50)
        mapping = DocxTypstMapping(
            version="1.0.0",
            full_hash="full_doc_hash",
            entries={node_id.canonical: entry},
            path_index={"paragraphs/0": node_id.canonical},
        )

        json_str = mapping.model_dump_json()
        restored = DocxTypstMapping.model_validate_json(json_str)

        assert restored.version == mapping.version
        assert restored.full_hash == mapping.full_hash
        assert len(restored.entries) == len(mapping.entries)
        assert restored.path_index == mapping.path_index
