"""Weibull distribution schemas.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓ | Schema Validation ✓
"""

import dataframely as dy


class WeibullSchema(dy.Schema):
    """Schema for Weibull distribution fitting results.

    One row per height with fitted Weibull parameters and density curves.

    Example:
        height | interpolation_marker | shape_k | scale_c | mean_speed | bin_centers      | observed_density | fitted_density
         100.0 | None                 | 2.1     | 8.5     | 7.52       | [0.5, 1.5, 2.5]  | [0.02, 0.05]     | [0.025, 0.048]
    """

    height = dy.Float64(nullable=False)
    interpolation_marker = dy.String(nullable=True)
    shape_k = dy.Float64(nullable=False)
    scale_c = dy.Float64(nullable=False)
    mean_speed = dy.Float64(nullable=False)
    bin_centers = dy.List(dy.Float64())
    observed_density = dy.List(dy.Float64())
    fitted_density = dy.List(dy.Float64())
