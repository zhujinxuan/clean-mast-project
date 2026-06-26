from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AnalysisMetadata:
    mast_name: str
    time_range: str
    created_at: datetime
