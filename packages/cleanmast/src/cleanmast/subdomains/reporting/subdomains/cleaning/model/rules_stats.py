"""Value objects parsed from process-clean TOML/YAML sources (2.3.3).

Mirror of the Julia ``ViolationAnalysisData`` structure
(``CleanMastProject/src/Types/ViolationData.jl``) minus the per-timestamp
lists, which the report never renders.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EnabledCleaningRules:
    """Deduplicated enabled rules across the project's masts.

    Attributes:
        rows: One dict per unique rule with keys ``rule_name``,
            ``sensor_type``, ``height_min``, ``height_max`` (None =
            unbounded) and the pre-formatted ``condition`` string.
        source: Filename the rules were discovered from.
    """

    rows: list[dict[str, object]] = field(default_factory=list)
    source: str = ""


@dataclass(frozen=True)
class ViolationRuleCount:
    """Violations of one rule in one sensor column."""

    rule_name: str
    count: int


@dataclass(frozen=True)
class ViolationColumnStats:
    """Violations of one sensor column, grouped by rule."""

    column: str
    total_violations: int
    rules: list[ViolationRuleCount] = field(default_factory=list)


@dataclass(frozen=True)
class MastViolationStats:
    """Parsed ``process-stats/process-clean-<mast>.yaml``.

    Attributes:
        mast_name: Mast the stats belong to.
        total_violations: Total flagged points across all columns.
        violation_percentage: total_violations / total_timestamps * 100,
            None when the YAML omits it.
        columns: Per-column rule breakdown (YAML order).
    """

    mast_name: str
    total_violations: int = 0
    violation_percentage: float | None = None
    columns: list[ViolationColumnStats] = field(default_factory=list)
