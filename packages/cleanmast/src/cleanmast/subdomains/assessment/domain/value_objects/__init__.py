"""Value objects for the assessment subdomain.

These value objects encapsulate analysis inputs, parameters, results,
and metadata for wind resource assessment calculations.
"""

from cleanmast.subdomains.assessment.shared.collections.atom_collection import (
    AtomCollection,
)
from cleanmast.subdomains.assessment.shared.utils.air_density import (
    FILL_TYPE_LABELS,
    GAS_CONSTANT_DRY_AIR,
    STANDARD_AIR_DENSITY,
    _normalize_pressure,
    _normalize_temperature,
    calculate_air_density,
    detect_interpolation_marker,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_input import (
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_metadata import (
    AnalysisMetadata,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.assessment.shared.value_objects.analysis_result import (
    AnalysisResult,
)
from cleanmast.subdomains.assessment.shared.value_objects.single_mast.report_meta import (
    SingleMastMeta,
    get_height_display_name,
)

__all__ = [
    # Core value objects
    "AnalysisResult",
    "SingleMastAnalysisInput",
    "AnalysisMetadata",
    "AnalysisParameters",
    # Collections
    "AtomCollection",
    # Utilities
    "calculate_air_density",
    # Report meta
    "SingleMastMeta",
    "get_height_display_name",
    "FILL_TYPE_LABELS",
    "GAS_CONSTANT_DRY_AIR",
    "STANDARD_AIR_DENSITY",
    "_normalize_temperature",
    "_normalize_pressure",
    "detect_interpolation_marker",
]
