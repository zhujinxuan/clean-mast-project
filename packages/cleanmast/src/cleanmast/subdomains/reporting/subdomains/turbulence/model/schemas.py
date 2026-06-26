"""Turbulence intensity schemas for the reporting domain.

LOGIC-PRESERVATION: Ported from assessment/subdomains/turbulence/value_objects/schemas.py.
Schema definitions are identical — only import paths have changed.
"""

import dataframely as dy


class TurbulenceSchema(dy.Schema):
    """Long format for turbulence intensity analysis by wind speed bin.

    风速分档 | 高度 | 外推/内插 | 平均湍流强度 | 湍流强度标准差 | 代表湍流强度 | IEC类别

    Example:
        wind_speed_bin | height | interpolation_marker | mean_ti | std_ti | representative_ti | iec_category | count
                   3   |  125.0 | "外推"               | 0.18    | 0.03   | 0.216             | "B"          | 42
                   5   |  125.0 | None                 | 0.15    | 0.02   | 0.176             | "B"          | 42
                   8   |  125.0 | None                 | 0.12    | 0.02   | 0.146             | "A"          | 42

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
    count = dy.Int64(nullable=False, min=0)


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


__all__ = ["TurbulenceSchema", "TurbulenceSectorSchema"]
