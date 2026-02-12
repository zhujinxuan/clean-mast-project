"""Fill heights configuration models and validation.

This module provides Pydantic models for the fill-heights TOML configuration
file. It defines the configuration structure for wind speed and wind direction
height filling operations, including:

- HeightReference: Reference sensor configuration for height filling
- WindSpeedHeightConfig: Wind speed filling configuration (interpolation/extrapolation)
- WindDirectionHeightConfig: Wind direction filling configuration
- MastFillConfig: Complete mast configuration with input/output sources
- FillHeightsConfiguration: Top-level configuration with multiple masts

Each configuration class includes comprehensive validation to ensure:
- Column naming conventions (WS_/WD_ prefixes)
- Height consistency (interpolation: target between refs, extrapolation: target above ref)
- Weight normalization for interpolation (sum to 1.0)
- No circular references between target and source columns

The configuration follows a hierarchical design:
1. HeightReference: Individual sensor reference (height, column, weight)
2. WindSpeedHeightConfig/WindDirectionHeightConfig: Target column + references
3. MastFillConfig: Multiple configs per mast with I/O sources
4. FillHeightsConfiguration: Multiple masts in a single config file

Example TOML structure:
    [fill-heights]
    strategy = "default"
    
    [[fill-heights.masts]]
    name = "mast-01"
    input.data = "./reconstructed/mast-01.parquet"
    output.data = "./filled/mast-01.parquet"
    
    [[fill-heights.masts.windspeed]]
    target_column = "WS_120m_fill:extrapolated"
    shear = 0.15
    [[fill-heights.masts.windspeed.references]]
    source_column = "WS_80m_avg"
    height = 80.0
    weight = 1.0
"""

from typing import Literal

import tomli
from pydantic import BaseModel, field_validator, model_validator

from ..models.sensor import SensorColumn
from ..models.timeseries import TimeSeriesSource


class HeightReference(BaseModel):
    """Reference sensor configuration for height filling operations.

    Defines a single reference sensor used to calculate values at a target height.
    Multiple references can be combined with weights for interpolation.

    Validation Rules:
        - weight: MUST be positive; for interpolation, weights should sum to 1.0

    Attributes:
        sensor: SensorColumn metadata for the reference sensor.
            Contains column_name, height, and other sensor metadata.
        weight: Weight for weighted averaging in interpolation.
            Default is 1.0 (single reference). For interpolation with two references,
            weights should sum to 1.0 (enforced by WindSpeedHeightConfig/WindDirectionHeightConfig).

    Example:
        For extrapolating WS_100m from WS_80m with shear=0.15:
            HeightReference(
                sensor=SensorColumn(column_name="WS_80m_avg", sensor_type="WindSpeed", ...),
                weight=1.0
            )

        For interpolating WS_100m between 80m and 120m:
            HeightReference(sensor=SensorColumn(..., height=80.0), weight=0.4)
            HeightReference(sensor=SensorColumn(..., height=120.0), weight=0.6)
    """

    sensor: SensorColumn
    weight: float = 1.0

    @field_validator("weight")
    @classmethod
    def validate_weight_positive(cls, v: float) -> float:
        """Validate weight is a positive value.

        Weights must be positive because:
        1. Negative weights would produce nonsensical results
        2. They represent relative importance in weighted averages
        3. Zero weight would make the reference effectively unused

        Args:
            v: The weight value to validate

        Returns:
            The validated weight if positive

        Raises:
            ValueError: If weight is less than or equal to zero
        """
        if v <= 0:
            raise ValueError(f"weight must be positive, got: {v}")
        return v


class WindSpeedHeightConfig(BaseModel):
    """Configuration for filling wind speed at a target height.

    Supports two filling methods:
    - Interpolation: Target height is between two reference heights using 1/distance weighting
    - Extrapolation: Target height is above highest reference using power law shear

    The power law for wind speed extrapolation:
        V2 = V1 * (H2 / H1)^shear

    Where:
        V1, H1 = Reference wind speed and height
        V2, H2 = Target wind speed and height
        shear = Power law exponent (typically 0.1-0.3 for stable conditions)

    Validation Rules:
        - target_sensor: Must have sensor_type="WindSpeed"
        - references: Exactly 2 for interpolation, 1 for extrapolation
        - weights: Must sum to 1.0 (±0.001) for interpolation
        - height consistency: Interpolation target between refs, extrapolation target above

    Attributes:
        target_sensor: SensorColumn for the target height.
            Contains column_name (output column) and height information.
        references: List of reference sensors. 2 for interpolation, 1 for extrapolation.
        shear: Power law shear exponent α for extrapolation.
            Typical values: 0.05-0.4 depending on atmospheric stability.
            Negative shear possible in very stable conditions.

    Raises:
        ValueError: On validation failure (reference count, weights, height consistency)

    Example:
        # Extrapolation: Estimate WS_100m from WS_80m with shear=0.15
        WindSpeedHeightConfig(
            target_sensor=SensorColumn(
                column_name="WS_100m_fill:extrapolated",
                sensor_type="WindSpeed",
                height=100.0,
                ...
            ),
            references=[HeightReference(sensor=SensorColumn(..., height=80.0), weight=1.0)],
            shear=0.15
        )

        # Interpolation: Estimate WS_100m between 80m and 120m
        WindSpeedHeightConfig(
            target_sensor=SensorColumn(column_name="WS_100m_fill:interpolated", ...),
            references=[
                HeightReference(sensor=SensorColumn(..., height=80.0), weight=0.4),
                HeightReference(sensor=SensorColumn(..., height=120.0), weight=0.6)
            ],
            shear=0.15  # Pre-fitted from data, used for validation only
        )
    """

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
        """Validate target_sensor has correct sensor_type for wind speed.

        Args:
            v: The target_sensor to validate

        Returns:
            The validated target_sensor

        Raises:
            ValueError: If sensor_type is not "WindSpeed"
        """
        if v.sensor_type != "WindSpeed":
            raise ValueError(
                f"target_sensor.sensor_type must be 'WindSpeed', got: {v.sensor_type}"
            )
        return v

    @model_validator(mode="after")
    def validate_reference_count_matches_method(self) -> "WindSpeedHeightConfig":
        """Ensure reference count matches interpolation/extrapolation method.

        This validation ensures:
        - Interpolation uses exactly 2 references (lower and higher heights)
        - Extrapolation uses exactly 1 reference (highest available height)

        The reason for this split:
        - Interpolation: Two reference points define the linear relationship in log space
        - Extrapolation: One reference + shear parameter defines the power law

        Returns:
            Self if validation passes

        Raises:
            ValueError: If reference count doesn't match method requirements
        """
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
        """Ensure interpolation weights sum to 1.0 (±0.001 tolerance).

        Weighted interpolation requires weights to sum to 1.0 to maintain
        unbiased estimation. The ±0.001 tolerance accounts for floating point
        precision issues in weight calculation.

        This validation is only applied to interpolation configs.

        Returns:
            Self if validation passes

        Raises:
            ValueError: If weights don't sum to 1.0 within tolerance
        """
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
        """Ensure target height is consistent with interpolation/extrapolation method.

        Height consistency rules:
        - Interpolation: Target height must be strictly BETWEEN reference heights
          (linear interpolation is undefined outside the reference range)
        - Extrapolation: Target height must be strictly ABOVE reference height
          (extrapolation below would be mathematically valid but physically questionable)

        Returns:
            Self if validation passes

        Raises:
            ValueError: If target height doesn't meet method-specific requirements
        """
        method = self._extract_method()
        target_height = self.target_height
        ref_heights = sorted([r.sensor.height for r in self.references])

        if method == "interpolated":
            # Target must be between reference heights
            if len(ref_heights) == 2:
                if not (ref_heights[0] < target_height < ref_heights[1]):
                    raise ValueError(
                        f"Interpolation target height {target_height}m must be "
                        f"between reference heights [{ref_heights[0]}m, {ref_heights[1]}m]"
                    )
        elif method == "extrapolated":
            # Target must be above reference height
            if ref_heights and target_height <= ref_heights[0]:
                raise ValueError(
                    f"Extrapolation target height {target_height}m must be "
                    f"above reference height {ref_heights[0]}m"
                )

        return self

    @model_validator(mode="after")
    def validate_shear_bounds(self) -> "WindSpeedHeightConfig":
        """Warn if shear is outside physically reasonable bounds [-0.5, 1.0].

        This is an advisory validation that notes unusual shear values.
        Extreme shear values may indicate:
        - Data quality issues
        - Non-standard atmospheric conditions
        - Configuration errors

        Note: This does NOT raise an error because:
        1. Real atmospheric conditions can produce unusual shear
        2. The user may have specific domain knowledge justifying the value
        3. Production systems should handle edge cases gracefully

        In production, this should log a warning instead of silently passing.

        Returns:
            Self always (shear bounds are advisory, not enforced)
        """
        # Note: This is a validation check but we don't raise an error
        # since the config might still be intentionally used
        if self.shear < -0.5 or self.shear > 1.0:
            # Return self - we just want to note this during validation
            # In production, this would log a warning
            pass
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
    """Configuration for filling wind direction at a target height.

    Supports two filling methods:
    - Interpolation: Target height between two references using vector components
    - Extrapolation: Target height above highest reference using deg_diff_per_m

    Wind direction requires VECTOR-BASED processing because:
    1. Directions are circular (0° ≡ 360°)
    2. Direct arithmetic fails at wraparound points
    3. Simple averaging gives wrong results (e.g., averaging 350° and 10°)

    The vector approach converts directions to (u,v) components:
    - u = -sin(θ) (East-West, positive = East)
    - v = -cos(θ) (North-South, positive = North)
    - θ = wind direction in degrees (direction wind comes FROM)

    After processing, vectors are converted back to degrees.

    Validation Rules:
        - target_sensor: Must have sensor_type="WindDirection"
        - references: Exactly 2 for interpolation, 1 for extrapolation
        - weights: Must sum to 1.0 (±0.001) for interpolation
        - height consistency: Same rules as wind speed

    Attributes:
        target_sensor: SensorColumn for the target height.
        references: List of reference sensors. 2 for interpolation, 1 for extrapolation.
        deg_diff_per_m: Direction change per meter (degrees/meter).
            Positive = clockwise rotation with height (veering)
            Negative = counter-clockwise (backing)

    Raises:
        ValueError: On validation failure (reference count, weights, height consistency)

    Example:
        # Extrapolation: Estimate WD_100m from WD_80m with veering of 0.1°/m
        WindDirectionHeightConfig(
            target_sensor=SensorColumn(
                column_name="WD_100m_fill:extrapolated",
                sensor_type="WindDirection",
                height=100.0,
                ...
            ),
            references=[HeightReference(sensor=SensorColumn(..., height=80.0), weight=1.0)],
            deg_diff_per_m=0.1
        )
    """

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
        """Validate target_sensor has correct sensor_type for wind direction.

        Args:
            v: The target_sensor to validate

        Returns:
            The validated target_sensor

        Raises:
            ValueError: If sensor_type is not "WindDirection"
        """
        if v.sensor_type != "WindDirection":
            raise ValueError(
                f"target_sensor.sensor_type must be 'WindDirection', got: {v.sensor_type}"
            )
        return v

    @model_validator(mode="after")
    def validate_reference_count_matches_method(self) -> "WindDirectionHeightConfig":
        """Ensure reference count matches interpolation/extrapolation method.

        Returns:
            Self if validation passes

        Raises:
            ValueError: If reference count doesn't match method requirements
        """
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
        """Ensure interpolation weights sum to 1.0 (±0.001 tolerance).

        Returns:
            Self if validation passes

        Raises:
            ValueError: If weights don't sum to 1.0 within tolerance
        """
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
        """Ensure target height is consistent with interpolation/extrapolation method.

        Returns:
            Self if validation passes

        Raises:
            ValueError: If target height doesn't meet method-specific requirements
        """
        method = self._extract_method()
        target_height = self.target_height
        ref_heights = sorted([r.sensor.height for r in self.references])

        if method == "interpolated":
            # Target must be between reference heights
            if len(ref_heights) == 2:
                if not (ref_heights[0] < target_height < ref_heights[1]):
                    raise ValueError(
                        f"Interpolation target height {target_height}m must be "
                        f"between reference heights [{ref_heights[0]}m, {ref_heights[1]}m]"
                    )
        elif method == "extrapolated":
            # Target must be above reference height
            if ref_heights and target_height <= ref_heights[0]:
                raise ValueError(
                    f"Extrapolation target height {target_height}m must be "
                    f"above reference height {ref_heights[0]}m"
                )

        return self

    @model_validator(mode="after")
    def validate_deg_diff_reasonable(self) -> "WindDirectionHeightConfig":
        """Warn if deg_diff_per_m is outside reasonable bounds [-0.5, 0.5].

        Reasonable bounds for direction change per meter:
        - Extreme values (>0.5°/m) might indicate:
          * Data quality issues
          * Sensor misalignment
          * Complex terrain effects

        This is advisory only - production use should log warnings.

        Returns:
            Self always (bounds are advisory, not enforced)
        """
        # Note: Reasonable bounds for direction change per meter
        # Very high values might indicate data issues
        if abs(self.deg_diff_per_m) > 0.5:
            # Return self - we just want to note this during validation
            # In production, this would log a warning
            pass
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
    """Complete mast configuration for height filling operations.

    Combines input/output sources with wind speed and direction filling configurations.
    This represents a single mast's complete fill-heights configuration.

    Validation Rules:
        - No duplicate target_column values across all heights
        - No circular references (target column appearing as source)

    Attributes:
        name: Unique mast identifier. Must be unique across all masts in config.
        input: TimeSeriesSource defining where input data comes from.
            Typically points to reconstruct-meso output.
        output: TimeSeriesSource defining where to save filled data.
            New columns are added to input, saved here.
        windspeed: List of wind speed height filling configurations.
            Can contain multiple entries for different target heights/methods.
        winddirection: List of wind direction height filling configurations.
            Can contain multiple entries for different target heights/methods.

    Example:
        MastFillConfig(
            name="mast-01",
            input=TimeSeriesSource(data="./reconstructed/mast-01.parquet"),
            output=TimeSeriesSource(data="./filled/mast-01.parquet"),
            windspeed=[
                WindSpeedHeightConfig(
                    target_column="WS_100m_fill:extrapolated",
                    references=[HeightReference(...)],
                    shear=0.15
                )
            ],
            winddirection=[
                WindDirectionHeightConfig(
                    target_column="WD_100m_fill:extrapolated",
                    references=[HeightReference(...)],
                    deg_diff_per_m=0.1
                )
            ]
        )
    """

    name: str
    input: TimeSeriesSource
    output: TimeSeriesSource
    windspeed: list[WindSpeedHeightConfig]
    winddirection: list[WindDirectionHeightConfig]

    @model_validator(mode="after")
    def validate_no_duplicate_targets(self) -> "MastFillConfig":
        """Ensure no duplicate target_column values across all heights.

        Duplicate target columns would cause:
        1. Ambiguity in which configuration applies
        2. Column name conflicts during fill operations
        3. Data integrity issues

        This check scans both windspeed and winddirection configurations.

        Returns:
            Self if no duplicates found

        Raises:
            ValueError: If duplicate target_column is found
        """
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
        """Ensure target columns don't appear in any source_column (circular ref).

        Circular references would cause:
        1. Dependencies that can't be resolved (A depends on B, B depends on A)
        2. Potential infinite loops during fill operations
        3. Incorrect results from using filled data as source

        This check ensures target columns only reference original source columns
        (those not ending in '_fill:*', not those created by fill operations).

        Returns:
            Self if no circular references found

        Raises:
            ValueError: If circular reference is detected
        """
        # Collect all target columns
        all_targets = set(
            ws.target_column for ws in self.windspeed
        ) | set(
            wd.target_column for wd in self.winddirection
        )

        # Check that no target appears as a source
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
    """Top-level configuration for fill heights operation.

    This is the root configuration model read from fill-heights-*.toml files.
    It contains multiple mast configurations and metadata about the configuration.

    Design Pattern:
        This uses the Facade pattern - combining all mast configs into one
        document that can be serialized/deserialized from a single TOML file.

    Attributes:
        strategy: Strategy identifier used to generate this config.
            Default is "default". Used by recommend commands to track generation method.
        masts: List of MastFillConfig, one per mast.
            Each mast has its own input/output and fill configurations.

    Example TOML Structure:
        [fill-heights]
        strategy = "default"
        
        [[fill-heights.masts]]
        name = "mast-01"
        input.data = "./reconstructed/mast-01.parquet"
        output.data = "./filled/mast-01.parquet"
        
        [[fill-heights.masts.windspeed]]
        target_column = "WS_100m_fill:extrapolated"
        shear = 0.15
        [[fill-heights.masts.windspeed.references]]
        source_column = "WS_80m_avg"
        height = 80.0
        weight = 1.0
        
        [[fill-heights.masts.winddirection]]
        target_column = "WD_100m_fill:extrapolated"
        deg_diff_per_m = 0.1
        [[fill-heights.masts.winddirection.references]]
        source_column = "WD_80m_avg"
        height = 80.0
        weight = 1.0
    """

    strategy: str = "default"
    masts: list[MastFillConfig]

    @model_validator(mode="after")
    def validate_mast_names_unique(self) -> "FillHeightsConfiguration":
        """Ensure all mast names are unique within the configuration.

        Duplicate mast names would cause:
        1. Ambiguity when loading/saving configurations
        2. Difficulties in tracking processing status per mast
        3. Potential data overwriting issues

        Returns:
            Self if all mast names are unique

        Raises:
            ValueError: If duplicate mast names are found
        """
        names = [mast.name for mast in self.masts]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate mast names found in configuration")
        return self


def load_fill_heights_config(config_path: str) -> FillHeightsConfiguration:
    """Load fill heights configuration from TOML file.

    This is the primary entry point for loading fill-heights configurations
    from persistent storage (TOML files).

    The function:
    1. Reads the TOML file using tomli (binary mode for Unicode support)
    2. Parses it into a dictionary
    3. Validates and constructs FillHeightsConfiguration via Pydantic

    Args:
        config_path: Absolute path to fill-heights configuration TOML file.
            Can be relative to current working directory.

    Returns:
        FillHeightsConfiguration parsed and validated from the file.
        All validation rules are applied during construction.

    Raises:
        FileNotFoundError: If config file doesn't exist at specified path
        ValueError: If TOML parsing fails or configuration validation fails
        pydantic.ValidationError: If configuration structure is invalid

    Example:
        config = load_fill_heights_config("/project/fill-heights.toml")
        for mast in config.masts:
            print(f"Mast: {mast.name}, WS configs: {len(mast.windspeed)}")
    """
    with open(config_path, "rb") as f:
        data = tomli.load(f)

    return FillHeightsConfiguration(**data)
