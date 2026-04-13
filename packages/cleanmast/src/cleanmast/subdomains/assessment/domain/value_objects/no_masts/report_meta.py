"""Metadata for no-mast report value objects.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓
"""

from dataclasses import dataclass


@dataclass
class NoMastMeta:
    """Metadata for no-mast report atoms."""
    mast_name: str = "_no_mast"
    caption: str | None = None
