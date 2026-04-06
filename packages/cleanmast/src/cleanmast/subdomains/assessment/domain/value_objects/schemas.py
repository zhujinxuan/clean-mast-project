"""Analysis result schemas in long format.

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


class VerticalProfileSchema(dy.Schema):
    """Vertical wind profile data at a single height level.

    高度 | 外推/内插标记 | 平均风速 | 风速标准差 | 风切变指数 | 拟合优度

    Formula (Power Law):
        v = v_ref * (h / h_ref)^α

    Where:
        v: wind speed at height h
        v_ref: wind speed at reference height h_ref
        α: power law exponent (alpha)

    Typical Alpha Values:
        - Smooth (water): 0.10-0.12
        - Open (grassland): 0.12-0.16
        - Rough (suburban): 0.16-0.25
        - Very rough (urban): 0.25-0.40

    Example:
        height | interpolation_marker | wind_speed_mean | wind_speed_std | alpha | r_squared
          50.0 | None                 | 5.2             | 1.8            | 0.15  | 0.98
         100.0 | "外推"               | 6.1             | 2.0            | None  | None
    """

    height = dy.Float64(nullable=False)
    interpolation_marker = dy.String(nullable=True)
    wind_speed_mean = dy.Float64(nullable=False)
    wind_speed_std = dy.Float64(nullable=False)
    alpha = dy.Float64(nullable=True)  # 幂律指数 / power law exponent
    r_squared = dy.Float64(nullable=True)  # 拟合优度 0-1 / fit quality


class WindShearSchema(dy.Schema):
    """Wind shear calculation results between two height levels.

    起始高度 | 终止高度 | 平均风切变 | 风切变标准差 | 最小风切变 | 最大风切变

    Formula (Logarithmic Profile):
        α = ln(v2/v1) / ln(h2/h1)

    Where:
        α: wind shear exponent
        v1, v2: wind speeds at heights h1 and h2
        h1, h2: lower and upper heights (h2 > h1)

    Typical Alpha Values:
        - Smooth (water): 0.10-0.12
        - Open (grassland): 0.12-0.16
        - Rough (suburban): 0.16-0.25
        - Very rough (urban): 0.25-0.40

    Example:
        from_height | to_height | alpha_mean | alpha_std | alpha_min | alpha_max
             50.0   |    100.0  | 0.15       | 0.03      | 0.08      | 0.25
    """

    from_height = dy.Float64(nullable=False)  # 起始高度 / lower height
    to_height = dy.Float64(nullable=False)  # 终止高度 / upper height
    alpha_mean = dy.Float64(nullable=False)  # 平均风切变 / mean shear
    alpha_std = dy.Float64(nullable=False)  # 风切变标准差 / std of shear
    alpha_min = dy.Float64(nullable=False)  # 最小风切变 / minimum shear
    alpha_max = dy.Float64(nullable=False)  # 最大风切变 / maximum shear
