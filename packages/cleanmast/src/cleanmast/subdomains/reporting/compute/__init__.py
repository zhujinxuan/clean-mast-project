"""Shared pure calculations for reporting capabilities.

# LOGIC-PRESERVATION: Functions exported here are ported from
# assessment/shared/utils/ with no behavioural changes.
"""

from cleanmast.subdomains.reporting.compute.air_density import (
    FILL_TYPE_LABELS,
    GAS_CONSTANT_DRY_AIR,
    STANDARD_AIR_DENSITY,
    calculate_air_density,
    calculate_air_density_for_height,
    convert_to_standard_air_density,
    detect_interpolation_marker,
)
from cleanmast.subdomains.reporting.compute.height_filter import select_interested_heights
from cleanmast.subdomains.reporting.compute.merge import merge_paragraphs

__all__ = [
    "GAS_CONSTANT_DRY_AIR",
    "STANDARD_AIR_DENSITY",
    "FILL_TYPE_LABELS",
    "calculate_air_density",
    "calculate_air_density_for_height",
    "convert_to_standard_air_density",
    "detect_interpolation_marker",
    "select_interested_heights",
    "merge_paragraphs",
]
