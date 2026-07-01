"""Report schemas for representative year calibration analysis.

Compliance: Subdomain layout | Value Object | Schema Validation
"""

import dataframely as dy


class RepYearSummarySchema(dy.Schema):
    """Schema for multi-mast representative year calibration summary."""

    year_range = dy.String(nullable=False)
    mast_name = dy.String(nullable=False)
    meso_name = dy.String(nullable=False)
    climatology_mean_ws = dy.Float64(nullable=False)
    rep_year_mean_ws = dy.Float64(nullable=False)
    anomaly_percent = dy.Float64(nullable=False)
    needs_correction = dy.Bool(nullable=False)


class RepYearSectorSchema(dy.Schema):
    """Schema for per-mast 16-sector calibration statistics."""

    sector = dy.String(nullable=False)
    sector_index = dy.Int32(nullable=False)
    climatology_mean = dy.Float64(nullable=True)
    rep_year_mean = dy.Float64(nullable=True)
    meso_difference = dy.Float64(nullable=True)
    slope = dy.Float64(nullable=True)
    intercept = dy.Float64(nullable=True)
    adjustment = dy.Float64(nullable=True)
    data_points = dy.Int32(nullable=True)

