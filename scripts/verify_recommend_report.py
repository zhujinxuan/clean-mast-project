#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from cleanmast.application.usecases.recommend_report import recommend_report
from cleanmast.subdomains.assessment.domain.value_objects.rep_ts_report_config import (
    RepTsReportConfig,
)


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    project_dir = (script_dir / ".." / "test-data" / "cleanmast" / "kp-202603-report").resolve()
    output_path = project_dir / "rep-ts-report.toml"
    metrics_path = project_dir / "recommend-report-metrics.json"

    if output_path.exists():
        output_path.unlink()

    try:
        generated_path = recommend_report(str(project_dir))
    except Exception as e:
        print(f"ERROR: recommend_report failed: {e}")
        return 1

    assert Path(generated_path).resolve() == output_path.resolve()

    try:
        config = RepTsReportConfig.from_toml(output_path)
    except Exception as e:
        print(f"ERROR: Failed to parse generated TOML: {e}")
        return 1

    errors: list[str] = []

    sections = config.document.sections
    if len(sections) != 1:
        errors.append(f"Expected 1 document section, got {len(sections)}")
    else:
        section = sections[0]
        if section.title != "风资源分析":
            errors.append(f"Expected section title '风资源分析', got '{section.title}'")

        subsections = section.subsections
        if len(subsections) != 3:
            errors.append(f"Expected 3 subsections, got {len(subsections)}")
        else:
            _validate_timeseries_subsection(subsections[0], "测风年", errors)
            _validate_timeseries_subsection(subsections[1], "代表年", errors)
            _validate_fifty_year_subsection(subsections[2], errors)

    metrics = {
        "valid": len(errors) == 0,
        "section_count": len(sections),
        "subsection_count": len(sections[0].subsections) if sections else 0,
        "error_count": len(errors),
        "errors": errors,
    }

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    if errors:
        print("VALIDATION FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"SUCCESS: Generated and validated {output_path}")
    print(f"Metrics written to {metrics_path}")
    return 0


def _validate_timeseries_subsection(ts_sub, name: str, errors: list[str]) -> None:
    if ts_sub.type != "timeseries":
        errors.append(f"Expected {name} type 'timeseries', got '{ts_sub.type}'")

    expected_titles = {"测风年": "测风年风资源分析", "代表年": "代表年风资源分析"}
    if ts_sub.title != expected_titles.get(name):
        errors.append(f"Expected {name} title '{expected_titles.get(name)}', got '{ts_sub.title}'")

    if not ts_sub.masts or len(ts_sub.masts) != 2:
        errors.append(
            f"Expected {name} timeseries to have 2 masts, got {len(ts_sub.masts) if ts_sub.masts else 0}"
        )
    else:
        mast_names = [m.name for m in ts_sub.masts]
        if mast_names != ["L32261", "M245228"]:
            errors.append(f"Expected mast names ['L32261', 'M245228'], got {mast_names}")

    expected_counts = {"测风年": 7, "代表年": 4}
    expected_types_map = {
        "测风年": [
            "air_density",
            "temporal",
            "wind_rose",
            "vertical_profile",
            "wind_frequency",
            "weibull",
            "turbulence",
        ],
        "代表年": [
            "temporal",
            "wind_rose",
            "wind_frequency",
            "weibull",
        ],
    }
    expected_count = expected_counts.get(name, 6)
    if not ts_sub.subsections or len(ts_sub.subsections) != expected_count:
        errors.append(
            f"Expected {name} timeseries to have {expected_count} subsections, got {len(ts_sub.subsections) if ts_sub.subsections else 0}"
        )
    else:
        expected_types = expected_types_map.get(name, [])
        actual_types = [s.type for s in ts_sub.subsections]
        if actual_types != expected_types:
            errors.append(f"Expected subsection types {expected_types}, got {actual_types}")


def _validate_fifty_year_subsection(fifty_year, errors: list[str]) -> None:
    if fifty_year.type != "fifty_year_max_wind":
        errors.append(
            f"Expected subsection type 'fifty_year_max_wind', got '{fifty_year.type}'"
        )
    if fifty_year.title != "五十年一遇最大风速":
        errors.append(
            f"Expected subsection title '五十年一遇最大风速', got '{fifty_year.title}'"
        )
    if not fifty_year.masts or len(fifty_year.masts) != 2:
        errors.append(
            f"Expected fifty_year_max_wind to have 2 masts, got {len(fifty_year.masts) if fifty_year.masts else 0}"
        )
    if fifty_year.subsections:
        errors.append(
            f"Expected fifty_year_max_wind to have no subsections, got {len(fifty_year.subsections)}"
        )


if __name__ == "__main__":
    sys.exit(main())
