"""Metadata for single-mast wind frequency report atoms."""

from dataclasses import dataclass

from cleanmast.subdomains.reporting.model import get_height_display_name


@dataclass(frozen=True)
class WindFrequencyAtomMeta:
    """Metadata for single-mast wind frequency report atoms."""

    mast_name: str


def _height_label(height: float, marker: str | None) -> str:
    """Generate display label for a height with optional interpolation marker."""
    return get_height_display_name(height, marker or "")
