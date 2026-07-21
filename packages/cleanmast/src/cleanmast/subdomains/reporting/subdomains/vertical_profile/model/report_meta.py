"""Metadata for vertical profile report atoms."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VerticalProfileAtomMeta:
    """Metadata for vertical profile report atoms."""

    mast_name: str
    caption: str | None = None


