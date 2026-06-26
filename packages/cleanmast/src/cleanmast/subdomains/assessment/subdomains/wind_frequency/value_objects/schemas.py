"""Wind frequency analysis result schemas in long format.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓ | Schema Validation ✓
"""

import dataframely as dy


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


__all__ = ["WindFrequencySchema"]
