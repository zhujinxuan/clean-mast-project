"""Assessment subdomain for wind resource analysis.

This subdomain provides domain models and services for wind resource assessment,
including analysis inputs, parameters, results, and report generation.

Public API:
    # Core Analysis Types
    AnalysisResult          # Generic container for analysis outputs
    SingleMastAnalysisInput # Input specification for single mast analysis
    AnalysisMetadata        # Metadata about analysis execution
    AnalysisParameters      # Analysis configuration parameters

    # Report Configuration
    SingleMastMeta          # Metadata for single mast reports

    # Collections
    AtomCollection          # Collection of report atoms by mast

    # Utility Functions
    calculate_air_density   # Calculate air density from T and P
    get_height_display_name # Get display name for height level

Example:
    >>> from cleanmast.subdomains.assessment import (
    ...     AnalysisResult,
    ...     SingleMastAnalysisInput,
    ... )
    >>> # Use types for wind resource assessment
"""

# Re-export from domain layer
from cleanmast.subdomains.assessment.domain import (
    # Constants
    FILL_TYPE_LABELS,
    GAS_CONSTANT_DRY_AIR,
    STANDARD_AIR_DENSITY,
    AnalysisMetadata,
    AnalysisParameters,
    # Core analysis types
    AnalysisResult,
    # Collections
    AtomCollection,
    SingleMastAnalysisInput,
    SingleMastMeta,
    # Utilities
    calculate_air_density,
    get_height_display_name,
)

__all__ = [
    # Core analysis types
    "AnalysisResult",
    "SingleMastAnalysisInput",
    "AnalysisMetadata",
    "AnalysisParameters",
    "SingleMastMeta",
    "get_height_display_name",
    # Collections
    "AtomCollection",
    # Utilities
    "calculate_air_density",
    # Constants
    "FILL_TYPE_LABELS",
    "GAS_CONSTANT_DRY_AIR",
    "STANDARD_AIR_DENSITY",
]
