"""Report sections service.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service Package ✓

This module provides section implementations for organizing report content.
"""

from cleanmast.subdomains.reporting.services.sections.representative_wind_power import (
    RepresentativeWindPowerSection,
)
from cleanmast.subdomains.reporting.services.sections.representative_wind_speed import (
    RepresentativeWindSpeedSection,
)
from cleanmast.subdomains.reporting.services.sections.templated import (
    TemplatedSection,
    WIND_SPEED_POWER_TEMPLATE,
)
from cleanmast.subdomains.reporting.services.sections.wind_rose import WindRoseSection

__all__ = [
    "RepresentativeWindPowerSection",
    "RepresentativeWindSpeedSection",
    "TemplatedSection",
    "WIND_SPEED_POWER_TEMPLATE",
    "WindRoseSection",
]
