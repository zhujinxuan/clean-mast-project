"""Metadata for wind temporal report atoms.

Compliance: Subdomain layout | Value Object | frozen
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WindTemporalAtomMeta:
    """Metadata for wind temporal report atoms."""

    mast_name: str


__all__ = ["WindTemporalAtomMeta"]
