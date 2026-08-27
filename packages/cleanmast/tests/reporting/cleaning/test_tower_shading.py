"""Tests for 2.3.4 塔影效应处理 (tower shading) compute, atoms, and section."""

from datetime import datetime
from pathlib import Path

import polars as pl
import pytest
from cleanmast.shared.timeseries import SensorColumn, TimeRange, TimeSeriesData
from cleanmast.shared.timeseries.time_series_source import TimeSeriesSource
from cleanmast.subdomains.reporting.model.analysis_input import (
    CleaningAnalysisPayload,
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.model.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.reporting.subdomains.cleaning import TowerShadingSection
from cleanmast.subdomains.reporting.subdomains.cleaning.assemble import (
    build_tower_shading_atoms,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.compute.tower_shading import (
    find_avg_wind_direction_column,
    find_dual_channel_heights,
    overall_weighted_row,
    tower_shading_comparison_frame,
    tower_shading_sector_stats,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model import (
    TOWER_SHADING_METHOD_TEXT,
    TOWER_SHADING_METHOD_TEXT_NO_TABLE,
    TowerShadingMethodAtom,
    TowerShadingSectorTableAtom,
    TowerShadingSectorTableAtomMeta,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model.schemas import (
    TowerShadingSectorSchema,
)
from typst_ir.nodes import TypstEquation, TypstTable

WD_COL = "WindDirection_100m_N_avg [deg]"
ESE_COL = "WindSpeed_120m_ESE_avg [m/s]"
WNW_COL = "WindSpeed_120m_WNW_avg [m/s]"
SOLO_COL = "WindSpeed_100m_ESE_avg [m/s]"
MERGED_COL = "WindSpeed_120m_avg [m/s]"

WINDOW = TimeRange(
    min=datetime(2025, 1, 1, 0, 0),
    max=datetime(2025, 1, 1, 0, 40),
)


def _sensor(column: str, height: float, stype: str, direction: str = "") -> SensorColumn:
    return SensorColumn(
        column_name=column,
        sensor_type=stype,
        sensor_direction=direction,
        height=height,
        stat_type="avg",
        unit="m/s" if stype == "WindSpeed" else "deg",
    )


def _clean_sensors() -> list[SensorColumn]:
    return [
        _sensor(ESE_COL, 120.0, "WindSpeed", "ESE"),
        _sensor(WNW_COL, 120.0, "WindSpeed", "WNW"),
        _sensor(SOLO_COL, 100.0, "WindSpeed", "ESE"),
        _sensor(WD_COL, 100.0, "WindDirection", "N"),
    ]


def _clean_df() -> pl.DataFrame:
    """Four in-window rows plus one out-of-window and one null-WD row.

    Merged (after) values are the per-row maximum of the two channels —
    the Julia tower-shading rule.
    """
    rows = {
        "timestamp": [
            datetime(2025, 1, 1, 0, 0),
            datetime(2025, 1, 1, 0, 10),
            datetime(2025, 1, 1, 0, 20),
            datetime(2025, 1, 1, 0, 30),
            datetime(2025, 1, 1, 1, 0),  # outside the window
            datetime(2025, 1, 1, 0, 40),  # null direction → excluded
        ],
        WD_COL: [0.0, 0.0, 0.0, 90.0, 0.0, None],
        ESE_COL: [6.0, 8.0, 7.0, 10.0, 20.0, None],
        WNW_COL: [5.0, 9.0, 7.0, 4.0, 20.0, 3.0],
        SOLO_COL: [4.0, 4.0, 4.0, 4.0, 4.0, 4.0],
    }
    return pl.DataFrame(rows)


def _shading_sensors() -> list[SensorColumn]:
    return [
        _sensor(MERGED_COL, 120.0, "WindSpeed", "N/A"),
        _sensor(SOLO_COL, 100.0, "WindSpeed", "ESE"),
        _sensor(WD_COL, 100.0, "WindDirection", "N"),
    ]


def _shading_df(clean: pl.DataFrame) -> pl.DataFrame:
    """Tower-shading stage: dual channels replaced by their row maximum."""
    merged = pl.max_horizontal(clean[ESE_COL], clean[WNW_COL])
    return clean.drop(ESE_COL, WNW_COL).with_columns(
        merged.alias(MERGED_COL)
    )


def _ts(df: pl.DataFrame, sensors: list[SensorColumn]) -> TimeSeriesData:
    return TimeSeriesData(df=df, sensors=sensors)


def _input(
    mast_name: str = "M1",
    *,
    with_shading: bool = True,
    clean_sensors: list[SensorColumn] | None = None,
    clean_df: pl.DataFrame | None = None,
    shading_sensors: list[SensorColumn] | None = None,
    shading_df: pl.DataFrame | None = None,
    with_payload: bool = True,
    cleaning_heights: list[float] | None = None,
) -> SingleMastAnalysisInput:
    final_df = pl.DataFrame({"timestamp": [datetime(2025, 1, 1)]})
    payload = None
    if with_payload:
        payload = CleaningAnalysisPayload(
            raw_input=TimeSeriesSource(data="./raw/M1.parquet"),
            clean_input=TimeSeriesSource(data="./clean/M1.parquet"),
            tower_shading_input=(
                TimeSeriesSource(data="./tower-shading/M1.parquet")
                if with_shading else None
            ),
            cleaning_heights=cleaning_heights or [120.0, 100.0],
            analysis_window=WINDOW,
            clean_series=_ts(
                clean_df if clean_df is not None else _clean_df(),
                clean_sensors if clean_sensors is not None else _clean_sensors(),
            ),
            tower_shading_series=(
                _ts(
                    shading_df
                    if shading_df is not None
                    else _shading_df(_clean_df()),
                    shading_sensors
                    if shading_sensors is not None
                    else _shading_sensors(),
                )
                if with_shading else None
            ),
        )
    return SingleMastAnalysisInput(
        time_series=_ts(final_df, [_sensor("ws", 120.0, "WindSpeed")]),
        parameters=AnalysisParameters(
            air_density=1.225,
            extreme_wind_10min_heights=[],
            extreme_wind_3s_heights=[],
            extreme_wind_gust_factors=[],
        ),
        mast_name=mast_name,
        cleaning_payload=payload,
    )


def _dual():
    return find_dual_channel_heights(
        _clean_df(), _shading_df(_clean_df()),
        _clean_sensors(), _shading_sensors(),
    )


class TestFindDualChannelHeights:
    def test_detects_merged_height_with_channel_labels(self):
        duals = _dual()
        assert len(duals) == 1
        d = duals[0]
        assert d.height == 120.0
        assert d.merged_column == MERGED_COL
        assert d.source_columns == [ESE_COL, WNW_COL]
        assert d.channel_labels == ["ESE", "WNW"]
        assert d.is_dual_channel

    def test_no_merged_column_means_no_dual_height(self):
        # Shading identical to clean (no tower-shading correction applied).
        duals = find_dual_channel_heights(
            _clean_df(), _clean_df(), _clean_sensors(), _clean_sensors(),
        )
        assert duals == []

    def test_single_channel_height_is_not_dual(self):
        # 100 m survives both stages unchanged → not a corrected height.
        assert all(d.height != 100.0 for d in _dual())

    def test_three_channels_at_one_height_are_not_dual(self):
        extra_col = "WindSpeed_120m_NNE_avg [m/s]"
        sensors = [
            *_clean_sensors(),
            _sensor(extra_col, 120.0, "WindSpeed", "NNE"),
        ]
        df = _clean_df().with_columns(pl.lit(5.0).alias(extra_col))
        merged3 = (
            df
            .with_columns(
                pl.max_horizontal(
                    pl.col(ESE_COL), pl.col(WNW_COL), pl.col(extra_col),
                ).alias(MERGED_COL)
            )
            .select("timestamp", WD_COL, MERGED_COL)
        )
        duals = find_dual_channel_heights(
            df, merged3, sensors,
            [_sensor(MERGED_COL, 120.0, "WindSpeed")],
        )
        assert duals == []

    def test_missing_or_duplicate_directions_fall_back(self):
        sensors = [
            _sensor(ESE_COL, 120.0, "WindSpeed", ""),
            _sensor(WNW_COL, 120.0, "WindSpeed", ""),
            _sensor(SOLO_COL, 100.0, "WindSpeed", "ESE"),
            _sensor(WD_COL, 100.0, "WindDirection", "N"),
        ]
        duals = find_dual_channel_heights(
            _clean_df(), _shading_df(_clean_df()), sensors, _shading_sensors(),
        )
        assert duals[0].channel_labels == ["通道1", "通道2"]

        sensors_dup = [
            _sensor(ESE_COL, 120.0, "WindSpeed", "ESE"),
            _sensor(WNW_COL, 120.0, "WindSpeed", "ESE"),
            _sensor(SOLO_COL, 100.0, "WindSpeed", "ESE"),
            _sensor(WD_COL, 100.0, "WindDirection", "N"),
        ]
        duals = find_dual_channel_heights(
            _clean_df(), _shading_df(_clean_df()),
            sensors_dup, _shading_sensors(),
        )
        assert duals[0].channel_labels == ["通道1", "通道2"]


class TestTowerShadingSectorStats:
    def test_hand_computed_sector_means_and_counts(self):
        stats = tower_shading_sector_stats(
            _clean_df(), _shading_df(_clean_df()), _dual()[0], WD_COL, WINDOW,
        )
        rows = {r["sector"]: r for r in stats.iter_rows(named=True)}
        # Sector 1 (N): three in-window rows; null-WD row excluded.
        assert rows[1]["data_points"] == 3
        assert rows[1]["mean_before_1"] == pytest.approx(7.0)  # ESE 6,8,7
        assert rows[1]["mean_before_2"] == pytest.approx(7.0)  # WNW 5,9,7
        assert rows[1]["mean_after"] == pytest.approx(22.0 / 3)  # max 6,9,7
        # Sector 5 (E): one row.
        assert rows[5]["data_points"] == 1
        assert rows[5]["mean_before_1"] == pytest.approx(10.0)
        assert rows[5]["mean_before_2"] == pytest.approx(4.0)
        assert rows[5]["mean_after"] == pytest.approx(10.0)
        assert sorted(rows) == [1, 5]

    def test_clip_excludes_out_of_window_rows(self):
        stats = tower_shading_sector_stats(
            _clean_df(), _shading_df(_clean_df()), _dual()[0], WD_COL, WINDOW,
        )
        # The 01:00 row (wd 0, values 20) must not inflate sector 1.
        assert stats["data_points"].sum() == 4


class TestOverallWeightedRow:
    def test_sample_weighted_means(self):
        stats = tower_shading_sector_stats(
            _clean_df(), _shading_df(_clean_df()), _dual()[0], WD_COL, WINDOW,
        )
        overall = overall_weighted_row(stats)
        assert overall is not None
        assert overall["data_points"] == 4
        assert overall["mean_before_1"] == pytest.approx((7.0 * 3 + 10.0) / 4)
        assert overall["mean_before_2"] == pytest.approx((7.0 * 3 + 4.0) / 4)
        assert overall["mean_after"] == pytest.approx((22.0 + 10.0) / 4)

    def test_empty_stats_returns_none(self):
        assert overall_weighted_row(pl.DataFrame()) is None


class TestTowerShadingComparisonFrame:
    def test_signed_deltas_and_percentages(self):
        stats = tower_shading_sector_stats(
            _clean_df(), _shading_df(_clean_df()), _dual()[0], WD_COL, WINDOW,
        )
        frame = tower_shading_comparison_frame(stats)
        by_sector = {r["sector"]: r for r in frame.iter_rows(named=True)}

        # Sector 5: after 10 vs before1 10 (delta 0) and before2 4 (+6).
        assert by_sector["E"]["delta_1"] == pytest.approx(0.0)
        assert by_sector["E"]["delta_2"] == pytest.approx(6.0)
        assert by_sector["E"]["pct_1"] == pytest.approx(0.0)
        assert by_sector["E"]["pct_2"] == pytest.approx(1.5)  # +150 %

        # Sector 1: after 22/3 vs before 7 → positive delta.
        assert by_sector["N"]["delta_1"] == pytest.approx(22.0 / 3 - 7.0)

        # Overall row appended, weighted, flagged.
        overall = by_sector["总体平均(加权)"]
        assert overall["is_overall"] is True
        assert overall["data_points"] == 4
        assert overall["mean_after"] == pytest.approx(8.0)
        assert all(
            not r["is_overall"] for s, r in by_sector.items()
            if s != "总体平均(加权)"
        )

    def test_negative_delta_stays_signed(self):
        # Channel above the merged mean → after − before < 0.
        stats = pl.DataFrame({
            "sector": [1],
            "data_points": [2],
            "mean_before_1": [9.0],
            "mean_before_2": [5.0],
            "mean_after": [7.0],
        })
        frame = tower_shading_comparison_frame(stats)
        row = frame.row(0, named=True)
        assert row["delta_1"] == pytest.approx(-2.0)
        assert row["pct_1"] == pytest.approx(-2.0 / 9.0)
        assert row["delta_2"] == pytest.approx(2.0)

    def test_zero_before_mean_gives_null_pct(self):
        stats = pl.DataFrame({
            "sector": [1],
            "data_points": [1],
            "mean_before_1": [0.0],
            "mean_before_2": [2.0],
            "mean_after": [1.0],
        })
        frame = tower_shading_comparison_frame(stats)
        row = frame.row(0, named=True)
        assert row["pct_1"] is None
        assert row["pct_2"] == pytest.approx(-0.5)

    def test_empty_stats_yields_empty_frame(self):
        frame = tower_shading_comparison_frame(pl.DataFrame())
        assert frame.is_empty()


class TestSectorTableAtom:
    def test_headers_use_channel_identities_and_formatting(self):
        stats = tower_shading_sector_stats(
            _clean_df(), _shading_df(_clean_df()), _dual()[0], WD_COL, WINDOW,
        )
        frame = tower_shading_comparison_frame(stats)
        atom = TowerShadingSectorTableAtom.create(
            schema=TowerShadingSectorSchema,
            df=frame,
            meta=TowerShadingSectorTableAtomMeta(
                mast_name="M1",
                height=120.0,
                channel_1_label="ESE",
                channel_2_label="WNW",
            ),
        )
        table = atom.renderTable()
        assert table is not None
        assert table.headers[0] == "扇区"
        assert table.headers[2] == "ESE修正前均值(m/s)"
        assert table.headers[3] == "WNW修正前均值(m/s)"
        assert table.headers[8] == "WNW百分比(%)"
        assert table.caption == "M1 120m 塔影修正前后分扇区风速对比"
        # Sector E row: after 10.00, WNW delta +6.00, WNW pct +150.0.
        e_row = next(r for r in table.data if r[0] == "E")
        assert e_row[4] == "10.00"
        assert e_row[6] == "6.00"
        assert e_row[8] == "150.0"
        # Sector N delta 22/3 − 7 ≈ 0.33, two decimals.
        n_row = next(r for r in table.data if r[0] == "N")
        assert n_row[5] == "0.33"
        assert n_row[7] == "4.8"
        # Weighted overall row is last.
        assert table.data[-1][0] == "总体平均(加权)"

    def test_null_pct_renders_na(self):
        frame = pl.DataFrame({
            "sector": ["N"],
            "data_points": [1],
            "mean_before_1": [0.0],
            "mean_before_2": [2.0],
            "mean_after": [1.0],
            "delta_1": [1.0],
            "delta_2": [-1.0],
            "pct_1": [None],
            "pct_2": [-0.5],
            "is_overall": [False],
        })
        atom = TowerShadingSectorTableAtom.create(
            schema=TowerShadingSectorSchema,
            df=frame,
            meta=TowerShadingSectorTableAtomMeta(
                mast_name="M1", height=120.0,
            ),
        )
        row = atom.renderTable().data[0]
        assert row[7] == "N/A"
        assert row[8] == "-50.0"


class TestMethodTexts:
    def test_both_variants_keep_method_sentence_and_citation(self):
        for text in (TOWER_SHADING_METHOD_TEXT, TOWER_SHADING_METHOD_TEXT_NO_TABLE):
            assert (
                "依据《风电场工程风能资源测量与评估技术规范》（NB/T 31147-2018）"
                in text
            )
            assert "逐时刻取两通道较大值" in text

    def test_no_table_variant_states_all_heights_single_channel(self):
        # The no-table variant states the verified outcome (single channel
        # at every height, nothing corrected) instead of referencing a
        # comparison that does not exist.
        assert TOWER_SHADING_METHOD_TEXT_NO_TABLE.endswith(
            "经检验，各测风塔各高度层均为单通道风速传感器，不涉及塔影修正。"
        )
        assert "对比" not in TOWER_SHADING_METHOD_TEXT_NO_TABLE
        assert TOWER_SHADING_METHOD_TEXT.endswith("修正前后分扇区风速对比见下表。")


class TestTowerShadingSection:
    def test_renders_method_equation_and_table(self, tmp_path):
        section = TowerShadingSection.from_inputs([_input("M1")])
        ir = section.render_ir(Path(tmp_path))
        assert ir.heading.text == "塔影效应处理"

        paragraphs = [b for b in ir.body if hasattr(b, "text")]
        equations = [b for b in ir.body if isinstance(b, TypstEquation)]
        tables = [b for b in ir.body if isinstance(b, TypstTable)]

        assert len(paragraphs) == 1
        assert paragraphs[0].text == TOWER_SHADING_METHOD_TEXT
        assert "NB/T 31147-2018" in paragraphs[0].text
        assert len(equations) == 1
        assert equations[0].latex == "V_i = max(V_i^1, V_i^2)"
        assert equations[0].display is True
        assert len(tables) == 1
        assert tables[0].headers[2] == "ESE修正前均值(m/s)"
        # Equation sits between the method paragraph and the table.
        assert ir.body.index(paragraphs[0]) < ir.body.index(equations[0])
        assert ir.body.index(equations[0]) < ir.body.index(tables[0])

    def test_mast_without_tower_shading_stage_keeps_method_text_only(
        self, tmp_path,
    ):
        section = TowerShadingSection.from_inputs(
            [_input("M1", with_shading=False)]
        )
        ir = section.render_ir(Path(tmp_path))
        assert not [b for b in ir.body if isinstance(b, TypstTable)]
        assert any(
            b.text == TOWER_SHADING_METHOD_TEXT_NO_TABLE
            for b in ir.body if hasattr(b, "text")
        )

    def test_mast_without_payload_is_skipped(self, tmp_path):
        section = TowerShadingSection.from_inputs([_input("M1", with_payload=False)])
        ir = section.render_ir(Path(tmp_path))
        assert not [b for b in ir.body if isinstance(b, TypstTable)]

    def test_no_dual_channels_omits_table(self, tmp_path):
        # Shading stage identical to clean → no merged column, no table;
        # the method text states the verified single-channel outcome.
        item = _input(
            "M1",
            shading_df=_clean_df(),
            shading_sensors=_clean_sensors(),
        )
        section = TowerShadingSection.from_inputs([item])
        ir = section.render_ir(Path(tmp_path))
        assert not [b for b in ir.body if isinstance(b, TypstTable)]
        assert any(
            b.text == TOWER_SHADING_METHOD_TEXT_NO_TABLE
            for b in ir.body if hasattr(b, "text")
        )

    def test_dual_outside_cleaning_heights_uses_full_scan_for_wording(self):
        # The wording decision scans all WS-avg heights: a dual channel
        # outside cleaning_heights suppresses the no-dual-channel sentence
        # even though its sector table is filtered out.
        item = _input("M1", cleaning_heights=[100.0])
        atoms = build_tower_shading_atoms([item])
        assert not [a for a in atoms if isinstance(a, TowerShadingSectorTableAtom)]
        method = next(a for a in atoms if isinstance(a, TowerShadingMethodAtom))
        assert method.renderSummary()[0].text == TOWER_SHADING_METHOD_TEXT

    def test_multiple_masts_render_one_table_each(self, tmp_path):
        section = TowerShadingSection.from_inputs(
            [_input("M1"), _input("M2")]
        )
        ir = section.render_ir(Path(tmp_path))
        tables = [b for b in ir.body if isinstance(b, TypstTable)]
        assert len(tables) == 2
        assert tables[0].caption.startswith("M1 ")
        assert tables[1].caption.startswith("M2 ")


class TestFindAvgWindDirectionColumn:
    def test_picks_highest_direction_sensor(self):
        sensors = [
            _sensor("WindDirection_10m_N_avg [deg]", 10.0, "WindDirection", "N"),
            _sensor(WD_COL, 100.0, "WindDirection", "N"),
        ]
        assert find_avg_wind_direction_column(sensors) == WD_COL

    def test_none_without_direction_sensors(self):
        assert find_avg_wind_direction_column(_clean_sensors()[:2]) is None
