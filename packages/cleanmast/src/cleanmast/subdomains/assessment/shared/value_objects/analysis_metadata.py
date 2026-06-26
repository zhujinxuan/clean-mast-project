"""AnalysisMetadata Value Object."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AnalysisMetadata:
    """Metadata for analysis results."""
    mast_name: str        # Mast identifier
    time_range: str       # Time period analyzed (e.g., "2023-01-01 to 2023-12-31")
    created_at: datetime  # When analysis was performed
