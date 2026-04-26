"""Core types for enriched section algebra.

Provides generic, type-safe data structures for representing document sections
with arbitrary metadata and recursive subsection structures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from typst_ir.nodes import TypstHeading

Meta = TypeVar("Meta")
B = TypeVar("B")
A = TypeVar("A")


@dataclass(frozen=True)
class DepthMeta:
    """Minimal metadata carrying only section depth.

    Attributes:
        depth: Nesting depth of the section in the document hierarchy.
    """

    depth: int


@dataclass(frozen=True)
class BaseMeta:
    """Standard metadata for enriched sections.

    Attributes:
        node_id: Unique identifier for the node.
        path: Structural path to the node within the document.
        depth: Nesting depth of the section.
        section_idx: Index of the section among its siblings.
    """

    node_id: str
    path: str
    depth: int
    section_idx: int


@dataclass(frozen=True)
class DocumentMeta:
    """Minimal metadata for document root."""

    depth: int
    path: list[tuple[str, int]]


class EnrichedSectionF(BaseModel, Generic[Meta, B, A]):
    """Functorial enriched section.

    Represents a section enriched with metadata, where the recursive
    subsection slot is left open (parameterized by `A`).

    Attributes:
        meta: Section metadata of type `Meta`.
        heading: The section heading.
        body: Content blocks within this section.
        subsections: Nested subsections of type `A`.
    """

    model_config = ConfigDict(frozen=True)

    meta: Meta
    heading: TypstHeading
    body: list[B]
    subsections: list[A]


class EnrichedSectionFFix(BaseModel, Generic[Meta, B]):
    """Fixed-point enriched section.

    Represents a recursively nested section by instantiating the
    subsection slot of `EnrichedSectionF` with itself.

    Attributes:
        unfix: The underlying functorial section with recursive subsections.
    """

    model_config = ConfigDict(frozen=True)

    unfix: EnrichedSectionF[Meta, B, "EnrichedSectionFFix[Meta, B]"]


class EnrichedDocumentF(BaseModel, Generic[Meta, A]):
    """Functorial enriched document.

    Represents a document enriched with metadata, where the recursive
    child slot is left open (parameterized by `A`).

    Attributes:
        meta: Document metadata of type `Meta`.
        children: Child elements of type `A`.
    """

    model_config = ConfigDict(frozen=True)

    meta: Meta
    children: list[A]


class EnrichedDocument(BaseModel, Generic[Meta, B]):
    """Enriched document container.

    Attributes:
        children: Top-level sections of the document.
    """

    model_config = ConfigDict(frozen=True)

    children: list[EnrichedSectionFFix[Meta, B]]


class EnrichedDocumentFix(BaseModel, Generic[Meta, B]):
    """Fixed-point enriched document.

    Represents a document whose children are fixed-point enriched sections.

    Attributes:
        unfix: The underlying document with section children.
    """

    model_config = ConfigDict(frozen=True)

    unfix: EnrichedDocument[Meta, B]