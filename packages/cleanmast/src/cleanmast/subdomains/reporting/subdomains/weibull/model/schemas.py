"""Weibull distribution schemas for the reporting domain."""

import dataframely as dy


class WeibullSchema(dy.Schema):
    """Schema for Weibull distribution fitting results.

    One row per height with fitted Weibull parameters and density curves.

    Example:
        height | interpolation_marker | shape_k | scale_c | mean_speed
         100.0 | None                 | 2.1     | 8.5     | 7.52
         120.0 | "外推"               | 2.3     | 9.0     | 7.98
    """

    height = dy.Float64(nullable=False)
    interpolation_marker = dy.String(nullable=True)
    shape_k = dy.Float64(nullable=False)
    scale_c = dy.Float64(nullable=False)
    mean_speed = dy.Float64(nullable=False)
    bin_centers = dy.List(dy.Float64())
    observed_density = dy.List(dy.Float64())
    fitted_density = dy.List(dy.Float64())
