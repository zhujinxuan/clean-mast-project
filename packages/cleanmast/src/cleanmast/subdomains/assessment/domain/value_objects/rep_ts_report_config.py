"""Report configuration models.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-vo-001-value-objects
Compliance: Subdomain layout ✓ | Value Object ✓
"""

from __future__ import annotations

from pathlib import Path

import tomli
from pydantic import BaseModel, Field, field_validator, model_validator

from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)


class MastConfig(BaseModel):
    """Configuration for a single mast in the report."""
    
    name: str
    air_density: float
    input: TimeSeriesSource  # Reuse existing type!


class ReportSubsectionsConfig(BaseModel):
    """Configuration for report subsections.
    
    Controls which analysis sections are included in the report.
    All subsections default to True for backward compatibility.
    """
    
    wind_rose: bool = True
    vertical_profile: bool = True
    wind_frequency: bool = True
    weibull: bool = True
    turbulence: bool = True
    temporal: bool = True
    fifty_year_max_wind: bool = True
    air_density: bool = True
    representative_year_calibration: bool = True


LEAF_SUBSECTION_TYPES = frozenset([
    "wind_rose",
    "vertical_profile",
    "wind_frequency",
    "weibull",
    "turbulence",
    "temporal",
    "air_density",
    "representative_year_calibration",
    "iec_standards",
    "fifty_year_method1",
    "fifty_year_method2",
    "fifty_year_method3",
    "fifty_year_summary",
])
CONTAINER_SUBSECTION_TYPES = frozenset(["timeseries", "fifty_year_max_wind"])
VALID_SUBSECTION_TYPES = LEAF_SUBSECTION_TYPES | CONTAINER_SUBSECTION_TYPES


def _check_subsections_depth(config: SubsectionConfig, seen: set[int] | None = None, depth: int = 0) -> None:
    """Validate subsection nesting depth and detect circular references.
    
    Recursively traverses the subsection tree to ensure there are no circular
    references and that nesting does not exceed the maximum allowed depth.
    
    Args:
        config: The subsection configuration to validate.
        seen: Set of object ids already visited in the current path.
        depth: Current nesting depth.
    
    Raises:
        ValueError: If a circular reference is detected or depth exceeds 10.
    """
    if seen is None:
        seen = set()
    if id(config) in seen:
        raise ValueError("Circular reference detected in subsection nesting")
    if depth > 10:
        raise ValueError("Subsection nesting exceeds maximum depth of 10")
    seen.add(id(config))
    if config.subsections:
        for sub in config.subsections:
            _check_subsections_depth(sub, seen.copy(), depth + 1)


class SubsectionConfig(BaseModel):
    """Configuration for a single report subsection.
    
    Defines a subsection with its type and optional custom title.
    Supports recursive nesting of subsections and per-subsection masts.
    """
    
    type: str
    title: str | None = None
    masts: list[MastConfig] | None = None
    subsections: list["SubsectionConfig"] | None = None
    
    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_SUBSECTION_TYPES:
            valid_types = ", ".join(sorted(VALID_SUBSECTION_TYPES))
            raise ValueError(f"Invalid subsection type '{v}'. Must be one of: {valid_types}")
        return v
    
    @model_validator(mode="after")
    def validate_structure(self) -> "SubsectionConfig":
        if self.type == "timeseries":
            if not self.masts:
                raise ValueError("Timeseries subsection must have at least one mast in 'masts'")
            if not self.subsections:
                raise ValueError("Timeseries subsection must have at least one nested subsection in 'subsections'")
        elif self.type == "fifty_year_max_wind":
            if not self.masts:
                raise ValueError("Fifty year max wind subsection must have at least one mast in 'masts'")
            if self.subsections:
                raise ValueError("Fifty year max wind subsection must not have 'subsections'")
        elif self.type in LEAF_SUBSECTION_TYPES:
            if self.masts:
                raise ValueError(f"Leaf subsection '{self.type}' must not have 'masts'")
            if self.subsections:
                raise ValueError(f"Leaf subsection '{self.type}' must not have 'subsections'")
        _check_subsections_depth(self)
        return self


class DocumentSectionConfig(BaseModel):
    """Configuration for a document section.

    Defines a section within the report with its type, title, and subsections.
    Currently only supports 'timeseries' type.
    """

    type: str = "timeseries"
    title: str | None = None
    subsections: list[SubsectionConfig] = Field(default_factory=list)


class DocumentConfig(BaseModel):
    """Configuration for the document structure.

    Defines the overall document structure containing multiple sections.
    Each section defines a part of the report with its own configuration.
    """

    sections: list[DocumentSectionConfig] = Field(default_factory=list)


class RepTsReportConfig(BaseModel):
    """Configuration for rep-ts report command."""
    
    document: DocumentConfig = Field(default_factory=DocumentConfig)
    
    @classmethod
    def from_toml(cls, path: Path) -> "RepTsReportConfig":
        """Load config from TOML file.
        
        Expected TOML format:
        [[document.section]]
        type = "timeseries"
        title = "Wind Speed Analysis"
        
        [[document.section.subsections]]
        type = "monthly_wind"
        title = "Monthly Wind Speed"
        
        [[document.section.subsections.masts]]
        name = "M6002"
        air_density = 1.225
        input.data = "./data.parquet"
        """
        with open(path, "rb") as f:
            data = tomli.load(f)
        
        def _parse_subsection(sub_data: dict) -> SubsectionConfig:
            masts_data = sub_data.pop("masts", [])
            masts = [MastConfig(**m) for m in masts_data] if masts_data else None
            nested = sub_data.pop("subsections", [])
            subsections = [_parse_subsection(s) for s in nested] if nested else None
            return SubsectionConfig(masts=masts, subsections=subsections, **sub_data)
        
        # Parse document sections from [[document.section]]
        document_data = data.get("document", {})
        sections_data = document_data.get("section", [])
        sections = []
        for section in sections_data:
            subsections_data = section.pop("subsections", [])
            subsections = [_parse_subsection(s) for s in subsections_data]
            sections.append(DocumentSectionConfig(subsections=subsections, **section))
        
        document = DocumentConfig(sections=sections)
        
        return cls(document=document)
