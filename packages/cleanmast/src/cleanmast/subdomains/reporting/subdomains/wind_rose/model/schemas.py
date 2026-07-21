"""Report schemas for wind_rose subdomain."""

import dataframely as dy


class WindRoseSchema(dy.Schema):
    """Long format: one row per month-sector-height.

    月份 | 扇区编号 | 扇区名称 | 高度 | 外推/内插 | 频率 | 风功率密度

    Example:
        month | month_name | sector | sector_name | height | interpolation_marker | frequency | wind_power_density
            1 | "1月"      |      0 | "N"         |  125.0 | "外推"               | 0.15      | 842.3
            1 | "1月"      |      1 | "NNE"       |  125.0 | "外推"               | 0.08      | 612.5

    Sectors: 0=N, 1=NNE, 2=NE, ..., 15=NNW (16 sectors)
    Months: 1-12 for January through December
    """

    month = dy.Int64(nullable=False, min=1, max=12)
    month_name = dy.String(nullable=False)
    sector = dy.Int64(nullable=False, min=0, max=15)
    sector_name = dy.String(nullable=False)
    height = dy.Float64(nullable=False)
    interpolation_marker = dy.String(nullable=True)
    frequency = dy.Float64(nullable=False)
    wind_power_density = dy.Float64(nullable=True)
    energy_frequency = dy.Float64(nullable=True)
