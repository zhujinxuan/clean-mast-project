"""Shared constants for the cleaning-rules subsection (2.3.3).

Rule-name translations mirror the Julia report generator
(``ReportClean/ViolationAnalysisReport.jl`` ``RULE_TRANSLATIONS``) so the
Python report and the Julia ``report-clean`` output show identical Chinese
rule names.
"""

import math

from cleanmast.shared.timeseries import SensorColumn

CLEANING_RULES_INTRO = (
    "依据《风电场气象观测资料审核、插补与订正技术规范》"
    "（GB/T 37523-2019），对测风数据按下表所列规则进行检验，"
    "检验不通过的数据予以剔除。"
)

# Same mapping as the Julia RULE_TRANSLATIONS (fallback = original name).
RULE_NAME_TRANSLATIONS: dict[str, str] = {
    "Wind Speed Range": "风速范围检查",
    "Wind Direction Range": "风向范围检查",
    "High Wind Speed Layer Difference": "高风速层差检查",
    "High Wind Speed Layer Difference; 50m": "高风速层差检查(50m)",
    "Icing WS Detection": "风速结冰检测",
    "Icing WD Detection": "风向结冰检测",
    "range_check": "范围检查",
    "icing_detection": "结冰检测",
    "layer_difference": "层差检查",
    "out_of_range": "超出范围",
}

SENSOR_TYPE_TRANSLATIONS: dict[str, str] = {
    "WindSpeed": "风速",
    "WindDirection": "风向",
    "Temperature": "温度",
    "Pressure": "气压",
    "DataAvailability": "数据可用率",
}

# Same mapping intent as SENSOR_TYPE_TRANSLATIONS for the statistic slot
# of the 2.3.3 sensor labels (fallback = original stat name).
STAT_TYPE_TRANSLATIONS: dict[str, str] = {
    "avg": "均值",
    "sd": "标准差",
    "max": "极大值",
    "min": "极小值",
}

# Row-order rank of sensor types in the 2.3.3 violations table:
# 风速 → 风向 → 温度 → 气压 → 其他 (anything else sorts last).
SENSOR_TYPE_ROW_ORDER: tuple[str, ...] = (
    "WindSpeed",
    "WindDirection",
    "Temperature",
    "Pressure",
)


def format_sensor_label(sensor: SensorColumn) -> str:
    """Chinese display label for a sensor column (2.3.3 数据列 cell).

    ``{height}m {类型}({方向}, {统计})`` built purely from
    ``SensorColumn`` metadata — e.g. ``70m 风速(ESE, 均值)``. An empty
    (merged or absent) direction omits the slot: ``140m 风速(均值)``.
    """
    height = sensor.height
    height_text = str(int(height)) if height == round(height) else f"{height:g}"
    type_text = translate_sensor_type(sensor.sensor_type)
    stat_text = translate_stat_type(sensor.stat_type)
    if sensor.sensor_direction:
        return (
            f"{height_text}m {type_text}"
            f"({sensor.sensor_direction}, {stat_text})"
        )
    return f"{height_text}m {type_text}({stat_text})"


def sensor_row_sort_key(
    sensor: SensorColumn | None,
    column_name: str,
    rule_name: str,
) -> tuple[object, ...]:
    """Sort key for 2.3.3 violations rows: type rank → height → column → rule.

    Columns without matching sensor metadata (``sensor is None``) sort in
    the 其他 bucket after every known type, height treated as unbounded.
    """
    other_rank = len(SENSOR_TYPE_ROW_ORDER)
    if sensor is None:
        return (other_rank + 1, math.inf, column_name, rule_name)
    type_rank = (
        SENSOR_TYPE_ROW_ORDER.index(sensor.sensor_type)
        if sensor.sensor_type in SENSOR_TYPE_ROW_ORDER
        else other_rank
    )
    return (type_rank, sensor.height, column_name, rule_name)


def translate_rule_name(rule_name: str) -> str:
    """Chinese display name for a rule (Julia ``get_chinese_rule_name``)."""
    return RULE_NAME_TRANSLATIONS.get(rule_name, rule_name)


def translate_sensor_type(sensor_type: str) -> str:
    """Chinese display name for a sensor type."""
    return SENSOR_TYPE_TRANSLATIONS.get(sensor_type, sensor_type)


def translate_stat_type(stat_type: str) -> str:
    """Chinese display name for a statistics type (avg/sd/max/min)."""
    return STAT_TYPE_TRANSLATIONS.get(stat_type, stat_type)
