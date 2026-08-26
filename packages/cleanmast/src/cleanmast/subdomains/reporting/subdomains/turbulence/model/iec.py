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


def classify_iec_category(
    representative_ti: float | None,
    wind_speed: float,
) -> str:
    """Classify IEC turbulence category by band membership.

    Compares representative TI against the IEC reference TI curves for
    categories A, B, C at the given wind speed. The band between two curves
    takes the higher category: above the C curve ⇒ B, above the B curve ⇒ A,
    above the A curve ⇒ A+. This matches the IEC band chart and the per-bin
    tables — never inline a second threshold chain in atoms.
    Defaults to "C" for None or zero wind.
    """
    if representative_ti is None or wind_speed <= 0:
        return "C"

    ti_a = compute_iec_ti(wind_speed, IEC_CATEGORIES["A"])
    ti_b = compute_iec_ti(wind_speed, IEC_CATEGORIES["B"])
    ti_c = compute_iec_ti(wind_speed, IEC_CATEGORIES["C"])

    if ti_a is not None and representative_ti > ti_a:
        return "A+"
    if ti_b is not None and representative_ti > ti_b:
        return "A"
    if ti_c is not None and representative_ti > ti_c:
        return "B"
    return "C"
