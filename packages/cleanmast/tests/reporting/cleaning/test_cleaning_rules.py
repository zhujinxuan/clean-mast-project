"""Tests for 2.3.3 缺测与不合理数据处理 (CleaningRulesSection)."""

from datetime import datetime
from pathlib import Path

import polars as pl
import yaml
from cleanmast.shared.timeseries import SensorColumn, TimeRange, TimeSeriesData
from cleanmast.shared.timeseries.time_series_source import TimeSeriesSource
from cleanmast.subdomains.reporting.model.analysis_input import (
    CleaningAnalysisPayload,
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.model.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.reporting.subdomains.cleaning import CleaningRulesSection
from cleanmast.subdomains.reporting.subdomains.cleaning.rules_io import (
    discover_enabled_rules,
    load_violation_stats,
)
from typst_ir import TypstParagraph, TypstTable

PRESET_RULES_TOML = """\
[[rules]]
name = "Wind Speed Range"
sensorType = "WindSpeed"
[rules.out_of_range]
min = 0.0
max = 30.0

[[rules]]
name = "High Wind Speed Layer Difference"
sensorType = "WindSpeed"
height.min = 70.0
[rules.layer_difference]
lower_layer_height = 20.0
abs_diff.max = 2.0
[rules.layer_difference.lower_wind_speed]
min = 3
max = 25
"""

INLINE_RULES = """
  { name = "Wind Speed Range", sensorType = "WindSpeed",
    out_of_range = { min = 0.0, max = 30.0 } },
  { name = "Icing WS Detection", sensorType = "WindSpeed",
    icing = { time_range = 18000, max_change = 0.02 } },
  { name = "Wind Direction Layer Difference", sensorType = "WindDirection",
    height = { min = 70.0 },
    layer_difference = { lower_layer_height = 20.0,
                         abs_diff = { max = 22.5 },
                         lower_wind_speed = {} } },
  { name = "Lidar Availability Check", sensorType = "DataAvailability",
    availability = { low_threshold = 80.0 } },
"""

PROCESS_CLEAN_TOML = f"""\
[[masts]]
name = "M1"
input = {{ data = "raw/M1.parquet" }}
output = {{ data = "clean/M1.parquet" }}
rules = "clean-rules.toml"

[[masts]]
name = "M2"
input = {{ data = "raw/M2.parquet" }}
output = {{ data = "clean/M2.parquet" }}
rules = [{INLINE_RULES}]
"""

VIOLATIONS_YAML = {
    "processing_info": {
        "mast_name": "M1",
        "start_time": "2024-01-01T00:00:00",
        "end_time": "2024-12-31T23:50:00",
        "total_timestamps": 52704,
    },
    "violation_summary": {
        "total_violations": 120,
        "violation_percentage": 0.23,
    },
    "violations_by_column": [
        {
            "column": "WS_140_N",
            "total_violations": 80,
            "rules": [
                {
                    "rule_name": "Wind Speed Range",
                    "count": 50,
                    "timestamps": ["2024-01-05T10:00:00"],
                },
                {
                    "rule_name": "Icing WS Detection",
                    "count": 30,
                    "timestamps": ["2024-02-01T00:00:00"],
                },
            ],
        },
        {
            "column": "WD_140",
            "total_violations": 40,
            "rules": [
                {
                    "rule_name": "Wind Direction Range",
                    "count": 40,
                    "timestamps": [],
                },
            ],
        },
    ],
}


def _project(tmp_path: Path, *, with_config: bool = True, with_stats: bool = True) -> Path:
    """Synthetic project dir with process-clean.toml and/or stats YAML."""
    if with_config:
        (tmp_path / "process-clean.toml").write_text(
            PROCESS_CLEAN_TOML, encoding="utf-8"
        )
        (tmp_path / "clean-rules.toml").write_text(
            PRESET_RULES_TOML, encoding="utf-8"
        )
    if with_stats:
        stats_dir = tmp_path / "process-stats"
        stats_dir.mkdir()
        with open(
            stats_dir / "process-clean-M1.yaml", "w", encoding="utf-8"
        ) as handle:
            yaml.safe_dump(VIOLATIONS_YAML, handle, allow_unicode=True)
    return tmp_path


def _input(mast_name: str) -> SingleMastAnalysisInput:
    ts = TimeSeriesData(
        df=pl.DataFrame({
            "timestamp": [datetime(2025, 1, 1)],
            "ws_140": [7.0],
        }),
        sensors=[
            SensorColumn(
                column_name="ws_140",
                sensor_type="WindSpeed",
                sensor_direction="N",
                height=140.0,
                stat_type="avg",
                unit="m/s",
            )
        ],
    )
    return SingleMastAnalysisInput(
        time_series=ts,
        parameters=AnalysisParameters(
            air_density=1.225,
            extreme_wind_10min_heights=[],
            extreme_wind_3s_heights=[],
            extreme_wind_gust_factors=[],
        ),
        mast_name=mast_name,
        cleaning_payload=CleaningAnalysisPayload(
            raw_input=TimeSeriesSource(data="raw/M1.parquet"),
            clean_input=TimeSeriesSource(data="clean/M1.parquet"),
            tower_shading_input=None,
            cleaning_heights=[140.0],
            analysis_window=TimeRange(
                min=datetime(2025, 1, 1), max=datetime(2025, 12, 31)
            ),
        ),
    )


class TestDiscoverEnabledRules:
    def test_inline_rules_cover_all_criteria_kinds(self, tmp_path):
        enabled = discover_enabled_rules(_project(tmp_path))
        assert enabled is not None
        assert enabled.source == "process-clean.toml"
        by_name = {row["rule_name"]: row for row in enabled.rows}

        assert by_name["Wind Speed Range"]["condition"] == "合理范围 [0, 30]"
        assert by_name["Icing WS Detection"]["condition"] == "持续18000s变化不超过0.02"
        assert by_name["Lidar Availability Check"]["condition"] == "可用率阈值80%"
        assert by_name["Wind Direction Layer Difference"]["condition"] == (
            "与下层20m差值超出[-∞, 22.5]"
        )

    def test_preset_referenced_rules_resolved(self, tmp_path):
        enabled = discover_enabled_rules(_project(tmp_path))
        assert enabled is not None
        preset_names = {
            "Wind Speed Range",
            "High Wind Speed Layer Difference",
        }
        assert preset_names <= {row["rule_name"] for row in enabled.rows}
        layer = next(
            row
            for row in enabled.rows
            if row["rule_name"] == "High Wind Speed Layer Difference"
        )
        assert layer["condition"] == (
            "与下层20m差值超出[-∞, 2]，且下层风速在[3, 25]内"
        )

    def test_duplicate_rules_across_masts_render_once(self, tmp_path):
        enabled = discover_enabled_rules(_project(tmp_path))
        assert enabled is not None
        names = [row["rule_name"] for row in enabled.rows]
        assert names.count("Wind Speed Range") == 1  # preset + inline duplicate

    def test_missing_config_returns_none(self, tmp_path):
        assert discover_enabled_rules(_project(tmp_path, with_config=False)) is None

    def test_none_project_dir_returns_none(self):
        assert discover_enabled_rules(None) is None


class TestLoadViolationStats:
    def test_parses_yaml_structure(self, tmp_path):
        stats = load_violation_stats(_project(tmp_path), "M1")
        assert stats is not None
        assert stats.mast_name == "M1"
        assert stats.total_violations == 120
        assert stats.violation_percentage == 0.23
        assert [col.column for col in stats.columns] == ["WS_140_N", "WD_140"]
        ws_rules = stats.columns[0].rules
        assert [(r.rule_name, r.count) for r in ws_rules] == [
            ("Wind Speed Range", 50),
            ("Icing WS Detection", 30),
        ]

    def test_missing_file_returns_none(self, tmp_path):
        assert load_violation_stats(_project(tmp_path), "NOPE") is None

    def test_malformed_yaml_returns_none(self, tmp_path):
        stats_dir = tmp_path / "process-stats"
        stats_dir.mkdir()
        (stats_dir / "process-clean-M9.yaml").write_text(
            "violations_by_column: [unclosed", encoding="utf-8"
        )
        assert load_violation_stats(tmp_path, "M9") is None

    def test_none_project_dir_returns_none(self):
        assert load_violation_stats(None, "M1") is None


class TestCleaningRulesSection:
    def test_renders_intro_rules_table_and_violations(self, tmp_path):
        section = CleaningRulesSection.from_inputs(
            [_input("M1"), _input("M2")], project_dir=_project(tmp_path)
        )
        assert section.title == "缺测与不合理数据处理"
        ir = section.render_ir(tmp_path)
        assert ir.heading.text == "缺测与不合理数据处理"

        paragraphs = [
            block.text for block in ir.body if isinstance(block, TypstParagraph)
        ]
        assert any("GB/T 37523-2019" in text for text in paragraphs)
        assert any(
            "M1：检验共剔除120点，占检验期总点数的0.23%。" in text
            for text in paragraphs
        )
        assert any(
            "M2：未找到 process-stats/process-clean-M2.yaml，剔除统计从略。" in text
            for text in paragraphs
        )

        tables = [block for block in ir.body if isinstance(block, TypstTable)]
        assert len(tables) == 2

        rules_table = tables[0]
        assert rules_table.headers == ["规则名称", "传感器类型", "适用高度(m)", "判定条件"]
        rows = {row[0]: row for row in rules_table.data}
        assert rows["风速范围检查"][1] == "风速"
        assert rows["风速范围检查"][2] == "全部高度"
        assert rows["风速范围检查"][3] == "合理范围 [0, 30]"
        assert rows["高风速层差检查"][2] == "≥70m"

        violations_table = tables[1]
        assert violations_table.headers == [
            "测风塔", "数据列", "剔除规则", "剔除点数",
        ]
        assert ["M1", "WS_140_N", "风速范围检查", "50"] in violations_table.data
        assert ["M1", "WS_140_N", "风速结冰检测", "30"] in violations_table.data
        assert ["M1", "WD_140", "风向范围检查", "40"] in violations_table.data
        assert all(row[0] == "M1" for row in violations_table.data)

    def test_without_project_dir_renders_skip_notes(self, tmp_path):
        section = CleaningRulesSection.from_inputs([_input("M1")])
        ir = section.render_ir(tmp_path)
        paragraphs = [
            block.text for block in ir.body if isinstance(block, TypstParagraph)
        ]
        assert any("未找到 process-clean.toml" in text for text in paragraphs)
        assert any("M1：未找到 process-stats" in text for text in paragraphs)
        assert not [block for block in ir.body if isinstance(block, TypstTable)]

    def test_empty_items_still_render_rules(self, tmp_path):
        section = CleaningRulesSection.from_inputs(
            [], project_dir=_project(tmp_path)
        )
        ir = section.render_ir(tmp_path)
        assert ir.heading.text == "缺测与不合理数据处理"
        tables = [block for block in ir.body if isinstance(block, TypstTable)]
        assert len(tables) == 1  # rules table only, no violation rows
