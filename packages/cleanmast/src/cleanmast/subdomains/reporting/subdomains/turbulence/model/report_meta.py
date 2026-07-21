"""Metadata for single mast turbulence report atoms."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TurbulenceAtomMeta:
    """Metadata for turbulence report atoms."""

    mast_name: str
    interested_heights: list[float]


