"""Metadata for multi-mast air density report value objects.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓
"""

from dataclasses import dataclass, field


@dataclass
class MultiMastMeta:
    """Metadata for multi-mast report atoms."""
    mast_name: str = "_all_masts"
    mast_names: list[str] = field(default_factory=list)
    caption: str | None = None
