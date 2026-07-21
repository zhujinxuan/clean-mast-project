"""Metadata for single mast report atoms."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WindRoseAtomMeta:
    """Metadata for single mast report atoms."""

    mast_name: str


