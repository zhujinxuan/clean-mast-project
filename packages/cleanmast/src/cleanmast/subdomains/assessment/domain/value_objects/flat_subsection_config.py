"""Flat subsection configuration model.

ADR-GUARDRAILS: ddd-vo-001-value-objects, types-001-strict-type-safety
Compliance: Value Object ✓ | Strict types ✓
"""

from __future__ import annotations

import re

from pydantic import BaseModel, field_validator

from cleanmast.subdomains.assessment.domain.value_objects.rep_ts_report_config import (
    VALID_SUBSECTION_TYPES,
)

_INDEX_PATTERN = re.compile(r"^\d+(\.\d+)*$")


class FlatSubsectionConfig(BaseModel):
    """Flat (non-recursive) configuration for a report subsection.

    Used in the redesigned report config format where hierarchy is
    represented by dot-separated indices rather than nested objects.
    """

    index: str
    type: str
    title: str | None = None
    datasets: list[str] | None = None

    @field_validator("index")
    @classmethod
    def validate_index(cls, v: str) -> str:
        if not _INDEX_PATTERN.match(v):
            raise ValueError(
                f"index must match pattern r'^\\d+(\\.\\d+)*$', got '{v}'"
            )
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_SUBSECTION_TYPES:
            valid_types = ", ".join(sorted(VALID_SUBSECTION_TYPES))
            raise ValueError(
                f"Invalid subsection type '{v}'. Must be one of: {valid_types}"
            )
        return v
