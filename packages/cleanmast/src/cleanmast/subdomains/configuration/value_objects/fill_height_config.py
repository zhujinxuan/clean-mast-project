"""Fill heights configuration models and validation.

ADR-GUARDRAILS: structure-001-subdomain-layout, config-001-config-structs
Compliance: Subdomain layout ✓ | Value Object ✓ | Validation ✓
Description: Pydantic models for the fill-heights TOML configuration
"""

from typing import Literal

import tomli
from pydantic import BaseModel, field_validator, model_validator

from cleanmast.subdomains.dataingestion.value_objects.sensor_column import SensorColumn
from cleanmast.subdomains.dataingestion.value_objects.time_series_source import (
    TimeSeriesSource,
)


class HeightReference(BaseModel):
    """Reference sensor configuration for height filling operations."""

    sensor: SensorColumn
    weight: float = 1.0

    @field_validator("weight")
    @classmethod
    def validate_weight_positive(cls, v: float) -> float:
        """Validate weight is a positive value."""
        if v <= 0:
            raise ValueError(f"weight must be positive, got: {v}")
        return v


class WindSpeedHeightConfig(BaseModel):
    """Configuration for filling wind speed at a target height."""

    target_sensor: SensorColumn
    references: list[HeightReference]
    shear: float

    @property
    def target_column(self) -> str:
        """Return the target column name from target_sensor."""
        return self.target_sensor.column_name

    @property
    def target_height(self) -> float:
        """Return the target height from target_sensor."""
        return self.target_sensor.height

    @field_validator("target_sensor")
    @classmethod
    def validate_target_sensor_type(cls, v: SensorColumn) -> SensorColumn:
        """Validate target_sensor has correct sensor_type for wind speed."""
        if v.sensor_type != "WindSpeed":
            raise ValueError(
                f"target_sensor.sensor_type must be 'WindSpeed', got: {v.sensor_type}"
            )
        return v

    @model_validator(mode="after")
    def validate_reference_count_matches_method(self) -> "WindSpeedHeightConfig":
        """Ensure reference count matches interpolation/extrapolation method."""
        method = self._extract_method()
        ref_count = len(self.references)

        if method == "interpolated" and ref_count != 2:
            raise ValueError(
                f"Interpolation requires exactly 2 references, got {ref_count}"
            )
        if method == "extrapolated" and ref_count != 1:
            raise ValueError(
                f"Extrapolation requires exactly 1 reference, got {ref_count}"
            )

        return self

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "WindSpeedHeightConfig":
        """Ensure interpolation weights sum to 1.0 (±0.001 tolerance)."""
        method = self._extract_method()

        if method == "interpolated":
            total_weight = sum(r.weight for r in self.references)
            if abs(total_weight - 1.0) > 0.001:
                raise ValueError(
                    f"Interpolation weights must sum to 1.0 (±0.001), got {total_weight}"
                )

        return self

    @model_validator(mode="after")
    def validate_height_consistency(self) -> "WindSpeedHeightConfig":
        """Ensure target height is consistent with interpolation/extrapolation method."""
        method = self._extract_method()
        target_height = self.target_height
        ref_heights = sorted([r.sensor.height for r in self.references])

        if method == "interpolated":
            if len(ref_heights) == 2:
                if not (ref_heights[0] < target_height < ref_heights[1]):
                    raise ValueError(
                        f"Interpolation target height {target_height}m must be "
                        f"between reference heights [{ref_heights[0]}m, {ref_heights[1]}m]"
                    )
        elif method == "extrapolated":
            if ref_heights and target_height <= ref_heights[0]:
                raise ValueError(
                    f"Extrapolation target height {target_height}m must be "
                    f"above reference height {ref_heights[0]}m"
                )

        return self

    def _extract_method(self) -> Literal["interpolated", "extrapolated"]:
        """Extract method (interpolated/extrapolated) from target_column."""
        if ":interpolated" in self.target_column:
            return "interpolated"
        elif ":extrapolated" in self.target_column:
            return "extrapolated"
        else:
            raise ValueError(f"Cannot determine method from: {self.target_column}")


class WindDirectionHeightConfig(BaseModel):
    """Configuration for filling wind direction at a target height."""

    target_sensor: SensorColumn
    references: list[HeightReference]
    deg_diff_per_m: float

    @property
    def target_column(self) -> str:
        """Return the target column name from target_sensor."""
        return self.target_sensor.column_name

    @property
    def target_height(self) -> float:
        """Return the target height from target_sensor."""
        return self.target_sensor.height

    @field_validator("target_sensor")
    @classmethod
    def validate_target_sensor_type(cls, v: SensorColumn) -> SensorColumn:
        """Validate target_sensor has correct sensor_type for wind direction."""
        if v.sensor_type != "WindDirection":
            raise ValueError(
                f"target_sensor.sensor_type must be 'WindDirection', got: {v.sensor_type}"
            )
        return v

    @model_validator(mode="after")
    def validate_reference_count_matches_method(self) -> "WindDirectionHeightConfig":
        """Ensure reference count matches interpolation/extrapolation method."""
        method = self._extract_method()
        ref_count = len(self.references)

        if method == "interpolated" and ref_count != 2:
            raise ValueError(
                f"Interpolation requires exactly 2 references, got {ref_count}"
            )
        if method == "extrapolated" and ref_count != 1:
            raise ValueError(
                f"Extrapolation requires exactly 1 reference, got {ref_count}"
            )

        return self

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "WindDirectionHeightConfig":
        """Ensure interpolation weights sum to 1.0 (±0.001 tolerance)."""
        method = self._extract_method()

        if method == "interpolated":
            total_weight = sum(r.weight for r in self.references)
            if abs(total_weight - 1.0) > 0.001:
                raise ValueError(
                    f"Interpolation weights must sum to 1.0 (±0.001), got {total_weight}"
                )

        return self

    @model_validator(mode="after")
    def validate_height_consistency(self) -> "WindDirectionHeightConfig":
        """Ensure target height is consistent with interpolation/extrapolation method."""
        method = self._extract_method()
        target_height = self.target_height
        ref_heights = sorted([r.sensor.height for r in self.references])

        if method == "interpolated":
            if len(ref_heights) == 2:
                if not (ref_heights[0] < target_height < ref_heights[1]):
                    raise ValueError(
                        f"Interpolation target height {target_height}m must be "
                        f"between reference heights [{ref_heights[0]}m, {ref_heights[1]}m]"
                    )
        elif method == "extrapolated":
            if ref_heights and target_height <= ref_heights[0]:
                raise ValueError(
                    f"Extrapolation target height {target_height}m must be "
                    f"above reference height {ref_heights[0]}m"
                )

        return self

    def _extract_method(self) -> Literal["interpolated", "extrapolated"]:
        """Extract method (interpolated/extrapolated) from target_column."""
        if ":interpolated" in self.target_column:
            return "interpolated"
        elif ":extrapolated" in self.target_column:
            return "extrapolated"
        else:
            raise ValueError(f"Cannot determine method from: {self.target_column}")


class MastFillConfig(BaseModel):
    """Complete mast configuration for height filling operations."""

    name: str
    input: TimeSeriesSource
    output: TimeSeriesSource
    windspeed: list[WindSpeedHeightConfig]
    winddirection: list[WindDirectionHeightConfig]

    @model_validator(mode="after")
    def validate_no_duplicate_targets(self) -> "MastFillConfig":
        """Ensure no duplicate target_column values across all heights."""
        all_targets: list[str] = []

        for ws_config in self.windspeed:
            if ws_config.target_column in all_targets:
                raise ValueError(
                    f"Duplicate target_column: {ws_config.target_column}"
                )
            all_targets.append(ws_config.target_column)

        for wd_config in self.winddirection:
            if wd_config.target_column in all_targets:
                raise ValueError(
                    f"Duplicate target_column: {wd_config.target_column}"
                )
            all_targets.append(wd_config.target_column)

        return self

    @model_validator(mode="after")
    def validate_no_circular_references(self) -> "MastFillConfig":
        """Ensure target columns don't appear in any source_column (circular ref)."""
        all_targets = set(
            ws.target_column for ws in self.windspeed
        ) | set(
            wd.target_column for wd in self.winddirection
        )

        for ws_config in self.windspeed:
            for ref in ws_config.references:
                if ref.sensor.column_name in all_targets:
                    raise ValueError(
                        f"Circular reference: {ref.sensor.column_name} is both a "
                        f"target and a source reference"
                    )

        for wd_config in self.winddirection:
            for ref in wd_config.references:
                if ref.sensor.column_name in all_targets:
                    raise ValueError(
                        f"Circular reference: {ref.sensor.column_name} is both a "
                        f"target and a source reference"
                    )

        return self


class FillHeightsConfiguration(BaseModel):
    """Top-level configuration for fill heights operation."""

    strategy: str = "default"
    masts: list[MastFillConfig]

    @model_validator(mode="after")
    def validate_mast_names_unique(self) -> "FillHeightsConfiguration":
        """Ensure all mast names are unique within the configuration."""
        names = [mast.name for mast in self.masts]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate mast names found in configuration")
        return self


def load_fill_heights_config(config_path: str) -> FillHeightsConfiguration:
    """Load fill heights configuration from TOML file."""
    with open(config_path, "rb") as f:
        data = tomli.load(f)

    return FillHeightsConfiguration(**data)
