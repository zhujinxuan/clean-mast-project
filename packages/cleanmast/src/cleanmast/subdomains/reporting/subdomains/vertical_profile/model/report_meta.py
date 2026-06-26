"""Metadata for vertical profile report atoms.

Compliance: Subdomain layout | Value Object
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class VerticalProfileAtomMeta:
    """Metadata for vertical profile report atoms."""

    mast_name: str
    caption: str | None = None


