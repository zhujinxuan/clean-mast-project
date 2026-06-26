"""Metadata for extreme wind report atoms.

Compliance: Subdomain layout | Value Object
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtremeWindAtomMeta:
    """Metadata for single-mast extreme wind report atoms."""

    mast_name: str


@dataclass(frozen=True)
class IECStandardsAtomMeta:
    """Metadata for no-mast report atoms (IEC standards)."""

    mast_name: str = "_no_mast"


