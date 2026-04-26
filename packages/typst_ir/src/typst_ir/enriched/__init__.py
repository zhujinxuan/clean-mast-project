"""Enriched section algebra for Typst IR.

Public types for representing document sections with arbitrary metadata
and recursive nesting structures.
"""

from typst_ir.enriched.cata import cata_enriched
from typst_ir.enriched.enrich import (
    depth_for_section,
    enrich_section,
    enrich_with_depth,
    identity_block,
)
from typst_ir.enriched.serialize_typst import serialize
from typst_ir.enriched.types import (
    BaseMeta,
    DepthMeta,
    DocumentMeta,
    EnrichedDocumentF,
    EnrichedDocumentFix,
    EnrichedSectionF,
    EnrichedSectionFFix,
)

__all__ = [
    "BaseMeta",
    "DepthMeta",
    "DocumentMeta",
    "EnrichedDocumentF",
    "EnrichedDocumentFix",
    "EnrichedSectionF",
    "EnrichedSectionFFix",
    "cata_enriched",
    "enrich_section",
    "depth_for_section",
    "identity_block",
    "enrich_with_depth",
    "serialize",
]
