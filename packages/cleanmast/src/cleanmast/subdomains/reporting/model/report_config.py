"""Flat report configuration models for the reporting pipeline.

Ported from assessment's domain/value_objects/flat_report_config.py and
flat_subsection_config.py. Models are frozen Pydantic BaseModel subclasses.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import tomli
import tomli_w
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)

if TYPE_CHECKING:
    from cleanmast.subdomains.reporting.assemble.tree_builder import SectionNode

_LEAF_SUBSECTION_TYPES = frozenset([
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
_CONTAINER_SUBSECTION_TYPES = frozenset(["timeseries", "fifty_year_max_wind"])
VALID_SUBSECTION_TYPES = _LEAF_SUBSECTION_TYPES | _CONTAINER_SUBSECTION_TYPES

_INDEX_PATTERN = re.compile(r"^\d+(\.\d+)*$")


# LOGIC-PRESERVATION: Ported from assessment domain/value_objects/dataset_config.py — same fields, same validators, added frozen=True
class DatasetConfig(BaseModel):
    """Configuration for a single dataset in the report.

    Attributes:
        name: Dataset identifier.
        masts: List of mast references within this dataset.
        mesos: Optional list of mesoscale data references.
        note: Optional note or description.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    masts: list[MastRef] | None = None
    mesos: list[MesoRef] | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_masts(self) -> "DatasetConfig":
        """Validate masts list: non-empty and no duplicate names."""
        if self.masts is not None:
            if not self.masts:
                raise ValueError("masts must contain at least one MastRef")

            names = [mast.name for mast in self.masts]
            seen = set()
            for name in names:
                if name in seen:
                    raise ValueError(
                        f"Duplicate mast name '{name}' in dataset '{self.name}'"
                    )
                seen.add(name)

        return self


# LOGIC-PRESERVATION: Ported from assessment domain/value_objects/dataset_config.py — same fields, same validators, added frozen=True
class MastRef(BaseModel):
    """Reference to a mast within a dataset.

    Attributes:
        name: Mast identifier (e.g., "M6002").
        air_density: Air density value in kg/m³; must be strictly positive.
        input: Time series data source for this mast.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    air_density: float = Field(gt=0)
    input: TimeSeriesSource


# LOGIC-PRESERVATION: Ported from assessment domain/value_objects/dataset_config.py — same fields, same validators, added frozen=True
class MesoRef(BaseModel):
    """Reference to a mesoscale data source for specific masts.

    Attributes:
        input: Time series data source for the mesoscale data (e.g., ERA5).
        target_masts: List of mast names this meso source applies to.
    """

    model_config = ConfigDict(frozen=True)

    input: TimeSeriesSource
    target_masts: list[str]

    @model_validator(mode="after")
    def validate_target_masts(self) -> "MesoRef":
        """Validate target_masts list is non-empty."""
        if not self.target_masts:
            raise ValueError("target_masts must contain at least one mast name")
        return self


class FlatSubsectionConfig(BaseModel):
    """Flat (non-recursive) configuration for a report subsection.

    Used in the redesigned report config format where hierarchy is
    represented by dot-separated indices rather than nested objects.
    """

    model_config = ConfigDict(frozen=True)

    index: str
    type: str
    title: str | None = None
    datasets: list[str]

    @field_validator("datasets")
    @classmethod
    def validate_datasets(cls, v: list[str]) -> list[str]:
        if len(v) == 0:
            raise ValueError("datasets must not be empty")
        return v

    @field_validator("index")
    @classmethod
    def validate_index(cls, v: str) -> str:
        if not _INDEX_PATTERN.match(v):
            raise ValueError(
                f"index must match pattern r'^\\d+(\\.\\d+)*$', got '{v}'"
            )
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_SUBSECTION_TYPES:
            valid_types = ", ".join(sorted(VALID_SUBSECTION_TYPES))
            raise ValueError(
                f"Invalid subsection type '{v}'. Must be one of: {valid_types}"
            )
        return v


class FlatReportConfig(BaseModel):
    """Flat (non-recursive) report configuration.

    Uses flat arrays for datasets and subsections, with hierarchy
    represented by dot-separated indices.
    """

    model_config = ConfigDict(frozen=True)

    datasets: list[DatasetConfig]
    subsections: list[FlatSubsectionConfig]

    @model_validator(mode="after")
    def validate_datasets(self) -> "FlatReportConfig":
        """Validate dataset names are unique and subsection references exist."""
        names = [ds.name for ds in self.datasets]
        seen = set()
        for name in names:
            if name in seen:
                raise ValueError(f"Duplicate dataset name '{name}' in catalog")
            seen.add(name)

        catalog = {ds.name for ds in self.datasets}
        for sub in self.subsections:
            for ds_name in sub.datasets:
                if ds_name not in catalog:
                    raise ValueError(
                        f"Subsection {sub.index} references unknown dataset '{ds_name}'"
                    )

        return self

    @property
    def tree(self) -> list[SectionNode]:
        from cleanmast.subdomains.reporting.assemble.tree_builder import build_section_tree

        return build_section_tree(self.subsections)

    @classmethod
    def from_toml(cls, path: Path) -> "FlatReportConfig":
        """Load config from TOML file."""
        with open(path, "rb") as f:
            data = tomli.load(f)
        return cls.model_validate(data)

    def to_toml(self, path: Path) -> None:
        """Serialize config to TOML file."""
        data = {
            "datasets": [ds.model_dump(exclude_none=True) for ds in self.datasets],
            "subsections": [
                sub.model_dump(exclude_none=True) for sub in self.subsections
            ],
        }
        toml_str = tomli_w.dumps(data)
        path.write_text(toml_str, encoding="utf-8")


class AtomCollection(BaseModel):
    """Minimal immutable collection of report atoms."""

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_dict(cls, data: dict[str, list[Any]]) -> "AtomCollection":
        return cls()
