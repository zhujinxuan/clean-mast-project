"""Extreme wind schemas for reporting domain.

# LOGIC-PRESERVATION: Ported from assessment extreme_wind value_objects/schemas.py.
All schema definitions preserved exactly.
"""

import dataframely as dy


class FiftyYearMaxWindResultSchema(dy.Schema):
    """五十年一遇最大风速结果表。

    高度 | 外推/内插 | 风速类型 | 计算方法 | 最大风速 | 标准空气密度风速 | 观测最大值
    """

    height = dy.Float64(nullable=False)
    interpolation_marker = dy.String(nullable=True)
    wind_speed_type = dy.String(nullable=False)
    method = dy.String(nullable=False)
    max_wind_speed = dy.Float64(nullable=False)
    standard_density_wind_speed = dy.Float64(nullable=False)
    observed_max = dy.Float64(nullable=True)


class FiftyYearMaxWindMethod1DetailSchema(dy.Schema):
    """五十年一遇最大风速方法一详细结果表。

    高度 | 外推/内插 | 风速类型 | 计算方法 | 最大风速 | 标准空气密度风速 | 平均风速 | 空气密度
    """

    height = dy.Float64(nullable=False)
    interpolation_marker = dy.String(nullable=True)
    wind_speed_type = dy.String(nullable=False)
    method = dy.String(nullable=False)
    max_wind_speed = dy.Float64(nullable=False)
    standard_density_wind_speed = dy.Float64(nullable=False)
    average_wind_speed = dy.Float64(nullable=False)
    air_density = dy.Float64(nullable=False)


class GumbelParameterSchema(dy.Schema):
    """耿贝尔分布参数表。

    高度 | 风速类型 | 位置参数 mu | 尺度参数 beta | 样本数量 | 样本均值 | 样本标准差 | 样本数据
    """

    height = dy.Float64(nullable=False)
    wind_speed_type = dy.String(nullable=False)
    mu = dy.Float64(nullable=False)
    beta = dy.Float64(nullable=False)
    sample_count = dy.Int64(nullable=False)
    sample_mean = dy.Float64(nullable=False)
    sample_std = dy.Float64(nullable=False)
    sample_data = dy.List(dy.Float64(), nullable=True)


class FiftyYearMaxWindComparisonSchema(dy.Schema):
    """五十年一遇最大风速多方法对比表。

    高度 | 方法1 | 方法2 | 方法3 | 保守估计 | 风速类型
    """

    height = dy.Float64(nullable=False)
    method1 = dy.Float64(nullable=False)
    method2 = dy.Float64(nullable=False)
    method3 = dy.Float64(nullable=False)
    conservative_max = dy.Float64(nullable=False)
    wind_speed_type = dy.String(nullable=False)


class IECWindClassSchema(dy.Schema):
    """IEC 风等级分类表。

    风等级 | 高度 | 持续风速阈值 | 极端风速阈值 | 保守持续风速 | 保守极端风速
    """

    wind_class = dy.String(nullable=False)
    height = dy.Float64(nullable=True)
    sustained_threshold = dy.Float64(nullable=False)
    extreme_threshold = dy.Float64(nullable=False)
    conservative_sustained = dy.Float64(nullable=True)
    conservative_extreme = dy.Float64(nullable=True)


class SiteDeterminationSchema(dy.Schema):
    """场址级跨塔判定表。

    高度 | 跨塔最大保守持续风速 | 跨塔最大保守极大风速 | 判定等级
    """

    height = dy.Float64(nullable=False)
    cross_mast_max_sustained = dy.Float64(nullable=False)
    cross_mast_max_extreme = dy.Float64(nullable=False)
    wind_class = dy.String(nullable=False)


class SiteConclusionSchema(dy.Schema):
    """场址级结论句表 — text 一行一句。"""

    text = dy.String(nullable=False)


class IECStandardsSchema(dy.Schema):
    """Schema for IEC wind class standards.

    iec_class | vref | ve50
    """

    iec_class = dy.String(nullable=False)
    vref = dy.Float64(nullable=False)
    ve50 = dy.Float64(nullable=False)


__all__ = [
    "FiftyYearMaxWindResultSchema",
    "FiftyYearMaxWindMethod1DetailSchema",
    "GumbelParameterSchema",
    "FiftyYearMaxWindComparisonSchema",
    "IECWindClassSchema",
    "IECStandardsSchema",
    "SiteDeterminationSchema",
    "SiteConclusionSchema",
]
