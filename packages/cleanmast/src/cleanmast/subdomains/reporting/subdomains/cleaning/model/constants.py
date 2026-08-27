"""Shared constants for the cleaning-rules subsection (2.3.3).

Rule-name translations mirror the Julia report generator
(``ReportClean/ViolationAnalysisReport.jl`` ``RULE_TRANSLATIONS``) so the
Python report and the Julia ``report-clean`` output show identical Chinese
rule names.
"""

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


def translate_rule_name(rule_name: str) -> str:
    """Chinese display name for a rule (Julia ``get_chinese_rule_name``)."""
    return RULE_NAME_TRANSLATIONS.get(rule_name, rule_name)


def translate_sensor_type(sensor_type: str) -> str:
    """Chinese display name for a sensor type."""
    return SENSOR_TYPE_TRANSLATIONS.get(sensor_type, sensor_type)
