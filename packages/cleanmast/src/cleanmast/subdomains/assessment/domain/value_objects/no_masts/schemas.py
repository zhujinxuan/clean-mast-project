"""Report schemas for no-mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓ | Schema Validation ✓
"""

import dataframely as dy


class IECStandardsSchema(dy.Schema):
    """Schema for IEC wind class standards.

    iec_class | vref | ve50

    Example:
        iec_class | vref | ve50
        "I"       | 10.0 | 70.0
    """

    iec_class = dy.String(nullable=False)
    vref = dy.Float64(nullable=False)
    ve50 = dy.Float64(nullable=False)
