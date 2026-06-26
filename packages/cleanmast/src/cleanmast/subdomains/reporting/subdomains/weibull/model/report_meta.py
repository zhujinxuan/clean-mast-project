"""Metadata for Weibull report atoms.

Compliance: Subdomain layout | Value Object
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WeibullAtomMeta:
    """Metadata for Weibull report atoms."""

    mast_name: str
