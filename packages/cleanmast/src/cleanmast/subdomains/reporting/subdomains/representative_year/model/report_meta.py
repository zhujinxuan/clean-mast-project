"""Metadata for representative year calibration report atoms.

Compliance: Subdomain layout | Value Object
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RepresentativeYearAtomMeta:
    """Metadata for representative year calibration report atoms."""

    mast_name: str = "_all_masts"
    mast_names: list[str] = field(default_factory=list)
