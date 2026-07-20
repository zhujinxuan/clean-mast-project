"""Flat report configuration models for the reporting pipeline.

Ported from assessment's domain/value_objects/flat_report_config.py and
flat_subsection_config.py. Models are frozen Pydantic BaseModel subclasses.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cleanmast.shared.timeseries.time_range import TimeRange
from cleanmast.shared.timeseries.time_series_source import (
    TimeSeriesSource,
)

SubsectionType = Literal[
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
    "timeseries",
    "fifty_year_max_wind",
]

_INDEX_PATTERN = re.compile(r"^\d+(\.\d+)*$")


# LOGIC-PRESERVATION: Ported from assessment domain/value_objects/dataset_config.py — same fields, same validators, added frozen=True
class DatasetConfig(BaseModel):
    """Configuration for a single dataset in the report.

    Attributes:
        name: Dataset identifier.
        masts: List of mast references within this dataset.
        mesos: Optional list of mesoscale data references.
        note: Optional note or description.
        analysis_windows: Analysis time windows (measurement year / representative year).
            Every mast in ``masts`` must be covered by exactly one window.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    masts: list[MastRef] | None = None
    mesos: list[MesoRef] | None = None
    analysis_windows: list[AnalysisWindow]
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

    @model_validator(mode="after")
    def validate_analysis_window_coverage(self) -> "DatasetConfig":
        """Validate analysis window coverage: every mast in exactly one window."""
        if not self.analysis_windows:
            raise ValueError("analysis_windows must contain at least one window")

        mast_names = [m.name for m in self.masts] if self.masts else []

        covered: dict[str, int] = {}
        for aw in self.analysis_windows:
            for target in aw.target_masts:
                covered[target] = covered.get(target, 0) + 1

        for target, count in covered.items():
            if count > 1:
                raise ValueError(
                    f"Mast '{target}' in dataset '{self.name}' is covered by "
                    f"multiple analysis windows"
                )

        for target in covered:
            if target not in mast_names:
                raise ValueError(
                    f"Analysis window targets mast '{target}' which is not in "
                    f"dataset '{self.name}' masts"
                )

        for mast_name in mast_names:
            if mast_name not in covered:
                raise ValueError(
                    f"Mast '{mast_name}' in dataset '{self.name}' is not covered "
                    f"by any analysis window"
                )

        return self


class ExtremeWindGustFactor(BaseModel):
    """Gust factor for deriving 3s extremes from 10min wind speeds at a height.

    Attributes:
        height: Measurement height in meters.
        gust_factor: Ratio of 3s gust to 10min sustained wind speed at this height.
    """

    model_config = ConfigDict(frozen=True)

    height: float
    gust_factor: float = 1.4


# LOGIC-PRESERVATION: Ported from assessment domain/value_objects/dataset_config.py — same fields, same validators, added frozen=True
class MastRef(BaseModel):
    """Reference to a mast within a dataset.

    Attributes:
        name: Mast identifier (e.g., "M6002").
        air_density: Air density value in kg/m³; must be strictly positive.
        input: Time series data source for this mast.
        turbulence_heights: Heights with both WS avg and WS sd sensors in turbine range.
        extreme_wind_10min_heights: Heights (120–160m) with WindSpeed avg sensors for
            10min-averaged extreme wind analysis. Required; empty list means no heights
            are configured (mast is skipped).
        extreme_wind_3s_heights: Heights (120–160m) with WindSpeed max sensors for
            3s gust extreme wind analysis. Required; empty list means no heights
            are configured.
        extreme_wind_gust_factors: Gust-factor table keyed by height, used to derive
            3s extremes from 10min data when a height lacks a max sensor. Required;
            empty list means no gust factors configured.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    air_density: float = Field(gt=0)
    input: TimeSeriesSource
    turbulence_heights: list[float] = Field(default_factory=list)
    extreme_wind_10min_heights: list[float]
    extreme_wind_3s_heights: list[float]
    extreme_wind_gust_factors: list[ExtremeWindGustFactor]


class MesoRef(BaseModel):
    """Reference to a mesoscale data source for specific masts.

    Attributes:
        input: Time series data source for the mesoscale data (e.g., ERA5).
        target_masts: List of mast names this meso source applies to.
        meso_name: Name of the mesoscale source (e.g. "ERA5Lidar").
    """

    model_config = ConfigDict(frozen=True)

    input: TimeSeriesSource
    target_masts: list[str]
    meso_name: str

    @model_validator(mode="after")
    def validate_target_masts(self) -> "MesoRef":
        """Validate target_masts list is non-empty."""
        if not self.target_masts:
            raise ValueError("target_masts must contain at least one mast name")
        return self


class AnalysisWindow(BaseModel):
    """Time window for analysis — measurement year or representative year."""
    model_config = ConfigDict(frozen=True)
    target_masts: list[str]
    time_range: TimeRange

    @model_validator(mode="after")
    def validate_target_masts(self) -> "AnalysisWindow":
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
    type: SubsectionType
    title: str | None = None
    datasets: list[str] = Field(..., min_length=1)

    @field_validator("index")
    @classmethod
    def validate_index(cls, v: str) -> str:
        if not _INDEX_PATTERN.match(v):
            raise ValueError(
                f"index must match pattern r'^\\d+(\\.\\d+)*$', got '{v}'"
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
