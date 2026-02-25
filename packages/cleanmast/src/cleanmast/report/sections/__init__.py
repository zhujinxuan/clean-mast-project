"""Report sections package.

Provides different section implementations for organizing
report content with various rendering strategies.
"""

from .templated import TemplatedSection, WIND_SPEED_POWER_TEMPLATE
from .wind_rose import WindRoseSection
from .representative_wind_speed import RepresentativeWindSpeedSection
from .representative_wind_power import RepresentativeWindPowerSection

__all__ = [
    "TemplatedSection",
    "WindRoseSection",
    "WIND_SPEED_POWER_TEMPLATE",
    "RepresentativeWindSpeedSection",
    "RepresentativeWindPowerSection",
]
