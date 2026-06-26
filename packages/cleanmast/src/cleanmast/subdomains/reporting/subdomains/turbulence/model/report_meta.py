"""Metadata for single mast turbulence report atoms.

Compliance: Subdomain layout | Value Object | frozen
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TurbulenceAtomMeta:
    """Metadata for turbulence report atoms."""

    mast_name: str


