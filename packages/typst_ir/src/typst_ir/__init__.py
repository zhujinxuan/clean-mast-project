"""Typst Intermediate Representation for document processing.

This package provides type-safe, immutable Pydantic models for representing
Typst documents as an intermediate representation (IR). It enables:

- **Type-safe document construction** using frozen Pydantic BaseModels
- **JSON serialization** for CLI boundaries and inter-process communication
- **Multi-format rendering** to Typst markup, PDF, and DOCX
- **Optional validation** using tree-sitter or regex fallback

Example:
    >>> from typst_ir import TypstDocument, TypstHeading, TypstParagraph
    >>> from typst_ir.renderer import render_to_pdf
    >>> doc = TypstDocument(children=[
    ...     TypstHeading(text="Title", level=1),
    ...     TypstParagraph(text="Content"),
    ... ])
    >>> pdf_path = render_to_pdf(doc.model_dump_json())
"""

from typst_ir.docx_paragraph_map import DocxBlockRange, extract_paragraph_ranges
from typst_ir.enriched.enrich import enrich_with_depth
from typst_ir.enriched.serialize_typst import serialize as _serialize_enriched
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
from typst_ir.polish_ir import ChangeStyle, CreateStyle, EditStyle, PolishIR
from typst_ir.polish_styles import DEFAULT_STYLE_DEFS, StyleDef, StyleProperties
from typst_ir.renderer import (
    compile_typst_to_docx,
    compile_typst_to_pdf,
    render_to_docx,
    render_to_pdf,
    render_to_typst,
)
from typst_ir.typst_block_type import TypstBlockType, build_block_type_map
from typst_ir.validation import (
    ValidationResult,
    escape_special_chars,
    validate_typst_content,
)


def serialize(node: TypstDocument) -> str:
    if not isinstance(node, TypstDocument):
        raise TypeError(f"Expected TypstDocument root, got {type(node).__name__}")
    parts = [_serialize_enriched(enrich_with_depth(child)) for child in node.children]
    return "\n".join(parts)


__all__ = [
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
    # Validation
    "ValidationResult",
    "validate_typst_content",
    "escape_special_chars",
    "ChangeStyle",
    "CreateStyle",
    "EditStyle",
    "PolishIR",
    "StyleDef",
    "StyleProperties",
    "DEFAULT_STYLE_DEFS",
    "DocxBlockRange",
    "extract_paragraph_ranges",
    "TypstBlockType",
    "build_block_type_map",
]