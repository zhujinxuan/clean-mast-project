"""Clean pipeline configuration models (process-clean.toml).

These models mirror the Julia source of truth EXACTLY (field names and
structure): ``CleanMastProject/src/Types/CleanRules.jl`` (``Rule`` and its
criteria structs, parsed by ``from_dict``) and
``CleanMastProject/src/Types/ProcessCleanConfig.jl`` (``Mast``,
``ProcessCleanConfiguration``). Python is a READ-ONLY consumer — the Julia
pipeline authors and executes these files; no new authoring format.

Schema notes (Julia parity):
- ``sensorType`` keeps the Julia/TOML camelCase spelling.
- A rule carries exactly one criteria block — ``out_of_range``,
  ``layer_difference``, ``icing``, or ``availability`` — mirroring the
  ``from_dict(Rule, ...)`` validation. Julia's ``ManualCriteria`` is an
  internal marker that ``from_dict`` cannot parse, so it has no TOML
  representation here either.
- ``rules`` on a mast is either a path string (resolved against the project
  directory, Julia ``load_rules``) or an inline array of rules.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cleanmast.shared.timeseries.time_series_source import (
    TimeSeriesSource,
)

_CRITERIA_FIELDS: tuple[str, ...] = (
    "out_of_range",
    "layer_difference",
    "icing",
    "availability",
)


class HeightFilter(BaseModel):
    """Height range a rule applies to (Julia ``HeightFilter``).

    Attributes:
        min: Minimum sensor height in meters (None = unbounded).
        max: Maximum sensor height in meters (None = unbounded).
    """

    model_config = ConfigDict(frozen=True)

    min: float | None = None
    max: float | None = None


class RangeCriteria(BaseModel):
    """Acceptance range (Julia ``RangeCriteria``).

    Attributes:
        min: Lower bound (None = unbounded).
        max: Upper bound (None = unbounded).
    """

    model_config = ConfigDict(frozen=True)

    min: float | None = None
    max: float | None = None


class LayerDifferenceCriteria(BaseModel):
    """Layer-difference criteria (Julia ``LayerDifferenceCriteria``).

    Flags sensors whose value deviates too far from a lower reference layer
    while that layer indicates free-stream flow.

    Attributes:
        lower_layer_height: Height of the reference (lower) layer in meters.
        abs_diff: Allowed absolute difference range.
        lower_wind_speed: Wind speed range at the lower layer for the rule
            to apply.
    """

    model_config = ConfigDict(frozen=True)

    lower_layer_height: float
    abs_diff: RangeCriteria
    lower_wind_speed: RangeCriteria


class IcingCriteria(BaseModel):
    """Icing detection criteria (Julia ``IcingCriteria``).

    Attributes:
        time_range: Detection window in seconds.
        max_change: Maximum tolerated relative change over the window.
    """

    model_config = ConfigDict(frozen=True)

    time_range: int
    max_change: float


class AvailabilityCriteria(BaseModel):
    """Data availability criteria (Julia ``AvailabilityCriteria``).

    Attributes:
        low_threshold: Availability percentage below which data is flagged.
    """

    model_config = ConfigDict(frozen=True)

    low_threshold: float


class CleanRule(BaseModel):
    """A single data-cleaning rule (Julia ``Rule``).

    Attributes:
        name: Human-readable rule name.
        sensorType: Sensor type the rule applies to (e.g. "WindSpeed").
            Keeps the Julia/TOML camelCase spelling.
        height: Height filter; omitted (or empty) means all heights.
        out_of_range: Range criteria — exactly one of the four criteria
            blocks must be present.
        layer_difference: Layer-difference criteria.
        icing: Icing detection criteria.
        availability: Availability criteria.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    sensorType: str
    height: HeightFilter = Field(default_factory=HeightFilter)
    out_of_range: RangeCriteria | None = None
    layer_difference: LayerDifferenceCriteria | None = None
    icing: IcingCriteria | None = None
    availability: AvailabilityCriteria | None = None

    @model_validator(mode="after")
    def validate_exactly_one_criteria(self) -> "CleanRule":
        """Enforce exactly one criteria block, mirroring Julia ``from_dict``."""
        present = [f for f in _CRITERIA_FIELDS if getattr(self, f) is not None]
        if len(present) != 1:
            raise ValueError(
                "Rule must have exactly one of: "
                + ", ".join(_CRITERIA_FIELDS)
                + f". Found: {', '.join(present) if present else 'none'}"
            )
        return self


class CleanRulesFile(BaseModel):
    """Top level of a standalone clean-rules preset file (``[[rules]]``)."""

    model_config = ConfigDict(frozen=True)

    rules: list[CleanRule]


class ProcessCleanMast(BaseModel):
    """Per-mast entry in process-clean.toml (Julia ``ProcessCleanConfig.Mast``).

    Attributes:
        name: Mast identifier.
        input: Raw (pre-clean) time series source.
        output: Cleaned time series destination.
        rules: Either a path to a rules preset file (relative to the project
            directory, resolved like Julia ``load_rules``) or an inline list
            of rules.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    input: TimeSeriesSource
    output: TimeSeriesSource
    rules: str | list[CleanRule]


class ProcessCleanConfiguration(BaseModel):
    """Full configuration read from process-clean.toml.

    Attributes:
        masts: List of mast configurations to clean.
    """

    model_config = ConfigDict(frozen=True)

    masts: list[ProcessCleanMast]
