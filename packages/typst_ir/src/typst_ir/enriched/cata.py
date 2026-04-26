"""Catamorphism for enriched section algebra.

Provides a generic fold over `EnrichedSectionFFix` trees.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from typst_ir.enriched.types import (
    EnrichedDocumentFix,
    EnrichedSectionF,
    EnrichedSectionFFix,
)

Meta = TypeVar("Meta")
B = TypeVar("B")
A = TypeVar("A")


def cata_enriched(
    section: EnrichedSectionFFix[Meta, B],
    algebra: Callable[[EnrichedSectionF[Meta, B, A]], A],
) -> A:
    """Fold over an `EnrichedSectionFFix` tree using the provided algebra.

    The catamorphism recursively traverses the fixed-point tree bottom-up,
    applying the algebra at each node after processing all subsections.

    Args:
        section: The fixed-point enriched section to fold over.
        algebra: A function that takes a functorial layer with already-folded
            subsections and produces a result of type `A`.

    Returns:
        The result of applying the algebra to the entire tree.
    """
    layer = section.unfix
    processed_subsections = [
        cata_enriched(sub, algebra) for sub in layer.subsections
    ]
    rebuilt = EnrichedSectionF(
        meta=layer.meta,
        heading=layer.heading,
        body=layer.body,
        subsections=processed_subsections,
    )
    return algebra(rebuilt)


def map_document_children(
    doc: EnrichedDocumentFix[Meta, B],
    algebra: Callable[[EnrichedSectionF[Meta, B, A]], A],
) -> list[A]:
    """Map a catamorphism over each child section of a document.

    Applies `cata_enriched` to each top-level section in the document,
    using the provided algebra, and returns the list of results.

    Args:
        doc: The fixed-point enriched document whose children to process.
        algebra: A section algebra function passed to `cata_enriched`.

    Returns:
        A list containing the result of applying the algebra to each
        child section, in document order.
    """
    return [cata_enriched(child, algebra) for child in doc.unfix.children]