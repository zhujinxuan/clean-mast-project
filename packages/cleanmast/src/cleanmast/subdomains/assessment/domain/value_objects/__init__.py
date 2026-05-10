"""Value objects for the assessment subdomain.

These value objects encapsulate analysis inputs, parameters, results,
and metadata for wind resource assessment calculations.
"""

from .air_density import calculate_air_density
from .analysis_input import SingleMastAnalysisInput
from .analysis_metadata import AnalysisMetadata
from .analysis_node import AnalysisNode
from .analysis_parameters import AnalysisParameters
from .analysis_result import AnalysisResult
from .collections import AtomCollection
from .dataset_config import DatasetConfig, MastRef
from .hash_utils import compute_node_id, hash_dataframe, hash_parameters
from .rep_ts_report_config import (
    CONTAINER_SUBSECTION_TYPES,
    LEAF_SUBSECTION_TYPES,
    VALID_SUBSECTION_TYPES,
    DocumentConfig,
    DocumentSectionConfig,
    MastConfig,
    RepTsReportConfig,
    SubsectionConfig,
)
from .report_config import ReportConfig, ReportSubsectionConfig
from .report_meta import (
    FILL_TYPE_LABELS,
    GAS_CONSTANT_DRY_AIR,
    STANDARD_AIR_DENSITY,
    _find_pressure_column,
    _find_temperature_column,
    _normalize_pressure,
    _normalize_temperature,
    detect_interpolation_marker,
)
from .schemas import (
    MonthlyWindPowerSchema,
    MonthlyWindSchema,
    VerticalProfileSchema,
    WindRoseSchema,
    WindShearSchema,
)
from .single_mast.report_meta import SingleMastMeta, get_height_display_name
from .single_mast.schemas import (
    MonthlyWindPowerSchema as SingleMastMonthlyWindPowerSchema,
)
from .single_mast.schemas import (
    MonthlyWindSchema as SingleMastMonthlyWindSchema,
)
from .single_mast.schemas import (
    WindRoseSchema as SingleMastWindRoseSchema,
)

__all__ = [
    # Core value objects
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
    # Single mast schemas
    "SingleMastMonthlyWindPowerSchema",
    "SingleMastMonthlyWindSchema",
    "SingleMastWindRoseSchema",
    # Collections
    "AtomCollection",
    # Utilities
    "calculate_air_density",
    "hash_dataframe",
    "hash_parameters",
    "compute_node_id",
    # Dataset config
    "DatasetConfig",
    "MastRef",
    # Report configs
    "DocumentConfig",
    "DocumentSectionConfig",
    "LEAF_SUBSECTION_TYPES",
    "CONTAINER_SUBSECTION_TYPES",
    "VALID_SUBSECTION_TYPES",
    "MastConfig",
    "RepTsReportConfig",
    "SubsectionConfig",
    "ReportConfig",
    "ReportSubsectionConfig",
    # Report meta
    "SingleMastMeta",
    "get_height_display_name",
    "FILL_TYPE_LABELS",
    "GAS_CONSTANT_DRY_AIR",
    "STANDARD_AIR_DENSITY",
    "_find_temperature_column",
    "_find_pressure_column",
    "_normalize_temperature",
    "_normalize_pressure",
    "detect_interpolation_marker",
]
