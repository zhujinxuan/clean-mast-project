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
    """Long format: one row per month-sector-height.

    月份 | 扇区编号 | 扇区名称 | 高度 | 外推/内插 | 频率 | 风功率密度

    Example:
        month | month_name | sector | sector_name | height | interpolation_marker | frequency | wind_power_density
            1 | "1月"      |      0 | "N"         |  125.0 | "外推"               | 0.15      | 842.3
            1 | "1月"      |      1 | "NNE"       |  125.0 | "外推"               | 0.08      | 612.5

    Sectors: 0=N, 1=NNE, 2=NE, ..., 15=NNW (16 sectors, 22.5° each)
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


class TurbulenceSchema(dy.Schema):
    """Long format for turbulence intensity analysis by wind speed bin.

    风速分档 | 高度 | 外推/内插 | 平均湍流强度 | 湍流强度标准差 | 代表湍流强度 | IEC类别

    Example:
        wind_speed_bin | height | interpolation_marker | mean_ti | std_ti | representative_ti | iec_category
                   3   |  125.0 | "外推"               | 0.18    | 0.03   | 0.216             | "B"
                   5   |  125.0 | None                 | 0.15    | 0.02   | 0.176             | "B"
                   8   |  125.0 | None                 | 0.12    | 0.02   | 0.146             | "A"

    Note: representative_ti = mean_ti + 1.28 * std_ti (P90 TI)
    IEC categories: A+ (high), A, B, C (low) based on turbulence intensity classification
    """

    wind_speed_bin = dy.Int64(nullable=False)
    height = dy.Float64(nullable=False)
    interpolation_marker = dy.String(nullable=True)
    mean_ti = dy.Float64(nullable=False)
    std_ti = dy.Float64(nullable=False)
    representative_ti = dy.Float64(nullable=False)
    iec_category = dy.String(nullable=False)


class TurbulenceSectorSchema(dy.Schema):
    """Long format for turbulence intensity analysis by direction sector.

    扇区编号 | 扇区名称 | 高度 | 外推/内插 | 平均湍流强度 | 代表湍流强度 | IEC类别

    Example:
        sector | sector_name | height | interpolation_marker | mean_ti | representative_ti | iec_category
             0 | "N"         |  125.0 | "外推"               | 0.16    | 0.192             | "B"
             1 | "NNE"       |  125.0 | None                 | 0.18    | 0.220             | "B"
             8 | "S"         |  125.0 | None                 | 0.14    | 0.168             | "B"

    Sectors: 0=N, 1=NNE, 2=NE, ..., 15=NNW (16 sectors, 22.5° each)
    Note: representative_ti = mean_ti + 1.28 * std_ti (P90 TI)
    IEC categories: A+ (high), A, B, C (low) based on turbulence intensity classification
    """

    sector = dy.Int64(nullable=False, min=0, max=15)
    sector_name = dy.String(nullable=False)
    height = dy.Float64(nullable=False)
    interpolation_marker = dy.String(nullable=True)
    mean_ti = dy.Float64(nullable=False)
    representative_ti = dy.Float64(nullable=False)
    iec_category = dy.String(nullable=False)


class WindFrequencySchema(dy.Schema):
    """Long format for wind frequency distribution by speed bin.

    高度 | 外推/内插 | 分档起点 | 分档终点 | 分档中心 | 频率 | 出现小时数 | 风能频率 | 风能小时数

    Example:
        height | interpolation_marker | bin_start | bin_end | bin_center | frequency | occurrence_hours | power_frequency | power_hours
         100.0 | None                 |       0.0 |     1.0 |        0.5 |     0.032 |           280.32 |           0.002 |       17.52
         100.0 | None                 |       1.0 |     2.0 |        1.5 |     0.085 |           744.60 |           0.018 |      157.68
         100.0 | "外推"               |      27.0 |    28.0 |       27.5 |     0.005 |            43.80 |           0.025 |      219.00

    Bins: 1 m/s intervals, typically [0,1), [1,2), ..., [27,28), [28,∞)
    Note: occurrence_hours = frequency * 8760 (hours/year)
          power_hours = power_frequency * 8760
          P = 0.5 * ρ * v³ (wind power density)
    """

    height = dy.Float64(nullable=False)
    interpolation_marker = dy.String(nullable=True)
    bin_start = dy.Float64(nullable=False)
    bin_end = dy.Float64(nullable=False)
    bin_center = dy.Float64(nullable=False)
    frequency = dy.Float64(nullable=False, min=0, max=1)
    occurrence_hours = dy.Float64(nullable=False)
    power_frequency = dy.Float64(nullable=False, min=0, max=1)
    power_hours = dy.Float64(nullable=False)
