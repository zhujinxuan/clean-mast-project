"""Shared pure calculations for reporting capabilities.

# LOGIC-PRESERVATION: Functions exported here are ported from
# assessment/shared/utils/ with no behavioural changes.
"""

from cleanmast.subdomains.reporting.compute.air_density import (
    GAS_CONSTANT_DRY_AIR,
    STANDARD_AIR_DENSITY,
    calculate_air_density,
    calculate_air_density_for_height,
    convert_to_standard_air_density,
)
from cleanmast.subdomains.reporting.compute.merge import merge_paragraphs

__all__ = [
    "GAS_CONSTANT_DRY_AIR",
    "STANDARD_AIR_DENSITY",
    "calculate_air_density",
    "calculate_air_density_for_height",
    "convert_to_standard_air_density",
    "merge_paragraphs",
]
