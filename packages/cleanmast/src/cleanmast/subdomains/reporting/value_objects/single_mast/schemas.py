"""Report schemas in long format for single mast analysis.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓ | Schema Validation ✓
"""

import dataframely as dy


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


class WindRoseSchema(dy.Schema):
    """Long format: one row per sector-height.
    
    扇区编号 | 扇区名称 | 高度 | 外推/内插 | 频率 | 风功率密度

    Example:
        sector | sector_name | height | interpolation_marker | frequency | wind_power_density
             0 | "N"         |  125.0 | "外推"               | 0.15      | 842.3
             1 | "NNE"       |  125.0 | "外推"               | 0.08      | 612.5

    Sectors: 0=N, 1=NNE, 2=NE, ..., 15=NNW (16 sectors, 22.5° each)
    """

    sector = dy.Int64(nullable=False, min=0, max=15)
    sector_name = dy.String(nullable=False)
    height = dy.Float64(nullable=False)
    interpolation_marker = dy.String(nullable=True)
    frequency = dy.Float64(nullable=False)
    wind_power_density = dy.Float64(nullable=True)
