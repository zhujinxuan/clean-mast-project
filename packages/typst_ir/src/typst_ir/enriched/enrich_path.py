"""Path enrichment anamorphism for Typst sections.

Provides `enrich_with_path()` for building recursive `EnrichedSectionFFix`
structures where each section is annotated with its hierarchical `PathMeta`.
"""

from __future__ import annotations

from typst_ir.enriched.docx_types import PathMeta
from typst_ir.enriched.types import (
    EnrichedDocument,
    EnrichedDocumentFix,
    EnrichedSectionF,
    EnrichedSectionFFix,
)
from typst_ir.nodes import TypstBodyBlock, TypstDocument, TypstSection


def compute_section_index(path: list[tuple[str, int]]) -> str:
    """Compute a dotted section index from a traversal path.

    Filters the path for ``("section", index)`` tuples only, converts
    each index to 1-based, and joins with ``"."``.

    Args:
        path: A list of (context, index) tuples from document traversal.

    Returns:
        Dotted section index string, or empty string if no sections.

    Examples:
        >>> compute_section_index([("section", 0)])
        '1'
        >>> compute_section_index([("section", 0), ("section", 1)])
        '1.2'
        >>> compute_section_index([])
        ''
    """
    indices = [i + 1 for (ctx, i) in path if ctx == "section"]
    return ".".join(str(i) for i in indices)


def path_for_section(
    section: TypstSection, parent: PathMeta, sibling_idx: int
) -> PathMeta:
    """Compute section PathMeta by appending the sibling index.

    Args:
        section: The section being processed (unused, present for signature).
        parent: The parent section's PathMeta.
        sibling_idx: Index of this section among its siblings.

    Returns:
        PathMeta with the new ("section", sibling_idx) pair appended.
    """
    new_path = parent.path + [("section", sibling_idx)]
    return PathMeta(depth=len(new_path), path=new_path)


def _identity_block(block: TypstBodyBlock, meta: PathMeta) -> TypstBodyBlock:
    """Return the block unchanged."""
    return block


def _build(
    sec: TypstSection,
    parent_path: list[tuple[str, int]],
    idx: int,
) -> EnrichedSectionFFix[PathMeta, TypstBodyBlock]:
    current_path = parent_path + [("section", idx)]
    current_meta = PathMeta(depth=len(current_path), path=current_path)
    return EnrichedSectionFFix(
        unfix=EnrichedSectionF(
            meta=current_meta,
            heading=sec.heading,
            body=[_identity_block(b, current_meta) for b in sec.body],
            subsections=[
                _build(sub, current_path, i)
                for i, sub in enumerate(sec.subsections)
            ],
        )
    )


def enrich_with_path(
    section: TypstSection,
) -> EnrichedSectionFFix[PathMeta, TypstBodyBlock]:
    """Enrich a section tree with PathMeta tracking structural paths.

    Each section receives a path composed of ("section", sibling_index)
    tuples from the root down to the current node. Body blocks are passed
    through unchanged via ``identity_block``.

    Args:
        section: The source TypstSection to enrich.

    Returns:
        An enriched section tree with PathMeta at each node.
    """
    return _build(section, [], 0)


def enrich_document_with_path(
    doc: TypstDocument,
) -> EnrichedDocumentFix[PathMeta, TypstBodyBlock]:
    enriched_children = [
        _build(section, [], sec_idx)
        for sec_idx, section in enumerate(doc.children)
    ]
    return EnrichedDocumentFix(
        unfix=EnrichedDocument(children=enriched_children)
    )
