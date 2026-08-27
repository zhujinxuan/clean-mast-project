"""Shared 16-direction wind-sector mapping helpers.

Used across reporting capabilities (representative_year, cleaning). Sector
semantics: 16 sectors clockwise from N, each 22.5° wide, 1-indexed.
"""

from __future__ import annotations

import math

# 16 sectors, clockwise from N
SECTOR_NAMES: list[str] = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def find_sector(angle: float) -> int:
    """Map wind direction angle (0-360) to 1-indexed sector (1=N, 2=NNE, ..., 16=NNW)."""
    return int(math.floor((angle + 11.25) / 22.5)) % 16 + 1
