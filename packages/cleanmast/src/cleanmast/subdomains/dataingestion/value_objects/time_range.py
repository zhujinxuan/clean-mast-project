"""Time range value object for CleanMast.

ADR-GUARDRAILS: structure-001-subdomain-layout
Compliance: Value Object ✓ | DDD Compliant ✓
Description: Time range specification with validation
"""

from datetime import datetime

from pydantic import BaseModel, field_validator


class TimeRange(BaseModel):
    """Time range specification.

    Attributes:
        min: Start of time range (inclusive)
        max: End of time range (inclusive)
    """

    min: datetime
    max: datetime

    @field_validator("min", "max", mode="before")
    @classmethod
    def parse_datetime(cls, v: datetime | str) -> datetime:
        """Parse datetime from ISO string if needed."""
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
