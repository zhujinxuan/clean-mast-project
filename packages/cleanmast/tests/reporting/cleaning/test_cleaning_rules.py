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
from cleanmast.subdomains.reporting.subdomains.cleaning.model.constants import (
    format_sensor_label,
)
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

# Deliberately scrambled column order (气压 → 未知列 → 风向 → 高风速 →
# 低风速 → 温度): the section must re-sort by 类型 → 高度 → 规则名.
VIOLATIONS_YAML_M2 = {
    "violation_summary": {"total_violations": 14, "violation_percentage": 0.1},
    "violations_by_column": [
        {
            "column": "AirPressure_10m_avg [hPa]",
            "total_violations": 2,
            "rules": [
                {"rule_name": "range_check", "count": 2, "timestamps": []},
            ],
        },
        {
            "column": "Unknown_99",
            "total_violations": 1,
            "rules": [
                {"rule_name": "range_check", "count": 1, "timestamps": []},
            ],
        },
        {
            "column": "WD_120",
            "total_violations": 4,
            "rules": [
                {"rule_name": "Wind Direction Range", "count": 4, "timestamps": []},
            ],
        },
        {
            "column": "WS_70",
            "total_violations": 6,
            "rules": [
                {
                    "rule_name": "Wind Speed Range",
                    "count": 5,
                    "timestamps": [],
                },
                {
                    "rule_name": "High Wind Speed Layer Difference",
                    "count": 1,
                    "timestamps": [],
                },
            ],
        },
        {
            "column": "WS_30",
            "total_violations": 1,
            "rules": [
                {"rule_name": "range_check", "count": 1, "timestamps": []},
            ],
        },
        {
            "column": "AirTemp_5m_avg [C]",
            "total_violations": 1,
            "rules": [
                {"rule_name": "range_check", "count": 1, "timestamps": []},
            ],
        },
    ],
}


def _sensor(
    column: str,
    sensor_type: str,
    height: float,
    *,
    direction: str = "",
    stat_type: str = "avg",
    unit: str = "m/s",
) -> SensorColumn:
    """Sensor metadata row for stage-series fixtures."""
    return SensorColumn(
        column_name=column,
        sensor_type=sensor_type,
        sensor_direction=direction,
        height=height,
        stat_type=stat_type,
        unit=unit,
    )


M1_SENSORS = [
    _sensor("WS_140_N", "WindSpeed", 140.0, direction="N"),
    _sensor("WD_140", "WindDirection", 140.0, unit="deg"),
]


M2_SENSORS = [
    _sensor("WS_70", "WindSpeed", 70.0, direction="ESE"),
    _sensor("WS_30", "WindSpeed", 30.0, direction="ESE"),
    _sensor("WD_120", "WindDirection", 120.0, direction="N", unit="deg"),
    _sensor("AirTemp_5m_avg [C]", "Temperature", 5.0, unit="C"),
    _sensor("AirPressure_10m_avg [hPa]", "Pressure", 10.0, unit="hPa"),
    # No entry for Unknown_99 — exercises the raw-name fallback.
]


def _project(
    tmp_path: Path,
    *,
    with_config: bool = True,
    with_stats: bool = True,
    extra_stats: dict[str, dict] | None = None,
) -> Path:
    """Synthetic project dir with process-clean.toml and/or stats YAML."""
    if with_config:
        (tmp_path / "process-clean.toml").write_text(
            PROCESS_CLEAN_TOML, encoding="utf-8"
        )
        (tmp_path / "clean-rules.toml").write_text(
            PRESET_RULES_TOML, encoding="utf-8"
        )
    if with_stats or extra_stats:
        stats_dir = tmp_path / "process-stats"
        stats_dir.mkdir()
    if with_stats:
        with open(
            stats_dir / "process-clean-M1.yaml", "w", encoding="utf-8"
        ) as handle:
            yaml.safe_dump(VIOLATIONS_YAML, handle, allow_unicode=True)
    for mast_name, document in (extra_stats or {}).items():
        with open(
            stats_dir / f"process-clean-{mast_name}.yaml", "w", encoding="utf-8"
        ) as handle:
            yaml.safe_dump(document, handle, allow_unicode=True)
    return tmp_path


def _input(
    mast_name: str,
    sensors: list[SensorColumn] | None = None,
) -> SingleMastAnalysisInput:
    """One mast input; ``sensors`` attaches the clean-stage metadata."""
    stage_sensors = M1_SENSORS if sensors is None else sensors
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
    clean_series = TimeSeriesData(
        df=pl.DataFrame({"timestamp": [datetime(2025, 1, 1)]}),
        sensors=stage_sensors,
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
            raw_input=TimeSeriesSource(data=f"raw/{mast_name}.parquet"),
            clean_input=TimeSeriesSource(data=f"clean/{mast_name}.parquet"),
            tower_shading_input=None,
            cleaning_heights=[140.0],
            analysis_window=TimeRange(
                min=datetime(2025, 1, 1), max=datetime(2025, 12, 31)
            ),
            clean_series=clean_series,
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


class TestFormatSensorLabel:
    def test_with_direction_and_avg_stat(self):
        sensor = _sensor("WindSpeed_70m_ESE_avg [m/s]", "WindSpeed", 70.0, direction="ESE")
        assert format_sensor_label(sensor) == "70m 风速(ESE, 均值)"

    def test_merged_direction_omits_direction_slot(self):
        sensor = _sensor("WindSpeed_140m_avg [m/s]", "WindSpeed", 140.0)
        assert format_sensor_label(sensor) == "140m 风速(均值)"

    def test_unknown_stat_falls_back_to_raw(self):
        sensor = _sensor("WS_gust", "WindSpeed", 140.0, direction="ESE", stat_type="gust")
        assert format_sensor_label(sensor) == "140m 风速(ESE, gust)"

    def test_fractional_height_keeps_decimals(self):
        sensor = _sensor("WD", "WindDirection", 87.5, direction="N", unit="deg")
        assert format_sensor_label(sensor) == "87.5m 风向(N, 均值)"

    def test_unknown_type_falls_back_to_raw(self):
        sensor = _sensor("H_10", "Humidity", 10.0, direction="N", unit="%")
        assert format_sensor_label(sensor) == "10m Humidity(N, 均值)"


class TestCleaningRulesSection:
    def test_renders_intro_rules_table_and_per_mast_violations(self, tmp_path):
        project = _project(
            tmp_path, extra_stats={"M2": VIOLATIONS_YAML_M2}
        )
        section = CleaningRulesSection.from_inputs(
            [
                _input("M1"),
                _input("M2", sensors=M2_SENSORS),
            ],
            project_dir=project,
        )
        assert section.title == "缺测与不合理数据处理"
        ir = section.render_ir(tmp_path)
        assert ir.heading.text == "缺测与不合理数据处理"

        paragraphs = [
            block.text for block in ir.body if isinstance(block, TypstParagraph)
        ]
        assert any("GB/T 37523-2019" in text for text in paragraphs)
        # Per-mast totals were subsumed by the per-mast tables.
        assert not any("检验共剔除" in text for text in paragraphs)

        tables = [block for block in ir.body if isinstance(block, TypstTable)]
        assert len(tables) == 3  # rules + one violations table per mast

        rules_table = tables[0]
        assert rules_table.headers == ["规则名称", "传感器类型", "适用高度(m)", "判定条件"]
        rows = {row[0]: row for row in rules_table.data}
        assert rows["风速范围检查"][1] == "风速"
        assert rows["风速范围检查"][2] == "全部高度"
        assert rows["风速范围检查"][3] == "合理范围 [0, 30]"
        assert rows["高风速层差检查"][2] == "≥70m"

        m1_table = tables[1]
        assert m1_table.caption == "M1 分规则剔除点数统计"
        assert m1_table.data == [
            ["140m 风速(N, 均值)", "风速结冰检测", "30"],
            ["140m 风速(N, 均值)", "风速范围检查", "50"],
            ["140m 风向(均值)", "风向范围检查", "40"],
        ]

    def test_rows_sort_by_type_height_then_rule_name(self, tmp_path):
        project = _project(
            tmp_path,
            with_stats=False,
            extra_stats={"M2": VIOLATIONS_YAML_M2},
        )
        section = CleaningRulesSection.from_inputs(
            [_input("M2", sensors=M2_SENSORS)], project_dir=project
        )
        ir = section.render_ir(tmp_path)
        tables = [block for block in ir.body if isinstance(block, TypstTable)]
        assert len(tables) == 2  # rules + M2 violations
        assert tables[1].data == [
            ["30m 风速(ESE, 均值)", "范围检查", "1"],
            ["70m 风速(ESE, 均值)", "高风速层差检查", "1"],
            ["70m 风速(ESE, 均值)", "风速范围检查", "5"],
            ["120m 风向(N, 均值)", "风向范围检查", "4"],
            ["5m 温度(均值)", "范围检查", "1"],
            ["10m 气压(均值)", "范围检查", "2"],
            ["Unknown_99", "范围检查", "1"],
        ]

    def test_missing_stats_yaml_renders_note_and_no_table(self, tmp_path):
        section = CleaningRulesSection.from_inputs(
            [_input("M1"), _input("M2", sensors=M2_SENSORS)],
            project_dir=_project(tmp_path),
        )
        ir = section.render_ir(tmp_path)
        paragraphs = [
            block.text for block in ir.body if isinstance(block, TypstParagraph)
        ]
        assert any(
            "M2：未找到 process-stats/process-clean-M2.yaml，剔除统计从略。"
            in text
            for text in paragraphs
        )
        tables = [block for block in ir.body if isinstance(block, TypstTable)]
        assert len(tables) == 2  # rules + M1 only
        assert tables[1].caption == "M1 分规则剔除点数统计"

    def test_column_without_metadata_falls_back_to_raw_name(self, tmp_path):
        section = CleaningRulesSection.from_inputs(
            [_input("M1")], project_dir=_project(tmp_path)
        )
        ir = section.render_ir(tmp_path)
        tables = [block for block in ir.body if isinstance(block, TypstTable)]
        m1_table = tables[1]
        assert [row[0] for row in m1_table.data] == [
            "140m 风速(N, 均值)",
            "140m 风速(N, 均值)",
            "140m 风向(均值)",
        ]

    def test_without_stage_sensors_labels_fall_back_to_raw_names(self, tmp_path):
        section = CleaningRulesSection.from_inputs(
            [_input("M1", sensors=[])], project_dir=_project(tmp_path)
        )
        ir = section.render_ir(tmp_path)
        tables = [block for block in ir.body if isinstance(block, TypstTable)]
        # No metadata → 其他 bucket, ordered by column name then rule.
        assert [row[0] for row in tables[1].data] == [
            "WD_140",
            "WS_140_N",
            "WS_140_N",
        ]

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
