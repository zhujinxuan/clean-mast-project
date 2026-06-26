"""Metadata for single mast report atoms.

Compliance: Subdomain layout | Value Object
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WindRoseAtomMeta:
    """Metadata for single mast report atoms."""

    mast_name: str


