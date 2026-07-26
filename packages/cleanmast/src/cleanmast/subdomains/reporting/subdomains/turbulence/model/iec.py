"""Shared IEC 61400-1 reference turbulence intensity helpers.

Lives in the model layer so model atoms can import it without creating
a model→compute dependency (pipeline rule: compute builds on model, never the reverse).
"""

IEC_CATEGORIES: dict[str, float] = {
    "A+": 0.18,
    "A": 0.16,
    "B": 0.14,
    "C": 0.12,
}
"""IEC 61400-1 ed. 4 reference turbulence intensity I_ref per category."""


def compute_iec_ti(wind_speed: float, i_ref: float) -> float | None:
    """Compute IEC reference turbulence intensity.

    TI_IEC = I_ref * (0.75 + 5.6/V)
    Returns None for wind_speed ≤ 0.
    """
    if wind_speed <= 0:
        return None

    return i_ref * (0.75 + 5.6 / wind_speed)
