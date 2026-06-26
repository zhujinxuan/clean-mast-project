"""Temporal pattern schemas.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓ | Schema Validation ✓
"""

import dataframely as dy


class TemporalPatternSchema(dy.Schema):
    """Long format for temporal pattern analysis.

    timestamp | hour | month | wind_speed | wind_power | height | mean_speed | mean_power | interpolation_marker

    Example:
        timestamp           | hour | month | wind_speed | wind_power | height | mean_speed | mean_power | interpolation_marker
        2024-01-01 00:00:00 |    0 |     1 |        5.2 |      156.8 |  125.0 |        6.1 |      210.5 | "外推"
        2024-01-01 01:00:00 |    1 |     1 |        5.8 |      195.2 |  125.0 |        6.1 |      210.5 | "外推"
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


class MonthlyWindSchema(dy.Schema):
    """Long format: one row per month-height combination.
    
    月份 | 高度 | 外推/内插 | 平均风速 | 最大风速 | 最小风速

    Example:
        month | height | interpolation_marker | wind_speed_mean | wind_speed_max | wind_speed_min
            1 |  125.0 | "外推"               | 5.2             | 8.1            | 2.3
            1 |  140.0 | "外推"               | 5.8             | 9.2            | 2.8
    """

    month = dy.Int64(nullable=False, min=1, max=12)
    height = dy.Float64(nullable=False)
    interpolation_marker = dy.String(nullable=True)
    wind_speed_mean = dy.Float64(nullable=False)
    wind_speed_max = dy.Float64(nullable=False)
    wind_speed_min = dy.Float64(nullable=False)


class MonthlyWindPowerSchema(dy.Schema):
    """Long format with power density.
    
    月份 | 高度 | 外推/内插 | 风功率密度 | 使用的空气密度

    Example:
        month | height | interpolation_marker | wind_power_density | air_density_used
            1 |  125.0 | "外推"               | 842.3              | 1.189
    """

    month = dy.Int64(nullable=False, min=1, max=12)
    height = dy.Float64(nullable=False)
    interpolation_marker = dy.String(nullable=True)
    wind_power_density = dy.Float64(nullable=False)
    air_density_used = dy.Float64(nullable=False)


__all__ = ["MonthlyWindPowerSchema", "MonthlyWindSchema", "TemporalPatternSchema"]
