"""Tests for the 2.3.2 cleaning overview section (flow intro + coverage).

Covers: expected-points math flowing into the table, percentage formatting,
missing-stage guards, dual-channel and fallback counting, multi-mast table
assembly, and end-to-end section rendering from synthetic inputs.
"""

from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
from cleanmast.shared.timeseries import SensorColumn, TimeRange, TimeSeriesData
from cleanmast.shared.timeseries.time_series_source import TimeSeriesSource
from cleanmast.subdomains.reporting.model.analysis_input import (
    CleaningAnalysisPayload,
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.model.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.reporting.subdomains.cleaning import (
    CleaningOverviewSection,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model import (
    FLOW_INTRO_TEXT,
)

# One hour on the inclusive 10-minute grid: 00:00 … 01:00 → 7 points.
WINDOW_START = datetime(2025, 6, 1, 0, 0)
WINDOW_END = datetime(2025, 6, 1, 1, 0)
WINDOW = TimeRange(min=WINDOW_START, max=WINDOW_END)
TIMESTAMPS = [WINDOW_START + timedelta(minutes=10 * i) for i in range(7)]

# Column layout: idx 2 应有点数, 3 原始点数, 4 原始占比, 5 清洗后点数,
# 6 清洗后占比, 7 插补后点数, 8 插补后占比.
IDX_EXPECTED = 2
IDX_RAW = 3
IDX_RAW_PCT = 4
IDX_CLEAN = 5
IDX_CLEAN_PCT = 6
IDX_FINAL = 7
IDX_FINAL_PCT = 8


def _sensor(column: str, height: float) -> SensorColumn:
    return SensorColumn(
        column_name=column,
        sensor_type="WindSpeed",
        sensor_direction="",
        height=height,
        stat_type="avg",
        unit="m/s",
    )


def _stage(
    sensors: list[SensorColumn],
    columns: dict[str, list[float | None]],
) -> TimeSeriesData:
    df = pl.DataFrame({"timestamp": TIMESTAMPS, **columns})
    return TimeSeriesData(df=df, sensors=sensors)


def _values(valid: int, total: int = 7) -> list[float | None]:
    """`valid` non-null values followed by nulls up to `total`."""
    return [6.0] * valid + [None] * (total - valid)


def _item(
    mast_name: str,
    *,
    heights: list[float],
    raw: TimeSeriesData | None,
    clean: TimeSeriesData | None,
    shading: TimeSeriesData | None,
    final: TimeSeriesData | None = None,
    with_payload: bool = True,
    window: TimeRange = WINDOW,
) -> SingleMastAnalysisInput:
    if final is None:
        final = _stage(
            [_sensor(f"ws_{h}", h) for h in heights],
            {f"ws_{h}": _values(7) for h in heights},
        )
    payload = (
        CleaningAnalysisPayload(
            raw_input=TimeSeriesSource(data=f"./raw/{mast_name}.parquet"),
            clean_input=TimeSeriesSource(data=f"./clean/{mast_name}.parquet"),
            tower_shading_input=TimeSeriesSource(
                data=f"./tower-shading/{mast_name}.parquet"
            ),
            cleaning_heights=heights,
            analysis_window=window,
            raw_series=raw,
            clean_series=clean,
            tower_shading_series=shading,
        )
        if with_payload
        else None
    )
    return SingleMastAnalysisInput(
        time_series=final,
        parameters=AnalysisParameters(
            air_density=1.225,
            extreme_wind_10min_heights=[],
            extreme_wind_3s_heights=[],
            extreme_wind_gust_factors=[],
        ),
        mast_name=mast_name,
        cleaning_payload=payload,
    )


def _m1_item() -> SingleMastAnalysisInput:
    """M1 at 140m: raw 4/7 valid, clean 6/7, no shading, final 7/7."""
    return _item(
        "M1",
        heights=[140.0],
        raw=_stage([_sensor("ws_140", 140.0)], {"ws_140": _values(4)}),
        clean=_stage([_sensor("ws_140", 140.0)], {"ws_140": _values(6)}),
        shading=None,
    )


def _coverage_table(items: list[SingleMastAnalysisInput]) -> pl.DataFrame:
    """Build the section and return the coverage atom's rendered table."""
    section = CleaningOverviewSection.from_inputs(items)
    coverage_atoms = [
        a for a in section._atoms if type(a).__name__ == "CleaningCoverageAtom"
    ]
    assert len(coverage_atoms) == 1
    table = coverage_atoms[0].renderTable()
    assert table is not None
    return table


class TestCoverageTable:
    def test_expected_points_and_stage_counts_in_table(self):
        # 1h inclusive window → 7 expected; counts and one-decimal
        # percentages flow from the stage series into the cells.
        table = _coverage_table([_m1_item()])
        assert table.headers == [
            "测风塔",
            "高度(m)",
            "应有点数",
            "原始点数",
            "占比(%)",
            "清洗后点数",
            "占比(%)",
            "插补后点数",
            "占比(%)",
        ]
        assert len(table.data) == 1
        row = table.data[0]
        assert row[0] == "M1"
        assert row[1] == "140m"
        assert row[IDX_EXPECTED] == "7"
        assert row[IDX_RAW] == "4"
        assert row[IDX_RAW_PCT] == "57.1"
        assert row[IDX_CLEAN] == "6"
        assert row[IDX_CLEAN_PCT] == "85.7"
        assert row[IDX_FINAL] == "7"
        assert row[IDX_FINAL_PCT] == "100.0"

    def test_percentage_rounding_one_decimal(self):
        # 3/7 = 42.857…% → 42.9; 5/7 = 71.428…% → 71.4.
        item = _item(
            "M1",
            heights=[140.0],
            raw=_stage([_sensor("ws_140", 140.0)], {"ws_140": _values(3)}),
            clean=_stage([_sensor("ws_140", 140.0)], {"ws_140": _values(5)}),
            shading=None,
            final=_stage([_sensor("ws_140", 140.0)], {"ws_140": _values(3)}),
        )
        row = _coverage_table([item]).data[0]
        assert row[IDX_RAW_PCT] == "42.9"
        assert row[IDX_CLEAN_PCT] == "71.4"
        assert row[IDX_FINAL_PCT] == "42.9"

    def test_missing_stage_renders_em_dash(self):
        # No raw series and neither clean nor shading → em-dash cells.
        item = _item(
            "M1",
            heights=[140.0],
            raw=None,
            clean=None,
            shading=None,
        )
        row = _coverage_table([item]).data[0]
        assert row[IDX_RAW] == "—"
        assert row[IDX_RAW_PCT] == "—"
        assert row[IDX_CLEAN] == "—"
        assert row[IDX_CLEAN_PCT] == "—"
        # The final stage is always present (reconstruct-meso input).
        assert row[IDX_FINAL] == "7"
        assert row[IDX_FINAL_PCT] == "100.0"

    def test_clean_stage_prefers_tower_shading_output(self):
        # Shading present (5 valid) wins over the process-clean output
        # (6 valid): 清洗后 counts the latest pre-imputation stage.
        item = _item(
            "M1",
            heights=[140.0],
            raw=_stage([_sensor("ws_140", 140.0)], {"ws_140": _values(7)}),
            clean=_stage([_sensor("ws_140", 140.0)], {"ws_140": _values(6)}),
            shading=_stage(
                [_sensor("ws_140_ts", 140.0)],
                {"ws_140_ts": _values(5)},
            ),
        )
        row = _coverage_table([item]).data[0]
        assert row[IDX_CLEAN] == "5"
        assert row[IDX_CLEAN_PCT] == "71.4"

    def test_dual_channel_height_counts_max(self):
        # Raw carries two channels at 140m (2 and 5 valid) → availability
        # takes the better channel.
        raw = _stage(
            [_sensor("ws_140_a", 140.0), _sensor("ws_140_b", 140.0)],
            {"ws_140_a": _values(2), "ws_140_b": _values(5)},
        )
        item = _item(
            "M1",
            heights=[140.0],
            raw=raw,
            clean=None,
            shading=None,
        )
        row = _coverage_table([item]).data[0]
        assert row[IDX_RAW] == "5"
        assert row[IDX_RAW_PCT] == "71.4"

    def test_height_missing_in_stage_counts_zero(self):
        # Stage loaded but lacks the 120m channel → 0 valid points, not
        # em-dash (the stage exists; the height has no data).
        raw = _stage([_sensor("ws_140", 140.0)], {"ws_140": _values(7)})
        item = _item(
            "M1",
            heights=[120.0, 140.0],
            raw=raw,
            clean=None,
            shading=None,
        )
        table = _coverage_table([item])
        assert table.data[0][1] == "120m"
        assert table.data[0][IDX_RAW] == "0"
        assert table.data[0][IDX_RAW_PCT] == "0.0"
        assert table.data[1][1] == "140m"
        assert table.data[1][IDX_RAW] == "7"

    def test_multi_mast_rows_grouped_in_input_order(self):
        m1 = _m1_item()
        m2_no_payload = _item(
            "M2",
            heights=[140.0],
            raw=None,
            clean=None,
            shading=None,
            with_payload=False,
        )
        m3 = _item(
            "M3",
            heights=[120.0],
            raw=_stage([_sensor("ws_120", 120.0)], {"ws_120": _values(7)}),
            clean=_stage([_sensor("ws_120", 120.0)], {"ws_120": _values(7)}),
            shading=None,
        )
        table = _coverage_table([m1, m2_no_payload, m3])
        # Payload-less masts are skipped; remaining masts keep input order,
        # mast name repeated per height row.
        assert [r[0] for r in table.data] == ["M1", "M3"]
        assert [r[1] for r in table.data] == ["140m", "120m"]
        assert all(len(r) == 9 for r in table.data)

    def test_table_caption(self):
        table = _coverage_table([_m1_item()])
        assert table.caption == "数据清洗与插补各阶段数据点统计表"


class TestSectionRendering:
    def test_render_ir_orders_intro_stats_table(self, tmp_path: Path):
        section = CleaningOverviewSection.from_inputs([_m1_item()])
        ir = section.render_ir(tmp_path)
        assert ir.heading.text == "数据清洗与插补总体概况"
        paragraphs = [b for b in ir.body if hasattr(b, "text")]
        tables = [b for b in ir.body if hasattr(b, "headers")]
        assert len(paragraphs) == 2
        assert paragraphs[0].text == FLOW_INTRO_TEXT
        assert FLOW_INTRO_TEXT.startswith("数据处理按以下流程进行")
        assert "GB/T 37523-2019" in FLOW_INTRO_TEXT
        assert "NB/T 31147-2018" in FLOW_INTRO_TEXT
        assert "2025-06-01 至 2025-06-01" in paragraphs[1].text
        assert "应有数据点 7 个" in paragraphs[1].text
        assert paragraphs[1].text.endswith("各塔主测风层数据点统计见下表。")
        assert len(tables) == 1

    def test_distinct_windows_get_per_mast_clauses(self, tmp_path: Path):
        june = _m1_item()
        july_window = TimeRange(min=datetime(2025, 7, 1), max=datetime(2025, 7, 1, 1, 0))
        july = _item(
            "M2",
            heights=[140.0],
            raw=None,
            clean=None,
            shading=None,
            window=july_window,
        )
        section = CleaningOverviewSection.from_inputs([june, july])
        ir = section.render_ir(tmp_path)
        paragraphs = [b for b in ir.body if hasattr(b, "text")]
        stats = paragraphs[1].text
        assert "M1 以代表年时间范围" in stats
        assert "M2 以代表年时间范围" in stats
        assert "2025-06-01" in stats and "2025-07-01" in stats
        assert stats.endswith("各塔主测风层数据点统计见下表。")

    def test_empty_items_render_intro_only(self, tmp_path: Path):
        section = CleaningOverviewSection.from_inputs([])
        ir = section.render_ir(tmp_path)
        paragraphs = [b for b in ir.body if hasattr(b, "text")]
        tables = [b for b in ir.body if hasattr(b, "headers")]
        assert [p.text for p in paragraphs] == [FLOW_INTRO_TEXT]
        assert tables == []

    def test_mast_without_payload_renders_others(self, tmp_path: Path):
        section = CleaningOverviewSection.from_inputs([
            _m1_item(),
            _item(
                "M2",
                heights=[140.0],
                raw=None,
                clean=None,
                shading=None,
                with_payload=False,
            ),
        ])
        ir = section.render_ir(tmp_path)
        tables = [b for b in ir.body if hasattr(b, "headers")]
        assert len(tables) == 1
        assert [r[0] for r in tables[0].data] == ["M1"]
