"""IO boundary for the cleaning-rules subsection (2.3.3).

Reads the two process-clean artifacts the report documents:

- ``process-clean.toml`` (via ``ProjectConfig.discover_process_clean_config``
  + ``load_clean_rules``) — the enabled rules, inline or preset-referenced.
- ``process-stats/process-clean-<mast>.yaml`` — per-mast violation counts
  written by the Julia ``process-clean`` command.

All reading happens here; sections/assembles stay pure. Missing artifacts
return ``None`` so the section can degrade to a note instead of crashing.
"""

from pathlib import Path

import yaml

from cleanmast.subdomains.configuration import (
    CleanRule,
    ProjectConfig,
    load_clean_rules,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model.rules_stats import (
    EnabledCleaningRules,
    MastViolationStats,
    ViolationColumnStats,
    ViolationRuleCount,
)

_PROCESS_STATS_SUBDIR = "process-stats"


def discover_enabled_rules(project_dir: Path | None) -> EnabledCleaningRules | None:
    """Discover and deduplicate the enabled rules of all configured masts.

    Rules are global for the report: identical rules referenced by several
    masts (inline or via preset files) render once, in first-seen order.

    Args:
        project_dir: Project directory holding ``process-clean.toml``.
            None (service without a project) → None.

    Returns:
        The deduplicated rule rows plus the source filename, or None when
        the project has no ``process-clean.toml``.
    """
    if project_dir is None:
        return None
    project_config = ProjectConfig(Path(project_dir))
    discovered = project_config.discover_process_clean_config()
    if discovered is None:
        return None
    rows: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()
    for clean_mast in discovered.config.masts:
        for rule in load_clean_rules(clean_mast.rules, Path(project_dir)):
            key = _rule_key(rule)
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "rule_name": rule.name,
                "sensor_type": rule.sensorType,
                "height_min": rule.height.min,
                "height_max": rule.height.max,
                "condition": format_rule_condition(rule),
            })
    return EnabledCleaningRules(rows=rows, source=discovered.filename)


def format_rule_condition(rule: CleanRule) -> str:
    """Human-readable 判定条件 for one rule, per its criteria kind."""
    if rule.out_of_range is not None:
        return f"合理范围 {_format_range(rule.out_of_range.min, rule.out_of_range.max)}"
    if rule.layer_difference is not None:
        criteria = rule.layer_difference
        text = (
            f"与下层{criteria.lower_layer_height:g}m差值超出"
            f"{_format_range(criteria.abs_diff.min, criteria.abs_diff.max)}"
        )
        ws = criteria.lower_wind_speed
        if ws.min is not None or ws.max is not None:
            text += (
                f"，且下层风速在"
                f"{_format_range(ws.min, ws.max)}内"
            )
        return text
    if rule.icing is not None:
        return f"持续{rule.icing.time_range:g}s变化不超过{rule.icing.max_change:g}"
    if rule.availability is not None:
        return f"可用率阈值{rule.availability.low_threshold:g}%"
    raise ValueError(
        f"Rule {rule.name!r} carries no known criteria block; "
        "CleanRule validation requires exactly one"
    )


def load_violation_stats(
    project_dir: Path | None,
    mast_name: str,
) -> MastViolationStats | None:
    """Parse ``process-stats/process-clean-<mast>.yaml`` for one mast.

    Missing file, unreadable YAML, or a non-mapping document → None
    (the section renders a skip note for that mast instead of crashing).
    """
    if project_dir is None:
        return None
    path = (
        Path(project_dir) / _PROCESS_STATS_SUBDIR / f"process-clean-{mast_name}.yaml"
    )
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None

    summary = data.get("violation_summary")
    summary = summary if isinstance(summary, dict) else {}
    percentage = summary.get("violation_percentage")
    columns: list[ViolationColumnStats] = []
    for col in data.get("violations_by_column") or []:
        if not isinstance(col, dict):
            continue
        rules = [
            ViolationRuleCount(
                rule_name=str(rule.get("rule_name", "")),
                count=int(rule.get("count", 0)),
            )
            for rule in col.get("rules") or []
            if isinstance(rule, dict)
        ]
        columns.append(
            ViolationColumnStats(
                column=str(col.get("column", "")),
                total_violations=int(col.get("total_violations", 0)),
                rules=rules,
            )
        )
    return MastViolationStats(
        mast_name=mast_name,
        total_violations=int(summary.get("total_violations", 0)),
        violation_percentage=(
            float(percentage) if percentage is not None else None
        ),
        columns=columns,
    )


def _rule_key(rule: CleanRule) -> tuple[object, ...]:
    """Identity of a rule for dedup across masts."""
    criteria = next(
        getattr(rule, field)
        for field in ("out_of_range", "layer_difference", "icing", "availability")
        if getattr(rule, field) is not None
    )
    return (
        rule.name,
        rule.sensorType,
        rule.height.min,
        rule.height.max,
        _freeze(criteria.model_dump()),
    )


def _freeze(value: object) -> object:
    """Recursively convert a criteria dump into a hashable structure."""
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def _format_bound(value: float | None, unbounded: str) -> str:
    return unbounded if value is None else f"{value:g}"


def _format_range(
    range_min: float | None,
    range_max: float | None,
    low_unbounded: str = "-∞",
    high_unbounded: str = "+∞",
) -> str:
    return (
        f"[{_format_bound(range_min, low_unbounded)}, "
        f"{_format_bound(range_max, high_unbounded)}]"
    )
