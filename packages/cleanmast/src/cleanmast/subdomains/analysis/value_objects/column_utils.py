"""Column utility functions for analysis subdomain.

ADR-GUARDRAILS: ddd-vo-001-value-objects
Compliance: Value Object ✓
"""

import re

FILL_TYPE_PATTERN = r"_fill:(\w+)$"

# Chinese display labels for fill types
FILL_TYPE_LABELS: dict[str, str] = {
    "extrapolated": "外推",
    "interpolated": "内插",
}


def detect_interpolation_marker(column_name: str) -> str:
    """Detect fill type marker from column name.

    Returns Chinese label:
    - "外推" for extrapolated (extrapolated)
    - "内插" for interpolated (interpolated)
    - Empty string if no fill marker found (original measured data)

    Pattern: *_fill:{type} at end of column name
    """
    if match := re.search(FILL_TYPE_PATTERN, column_name, re.IGNORECASE):
        fill_type = match.group(1).lower()
        return FILL_TYPE_LABELS.get(fill_type, "")
    return ""
