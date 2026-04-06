"""Assessment subdomain for wind resource analysis.

This subdomain provides domain models and services for wind resource assessment,
including analysis inputs, parameters, results, and report generation.

Public API:
    # Core Analysis Types
    AnalysisResult          # Generic container for analysis outputs
    SingleMastAnalysisInput # Input specification for single mast analysis
    AnalysisMetadata        # Metadata about analysis execution
    AnalysisParameters      # Analysis configuration parameters
    AnalysisNode            # Node in analysis dependency graph

    # Schemas (DataFrame validation)
    MonthlyWindSchema       # Monthly wind statistics schema
    MonthlyWindPowerSchema  # Monthly wind power density schema
    WindRoseSchema          # Wind rose data schema
    VerticalProfileSchema   # Vertical wind profile schema
    WindShearSchema         # Wind shear calculation schema

    # Report Configuration
    ReportConfig            # General report configuration
    RepTsReportConfig       # Representative time series report config
    MastConfig              # Mast-specific report configuration
    SingleMastMeta          # Metadata for single mast reports

    # Collections
    AtomCollection          # Collection of report atoms by mast

    # Utility Functions
    calculate_air_density   # Calculate air density from T and P
    hash_dataframe          # Create hash of DataFrame for caching
    hash_parameters         # Create hash of parameters for caching
    compute_node_id         # Compute unique node identifier
    get_height_display_name # Get display name for height level

Example:
    >>> from cleanmast.subdomains.assessment import (
    ...     AnalysisResult,
    ...     SingleMastAnalysisInput,
    ...     WindRoseSchema,
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
    AnalysisNode,
    AnalysisParameters,
    # Core analysis types
    AnalysisResult,
    # Collections
    AtomCollection,
    MastConfig,
    MonthlyWindPowerSchema,
    # Schemas
    MonthlyWindSchema,
    # Report configs
    ReportConfig,
    ReportSubsectionConfig,
    RepTsReportConfig,
    SingleMastAnalysisInput,
    SingleMastMeta,
    VerticalProfileSchema,
    WindRoseSchema,
    WindShearSchema,
    # Utilities
    calculate_air_density,
    compute_node_id,
    get_height_display_name,
    hash_dataframe,
    hash_parameters,
)

__all__ = [
    # Core analysis types
    "AnalysisResult",
    "SingleMastAnalysisInput",
    "AnalysisMetadata",
    "AnalysisParameters",
    "AnalysisNode",
    # Schemas
    "MonthlyWindSchema",
    "MonthlyWindPowerSchema",
    "WindRoseSchema",
    "VerticalProfileSchema",
    "WindShearSchema",
    # Report configs
    "ReportConfig",
    "ReportSubsectionConfig",
    "RepTsReportConfig",
    "MastConfig",
    "SingleMastMeta",
    "get_height_display_name",
    # Collections
    "AtomCollection",
    # Utilities
    "calculate_air_density",
    "hash_dataframe",
    "hash_parameters",
    "compute_node_id",
    # Constants
    "FILL_TYPE_LABELS",
    "GAS_CONSTANT_DRY_AIR",
    "STANDARD_AIR_DENSITY",
]
