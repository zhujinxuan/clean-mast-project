"""Report schemas for multi-mast air density analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓ | Schema Validation ✓
"""

import dataframely as dy


class MultiMastAirDensitySchema(dy.Schema):
    """Schema for multi-mast air density data.

    mast_name | temperature | pressure | ground_air_density | reference_height
    """

    mast_name = dy.String(nullable=False)
    temperature = dy.Float64(nullable=True)
    pressure = dy.Float64(nullable=True)
    ground_air_density = dy.Float64(nullable=False)
    reference_height = dy.Float64(nullable=False)
