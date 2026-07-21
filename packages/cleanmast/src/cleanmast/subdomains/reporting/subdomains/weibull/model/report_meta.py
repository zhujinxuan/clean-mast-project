"""Metadata for Weibull report atoms."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WeibullAtomMeta:
    """Metadata for Weibull report atoms."""

    mast_name: str
