"""Report schemas for representative year calibration analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓ | Schema Validation ✓
"""

import dataframely as dy


class MultiMastRepYearCalibrationSchema(dy.Schema):
    """Schema for multi-mast representative year calibration data."""

    year_range = dy.String(nullable=False)
    mast_name = dy.String(nullable=False)
    era5_name = dy.String(nullable=False)
    climatology_mean_ws = dy.Float64(nullable=False)
    rep_year_mean_ws = dy.Float64(nullable=False)
    anomaly_percent = dy.Float64(nullable=False)
    needs_correction = dy.Bool(nullable=False)
