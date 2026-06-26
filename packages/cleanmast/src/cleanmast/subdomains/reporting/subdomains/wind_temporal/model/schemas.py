"""Temporal pattern schemas.

Compliance: Subdomain layout | Value Object | Schema Validation
"""

import dataframely as dy


class TemporalPatternSchema(dy.Schema):
    """Long format for temporal pattern analysis.

    timestamp | hour | month | wind_speed | wind_power | height | mean_speed | mean_power | interpolation_marker
    """

    timestamp = dy.Datetime(nullable=False)
    hour = dy.Int64(nullable=False, min=0, max=23)
    month = dy.Int64(nullable=False, min=1, max=12)
    wind_speed = dy.Float64(nullable=True)
    wind_power = dy.Float64(nullable=True)
    height = dy.Float64(nullable=False)
    mean_speed = dy.Float64(nullable=True)
    mean_power = dy.Float64(nullable=True)
    interpolation_marker = dy.String(nullable=True)


__all__ = ["TemporalPatternSchema"]
