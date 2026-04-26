"""Anamorphism for enriching Typst sections with metadata.

Provides `enrich_section()` and DepthMeta-specific helpers for building
recursive `EnrichedSectionFFix` structures from `TypstSection` seeds.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from typst_ir.enriched.types import DepthMeta, EnrichedSectionF, EnrichedSectionFFix
from typst_ir.nodes import TypstBodyBlock, TypstSection

Meta = TypeVar("Meta")
B = TypeVar("B")


def enrich_section(
    section: TypstSection,
    parent_meta: Meta,
    meta_for_sec: Callable[[TypstSection, Meta], Meta],
    meta_for_block: Callable[[TypstBodyBlock, Meta], B],
) -> EnrichedSectionFFix[Meta, B]:
    """Ana: build EnrichedSectionFFix from TypstSection.

    Recursively constructs an enriched section tree by applying metadata
    generation functions at each level. This is the anamorphism for the
    enriched section functor.

    Args:
        section: The source TypstSection to enrich.
        parent_meta: Metadata inherited from the parent section.
        meta_for_sec: Function to compute section metadata from parent meta.
        meta_for_block: Function to transform body blocks with section meta.

    Returns:
        A fixed-point enriched section with recursively nested subsections.
    """
    current_meta = meta_for_sec(section, parent_meta)
    return EnrichedSectionFFix(
        unfix=EnrichedSectionF(
            meta=current_meta,
            heading=section.heading,
            body=[meta_for_block(b, current_meta) for b in section.body],
            subsections=[
                enrich_section(s, current_meta, meta_for_sec, meta_for_block)
                for s in section.subsections
            ],
        )
    )


def depth_for_section(section: TypstSection, parent: DepthMeta) -> DepthMeta:
    """Compute section metadata by incrementing parent depth.

    Args:
        section: The section being processed (unused, present for signature).
        parent: The parent section's DepthMeta.

    Returns:
        DepthMeta with depth incremented by 1.
    """
    return DepthMeta(depth=parent.depth + 1)


def identity_block(block: TypstBodyBlock, meta: DepthMeta) -> TypstBodyBlock:
    """Return the block unchanged.

    Args:
        block: The body block to preserve.
        meta: The section metadata (unused, present for signature).

    Returns:
        The same block, unmodified.
    """
    return block


def enrich_with_depth(
    section: TypstSection,
) -> EnrichedSectionFFix[DepthMeta, TypstBodyBlock]:
    """Convenience wrapper: enrich a section with DepthMeta only.

    Uses `depth_for_section` and `identity_block` as default helpers,
    starting from a root depth of 0.

    Args:
        section: The source TypstSection to enrich.

    Returns:
        An enriched section tree with DepthMeta at each node.
    """
    return enrich_section(
        section,
        DepthMeta(0),
        depth_for_section,
        identity_block,
    )
