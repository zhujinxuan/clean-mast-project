"""Shared constants for the wind_temporal capability.

Lives in the model layer so both model/ atoms can import it
(pipeline rule: compute builds on model, never the reverse).
"""

MONTH_NAMES: dict[int, str] = {
    1: "1月",
    2: "2月",
    3: "3月",
    4: "4月",
    5: "5月",
    6: "6月",
    7: "7月",
    8: "8月",
    9: "9月",
    10: "10月",
    11: "11月",
    12: "12月",
}
