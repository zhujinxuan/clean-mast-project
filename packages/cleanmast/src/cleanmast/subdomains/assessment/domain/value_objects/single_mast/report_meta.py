"""Metadata for single mast report value objects.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓
"""

from dataclasses import dataclass


@dataclass
class SingleMastMeta:
    """Metadata for single mast report atoms."""
    mast_name: str
    air_density: float = 1.225  # Calculated in recommend phase
    caption: str | None = None
    width: str = "80%"


def get_height_display_name(height: float, marker: str = "") -> str:
    """Generate display name for a height level.

    Args:
        height: Height value in meters
        marker: Interpolation/extrapolation marker (e.g., "外推", "内插")

    Returns:
        Formatted display name like "125m 外推" or "100m"
    """
    base = f"{int(height)}m"
    if marker:
        return f"{base} {marker}"
    return base
