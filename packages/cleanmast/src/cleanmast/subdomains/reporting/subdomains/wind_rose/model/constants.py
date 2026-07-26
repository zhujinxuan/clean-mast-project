"""Shared constants for the wind_rose capability.

Lives in the model layer so both compute/ and model/ atoms can import it
(pipeline rule: compute builds on model, never the reverse).
"""

SECTOR_COUNT = 16
"""Number of compass sectors in a wind rose (16 -> 22.5° each)."""

SECTOR_WIDTH = 360.0 / SECTOR_COUNT
"""Angular width of each sector in degrees."""

SECTOR_LABELS = [
    "N", "NNE", "NE", "ENE",
    "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW",
    "W", "WNW", "NW", "NNW",
]
"""Compass labels indexed by sector (length SECTOR_COUNT)."""

WIND_ROSE_COLORS = [
    "#1f77b4",
    "#d62728",
    "#2ca02c",
    "#ff7f0e",
    "#9467bd",
    "#17becf",
    "#8c564b",
    "#e377c2",
]
"""Color cycle for per-height series in wind rose charts."""
