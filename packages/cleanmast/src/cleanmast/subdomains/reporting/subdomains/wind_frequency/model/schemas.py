"""Wind frequency analysis result schema in long format.

Compliance: Subdomain layout | Value Object | Schema Validation
"""

import dataframely as dy


class WindFrequencySchema(dy.Schema):
    """Long format for wind frequency distribution by speed bin.

    高度 | 外推/内插 | 分档起点 | 分档终点 | 分档中心 | 频率 | 出现小时数 | 风能频率 | 风能小时数

    Bins: 1 m/s intervals, [0,1), [1,2), ..., [27,28), [28,∞)
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


__all__ = ["WindFrequencySchema"]
