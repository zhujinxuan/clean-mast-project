"""Shared constants for the wind_frequency capability.

Lives in the model layer so both compute/ and model/ atoms can import it
(pipeline rule: compute builds on model, never the reverse).
"""

PRODUCTIVE_RANGE: tuple[float, float] = (3.0, 25.0)
"""Productive wind speed range in m/s (cut-in to cut-out display bounds)."""
