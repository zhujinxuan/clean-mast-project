"""Metadata for multi-mast air density report atoms.

Compliance: Subdomain layout | Value Object
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AirDensityAtomMeta:
    """Metadata for multi-mast report atoms."""

    mast_name: str = "_all_masts"
    mast_names: list[str] = field(default_factory=list)
