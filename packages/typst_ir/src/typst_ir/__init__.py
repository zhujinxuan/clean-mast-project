"""Typst Intermediate Representation for document processing.

This package provides type-safe, immutable Pydantic models for representing
Typst documents as an intermediate representation (IR). It enables:

- **Type-safe document construction** using frozen Pydantic BaseModels
- **JSON serialization** for CLI boundaries and inter-process communication
- **Multi-format rendering** to Typst markup, PDF, and DOCX
- **DOCX mapping** for traceability between IR nodes and DOCX paragraphs
- **Optional validation** using tree-sitter or regex fallback

The mapping module provides traceability capabilities:
- NodeID: Unique identifier for each IR node (path + hashes)
- NodeRegistry: Fast lookup of node IDs using Python's id() function
- MappingBuilder: Orchestrates the mapping creation process
- ID injection: Embeds traceability IDs into DOCX paragraphs via custom XML

Example:
    >>> from typst_ir import TypstDocument, TypstHeading, TypstParagraph
    >>> from typst_ir.renderer import render_to_pdf
    >>> doc = TypstDocument(children=[
    ...     TypstHeading(text="Title", level=1),
    ...     TypstParagraph(text="Content"),
    ... ])
    >>> pdf_path = render_to_pdf(doc.model_dump_json())
"""

from typst_ir import mapping
from typst_ir.nodes import (
    TypstBlock,
    TypstBulletList,
    TypstChild,
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
from typst_ir.renderer import (
    compile_typst_to_docx,
    compile_typst_to_pdf,
    render_to_docx,
    render_to_pdf,
    render_to_typst,
)
from typst_ir.serializer import serialize
from typst_ir.validation import (
    ValidationResult,
    escape_special_chars,
    validate_typst_content,
)

__all__ = [
    # Submodules
    "mapping",
    # Nodes
    "TypstBlock",
    "TypstBulletList",
    "TypstChild",
    "TypstCodeBlock",
    "TypstDocument",
    "TypstEquation",
    "TypstFigure",
    "TypstHeading",
    "TypstOrderedList",
    "TypstParagraph",
    "TypstRawBlock",
    "TypstSection",
    "TypstTable",
    # Serializer
    "serialize",
    # Renderer
    "render_to_typst",
    "render_to_pdf",
    "render_to_docx",
    "compile_typst_to_pdf",
    "compile_typst_to_docx",
    "ValidationResult",
    "validate_typst_content",
    "escape_special_chars",
]