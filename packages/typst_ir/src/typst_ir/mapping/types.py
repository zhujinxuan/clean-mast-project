"""Core types for IR to source document mapping.

Defines Pydantic models for identifying IR nodes and mapping them
to their original source locations in input documents.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field


class DetectionMethod(StrEnum):
    """Method used to detect the mapping between an IR node and its source."""

    fingerprint = "fingerprint"
    style = "style"
    structure = "structure"
    drawing = "drawing"
    positional = "positional"
    xpath = "xpath"
    caption = "caption"


class ConfidenceLevel(StrEnum):
    """Confidence level of a mapping detection result."""

    high = "high"
    medium = "medium"
    low = "low"


class NodeID(BaseModel):
    """Unique identifier for an IR node.

    Combines a hierarchical path, full document hash, and node-specific hash
to create a unique, deterministic identifier for any node in the IR tree.

    Attributes:
        path: Hierarchical path to the node (e.g., "doc.children.0")
        full_hash: Hash of the entire document content
        node_hash: Hash of this specific node's content
    """

    model_config = ConfigDict(frozen=True)

    path: str
    full_hash: str
    node_hash: str

    @property
    def canonical(self) -> str:
        """Return canonical string representation.

        Format: "path:full_hash:node_hash"

        Returns:
            Canonical identifier string suitable for use as a dictionary key.
        """
        return f"{self.path}:{self.full_hash}:{self.node_hash}"


class MappingEntry(BaseModel):
    """Entry mapping an IR node to its source document location.

    Represents the bidirectional relationship between an IR node
    and its origin in the source document (e.g., DOCX paragraph range).

    Attributes:
        node_id: Unique identifier for the IR node
        source_start: Start index in the source document (inclusive)
        source_end: End index in the source document (exclusive)
        method: Detection method that produced this mapping
        confidence: Confidence level of the mapping
        details: Additional metadata about the detection
    """

    model_config = ConfigDict(frozen=True)

    node_id: NodeID
    source_start: int
    source_end: int
    method: DetectionMethod | None = None
    confidence: ConfidenceLevel | None = None
    details: Dict[str, Any] = Field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.node_id, self.source_start, self.source_end, self.method, self.confidence))


class DocxParagraph(BaseModel):
    """Represents a paragraph from a DOCX source document.

    Captures metadata about a paragraph extracted from a DOCX file to enable
    matching with Typst IR nodes and debugging of the conversion process.

    Attributes:
        index: Zero-based position of the paragraph in the document
        text_preview: First 100 characters of the paragraph text for debugging
        text_hash: Hash of the full paragraph text for exact matching
        paragraph_type: Classification of the paragraph (e.g., 'paragraph',
            'heading', 'table_cell', 'list_item')
    """

    model_config = ConfigDict(frozen=True)

    index: int = Field(
        description="Zero-based position of the paragraph in the document"
    )
    text_preview: str = Field(
        description="First 100 characters of the paragraph text for debugging",
        max_length=100,
    )
    text_hash: str = Field(
        description="Hash of the full paragraph text for exact matching"
    )
    paragraph_type: str = Field(
        default="paragraph",
        description="Classification: 'paragraph', 'heading', 'table_cell', 'list_item'",
    )


class DocxTypstMapping(BaseModel):
    """Container for complete DOCX-to-Typst IR mapping.

    Stores all mappings between a DOCX source document and its generated
    Typst IR representation, enabling round-trip navigation and debugging.

    Attributes:
        version: Schema version for migration support (e.g., '1.0.0')
        full_hash: Document-wide hash for change detection and validation
        entries: Dictionary mapping node ID strings to MappingEntry records
        path_index: Reverse index mapping source paths to node ID strings
    """

    model_config = ConfigDict(frozen=True)

    version: str = Field(
        default="1.0.0",
        description="Schema version for migration support (e.g., '1.0.0')"
    )
    full_hash: str = Field(
        description="Document-wide hash for change detection and validation"
    )
    entries: Dict[str, MappingEntry] = Field(
        default_factory=dict,
        description="Dictionary mapping node ID (canonical string) to MappingEntry records"
    )
    path_index: Dict[str, str] = Field(
        default_factory=dict,
        description="Reverse index mapping source paths to node ID (canonical string) for lookup"
    )
