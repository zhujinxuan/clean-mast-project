"""Tests for the imputation subsections (2.3.5 同塔 / 2.3.6 异塔 / 2.3.7 中尺度)."""

from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from cleanmast.shared.timeseries import SensorColumn, TimeRange, TimeSeriesData
from cleanmast.subdomains.reporting.model.analysis_input import (
    CleaningAnalysisPayload,
    RepresentativeYearCalibrationPayload,
    SingleMastAnalysisInput,
)
from cleanmast.subdomains.reporting.model.analysis_parameters import (
    AnalysisParameters,
)
from cleanmast.subdomains.reporting.subdomains.cleaning import (
    ImputationCrossMastSection,
    ImputationMesoSection,
    ImputationSameTowerSection,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.compute.scatter_pairs import (
    MIN_PAIRS,
    analyze_cross_mast,
    analyze_meso,
    analyze_same_tower,
    panel_stats,
    tidy_pairs,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model import (
    CorrelationLongSchema,
    CorrelationMatrixAtom,
    CorrelationMatrixAtomMeta,
    ScatterRegressionAtom,
)
from cleanmast.subdomains.reporting.subdomains.cleaning.model.scatter_regression_atom import (
    annotation_lines,
)
from typst_ir import TypstFigure, TypstTable

WINDOW = TimeRange(min=datetime(2025, 1, 1), max=datetime(2025, 12, 31))


def _sensor(column: str, height: float) -> SensorColumn:
    return SensorColumn(
        column_name=column,
        sensor_type="WindSpeed",
        sensor_direction="",
        height=height,
        stat_type="avg",
        unit="m/s",
    )


def _ten_minute_grid(
    n: int, start: datetime = datetime(2025, 1, 1)
) -> list[datetime]:
    return [start + timedelta(minutes=10 * i) for i in range(n)]


def _stage_series(
    columns: dict[str, list[float]],
    timestamps: list[datetime],
    heights: list[float],
) -> TimeSeriesData:
    """Corrected-stage stand-in: one WS avg column per height."""
    df = pl.DataFrame({"timestamp": timestamps, **columns}).with_columns(
        pl.col(c).cast(pl.Float64) for c in columns
    )
    sensors = [_sensor(col, height) for col, height in zip(columns, heights)]
    return TimeSeriesData(df=df, sensors=sensors)


def _item(
    mast_name: str,
    stage: TimeSeriesData | None,
    cleaning_heights: list[float],
    meso_payload: RepresentativeYearCalibrationPayload | None = None,
    stage_field: str = "clean_series",
) -> SingleMastAnalysisInput:
    payload = None
    if stage is not None:
        payload = CleaningAnalysisPayload(
            raw_input=None,
            clean_input=None,
            tower_shading_input=None,
            cleaning_heights=cleaning_heights,
            analysis_window=WINDOW,
            **{stage_field: stage},
        )
    return SingleMastAnalysisInput(
        time_series=TimeSeriesData(
            df=pl.DataFrame(
                {"timestamp": stage.df["timestamp"] if stage else []}
            ),
            sensors=[],
        ),
        parameters=AnalysisParameters(
            air_density=1.225,
            extreme_wind_10min_heights=[],
            extreme_wind_3s_heights=[],
            extreme_wind_gust_factors=[],
        ),
        mast_name=mast_name,
        cleaning_payload=payload,
        representative_year_calibration_payload=meso_payload,
    )


def _meso_payload(
    values: list[float],
    timestamps: list[datetime],
    meso_name: str = "ERA5",
    sampling_period: str = "10min",
) -> RepresentativeYearCalibrationPayload:
    meso = TimeSeriesData(
        df=pl.DataFrame({"timestamp": timestamps, "era5_ws": values}).with_columns(
            pl.col("era5_ws").cast(pl.Float64)
        ),
        sensors=[_sensor("era5_ws", 100.0)],
    )
    return RepresentativeYearCalibrationPayload(
        meso_time_series=meso,
        meso_name=meso_name,
        sampling_period=sampling_period,
        rep_year_start=WINDOW.min,
        rep_year_end=WINDOW.max,
    )


def _panel_by_labels(panels: pl.DataFrame, x_label: str, y_label: str) -> dict:
    rows = panels.filter(
        (pl.col("x_label") == x_label) & (pl.col("y_label") == y_label)
    )
    assert rows.height == 1
    return rows.iter_rows(named=True).__next__()


# ── Panel stats on a known synthetic pair ───────────────────────────────


class TestPanelStatsKnownPair:
    def test_exact_linear_relation(self):
        """y = 2x + 1 exactly → slope 2, intercept 1, r 1, RMSE 0."""
        pairs = tidy_pairs(
            pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [3.0, 5.0, 7.0, 9.0]}),
            "x",
            "y",
            "B",
            "A",
        )
        row = panel_stats(pairs).iter_rows(named=True).__next__()
        assert row["slope"] == pytest.approx(2.0)
        assert row["intercept"] == pytest.approx(1.0)
        assert row["r"] == pytest.approx(1.0)
        assert row["rmse"] == pytest.approx(0.0, abs=1e-12)
        assert row["n_pairs"] == 4

    def test_annotation_lines_format(self):
        lines = annotation_lines(slope=0.97, intercept=0.3, r=0.9804, rmse=0.36)
        assert lines == ["r=0.980  RMSE=0.36m/s", "y=0.97x+0.30"]

    def test_annotation_lines_negative_intercept(self):
        lines = annotation_lines(slope=1.05, intercept=-0.42, r=0.958, rmse=0.53)
        assert lines[1] == "y=1.05x-0.42"

    def test_annotation_lines_unfitted(self):
        assert annotation_lines(None, None, 0.5, 0.5) == []


# ── 2.3.5 同塔 ──────────────────────────────────────────────────────────


class TestSameTower:
    def _three_height_item(self) -> SingleMastAnalysisInput:
        n = 50
        rng = np.random.default_rng(11)
        base = rng.normal(8, 2, n).clip(0.5)
        stage = _stage_series(
            {
                "ws_120": list(base),
                "ws_140": list(2 * base + 1),
                "ws_160": list(0.5 * base + 2),
            },
            _ten_minute_grid(n),
            heights=[120.0, 140.0, 160.0],
        )
        return _item("M1", stage, [120.0, 140.0, 160.0])

    def test_matrix_symmetry_and_diagonal(self):
        result = analyze_same_tower([self._three_height_item()])[0]
        matrix = {
            (r["x_label"], r["y_label"]): r["r"]
            for r in result.matrix_long.iter_rows(named=True)
        }
        labels = ["120m", "140m", "160m"]
        assert result.labels == labels
        # full square with exact-1 diagonal
        assert set(matrix) == {(x, y) for x in labels for y in labels}
        for label in labels:
            assert matrix[(label, label)] == 1.0
        # symmetric off-diagonal
        for x in labels:
            for y in labels:
                assert matrix[(x, y)] == pytest.approx(matrix[(y, x)])

    def test_upper_triangle_regression_values(self):
        result = analyze_same_tower([self._three_height_item()])[0]
        # panel regresses y=120m on x=140m: base = (ws_140 - 1) / 2
        panel = _panel_by_labels(result.panels, "140m", "120m")
        assert panel["slope"] == pytest.approx(0.5)
        assert panel["intercept"] == pytest.approx(-0.5)
        assert panel["r"] == pytest.approx(1.0)
        assert panel["rmse"] == pytest.approx(0.0, abs=1e-9)
        assert panel["n_pairs"] == 50
        assert result.panels.height == 3  # C(3,2) upper-triangle pairs

    def test_tower_shading_preferred_over_clean(self):
        """tower_shading_series wins when both stages are present."""
        n = 10
        rng = np.random.default_rng(3)
        base = rng.normal(8, 2, n).clip(0.5)
        shading = _stage_series(
            {"ws_120": list(base), "ws_140": list(base + 1.0)},
            _ten_minute_grid(n),
            heights=[120.0, 140.0],
        )
        clean = _stage_series(
            {"ws_120": list(base), "ws_140": list(2 * base + 5)},
            _ten_minute_grid(n),
            heights=[120.0, 140.0],
        )
        item = _item("M1", clean, [120.0, 140.0])
        both = replace(
            item,
            cleaning_payload=replace(
                item.cleaning_payload, tower_shading_series=shading
            ),
        )
        panel = analyze_same_tower([both])[0].panels
        # shading relation: y(120) on x(140) → y = x − 1
        row = _panel_by_labels(panel, "140m", "120m")
        assert row["slope"] == pytest.approx(1.0)
        assert row["intercept"] == pytest.approx(-1.0)

    def test_falls_back_to_clean_series(self):
        n = 10
        rng = np.random.default_rng(3)
        base = rng.normal(8, 2, n).clip(0.5)
        clean = _stage_series(
            {"ws_120": list(base), "ws_140": list(2 * base + 5)},
            _ten_minute_grid(n),
            heights=[120.0, 140.0],
        )
        result = analyze_same_tower([_item("M1", clean, [120.0, 140.0])])[0]
        # clean relation: y(120) on x(140) → y = (x − 5) / 2
        row = _panel_by_labels(result.panels, "140m", "120m")
        assert row["slope"] == pytest.approx(0.5)
        assert row["intercept"] == pytest.approx(-2.5)

    def test_skips_mast_with_single_height(self):
        n = 10
        stage = _stage_series(
            {"ws_120": [7.0] * n}, _ten_minute_grid(n), heights=[120.0]
        )
        assert analyze_same_tower([_item("M1", stage, [120.0])]) == []

    def test_skips_mast_without_payload(self):
        assert analyze_same_tower([_item("M1", None, [120.0, 140.0])]) == []

    def test_skips_mast_without_stage_series(self):
        item = _item("M1", None, [120.0, 140.0])
        no_stage = replace(
            item,
            cleaning_payload=CleaningAnalysisPayload(
                raw_input=None,
                clean_input=None,
                tower_shading_input=None,
                cleaning_heights=[120.0, 140.0],
                analysis_window=WINDOW,
            ),
        )
        assert analyze_same_tower([no_stage]) == []

    def test_unrequested_heights_ignored(self):
        """Only cleaning_heights enter the exhibits, even with extra sensors."""
        n = 20
        rng = np.random.default_rng(5)
        base = rng.normal(8, 2, n).clip(0.5)
        stage = _stage_series(
            {
                "ws_80": list(base * 0.5),
                "ws_120": list(base),
                "ws_140": list(2 * base + 1),
            },
            _ten_minute_grid(n),
            heights=[80.0, 120.0, 140.0],
        )
        result = analyze_same_tower([_item("M1", stage, [120.0, 140.0])])[0]
        assert result.labels == ["120m", "140m"]
        assert "80m" not in result.matrix_long["x_label"].to_list()


# ── 2.3.6 异塔 ──────────────────────────────────────────────────────────


class TestCrossMast:
    def _two_masts(self, n: int = 30) -> list[SingleMastAnalysisInput]:
        rng = np.random.default_rng(13)
        base = rng.normal(8, 2, n).clip(0.5)
        stage_a = _stage_series(
            {"ws_120": list(base)}, _ten_minute_grid(n), heights=[120.0]
        )
        stage_b = _stage_series(
            {"ws_130": list(0.9 * base + 0.6)},
            _ten_minute_grid(n),
            heights=[130.0],
        )
        return [_item("M1", stage_a, [120.0]), _item("M2", stage_b, [130.0])]

    def test_ordered_pairs_both_directions(self):
        results = analyze_cross_mast(self._two_masts())
        assert [(r.mast_a, r.mast_b) for r in results] == [
            ("M1", "M2"),
            ("M2", "M1"),
        ]
        forward = _panel_by_labels(results[0].panels, "M2 130m", "M1 120m")
        assert forward["slope"] == pytest.approx(1 / 0.9, rel=1e-6)
        assert forward["n_pairs"] == 30

    def test_labels_carry_mast_prefix(self):
        results = analyze_cross_mast(self._two_masts())
        assert results[0].y_labels == ["M1 120m"]
        assert results[0].x_labels == ["M2 130m"]

    def test_disjoint_timestamps_skipped(self):
        n = 30
        rng = np.random.default_rng(13)
        base = rng.normal(8, 2, n).clip(0.5)
        stage_a = _stage_series(
            {"ws_120": list(base)}, _ten_minute_grid(n), heights=[120.0]
        )
        # M2 measured a year later — zero timestamp overlap
        stage_b = _stage_series(
            {"ws_130": list(base)},
            _ten_minute_grid(n, datetime(2026, 1, 1)),
            heights=[130.0],
        )
        items = [_item("M1", stage_a, [120.0]), _item("M2", stage_b, [130.0])]
        assert analyze_cross_mast(items) == []

    def test_overlap_below_min_pairs_skipped(self):
        n = MIN_PAIRS
        rng = np.random.default_rng(13)
        base = rng.normal(8, 2, n).clip(0.5)
        stage_a = _stage_series(
            {"ws_120": list(base)}, _ten_minute_grid(n), heights=[120.0]
        )
        # only 2 shared timestamps — below MIN_PAIRS everywhere
        stage_b = _stage_series(
            {"ws_130": list(base[:2])},
            _ten_minute_grid(n)[:2],
            heights=[130.0],
        )
        items = [_item("M1", stage_a, [120.0]), _item("M2", stage_b, [130.0])]
        assert analyze_cross_mast(items) == []

    def test_single_mast_no_pairs(self):
        n = 10
        rng = np.random.default_rng(13)
        base = rng.normal(8, 2, n).clip(0.5)
        stage = _stage_series(
            {"ws_120": list(base), "ws_140": list(base + 1)},
            _ten_minute_grid(n),
            heights=[120.0, 140.0],
        )
        assert analyze_cross_mast([_item("M1", stage, [120.0, 140.0])]) == []


# ── 2.3.7 中尺度 ────────────────────────────────────────────────────────


class TestMeso:
    def test_alignment_ten_minute_meso_exact_relation(self):
        """Native 10-min meso grid → exact y = 2x + 1 regression."""
        n = 40
        rng = np.random.default_rng(17)
        meso_values = rng.normal(5, 1.5, n).clip(0.5)
        stage = _stage_series(
            {"ws_120": list(2 * meso_values + 1)},
            _ten_minute_grid(n),
            heights=[120.0],
        )
        item = _item(
            "M1",
            stage,
            [120.0],
            meso_payload=_meso_payload(
                list(meso_values), _ten_minute_grid(n), sampling_period="10min"
            ),
        )
        panel = _panel_by_labels(analyze_meso([item])[0].panels, "ERA5", "120m")
        assert panel["slope"] == pytest.approx(2.0)
        assert panel["intercept"] == pytest.approx(1.0)
        assert panel["r"] == pytest.approx(1.0)
        assert panel["n_pairs"] == n

    def test_hourly_meso_upsampled_to_ten_minutes(self):
        """Hourly-meso payload aligned to the 10-min grid → 6× hourly pairs.

        Production wires ``sampling_period="10min"`` (load_datasets) with
        hourly ERA5 parquets — the meso frame is upsampled onto the mast
        grid, not the mast downsampled onto the meso grid.
        """
        hours = 6
        mast_rows = (hours - 1) * 6 + 1  # 31 10-min stamps over the same span
        hourly = list(np.linspace(4.0, 10.0, hours))
        # mast holds the hourly value constant within each hour
        mast_values = [hourly[min(i // 6, hours - 1)] for i in range(mast_rows)]
        stage = _stage_series(
            {"ws_120": mast_values},
            _ten_minute_grid(mast_rows),
            heights=[120.0],
        )
        meso_stamps = [
            datetime(2025, 1, 1) + timedelta(hours=i) for i in range(hours)
        ]
        item = _item(
            "M1",
            stage,
            [120.0],
            meso_payload=_meso_payload(
                list(hourly), meso_stamps, sampling_period="10min"
            ),
        )
        panel = _panel_by_labels(analyze_meso([item])[0].panels, "ERA5", "120m")
        assert panel["n_pairs"] == mast_rows  # upsampled, not just 6 hourly
        assert panel["r"] > 0.95

    def test_skips_mast_without_meso_payload(self):
        n = 10
        stage = _stage_series(
            {"ws_120": [7.0] * n}, _ten_minute_grid(n), heights=[120.0]
        )
        assert analyze_meso([_item("M1", stage, [120.0])]) == []

    def test_skips_mast_without_cleaning_payload(self):
        n = 10
        stage = _stage_series(
            {"ws_120": [7.0] * n}, _ten_minute_grid(n), heights=[120.0]
        )
        item = _item("M1", stage, [120.0])
        assert analyze_meso([replace(item, cleaning_payload=None)]) == []


# ── Atoms ───────────────────────────────────────────────────────────────


class TestAtoms:
    def _same_tower_section(self) -> ImputationSameTowerSection:
        n = 30
        rng = np.random.default_rng(11)
        base = rng.normal(8, 2, n).clip(0.5)
        stage = _stage_series(
            {"ws_120": list(base), "ws_140": list(2 * base + 1)},
            _ten_minute_grid(n),
            heights=[120.0, 140.0],
        )
        return ImputationSameTowerSection.from_inputs(
            [_item("M1", stage, [120.0, 140.0])]
        )

    def test_matrix_table_three_decimals_and_diagonal(self):
        section = self._same_tower_section()
        table_atom = next(
            a for a in section._atoms if isinstance(a, CorrelationMatrixAtom)
        )
        table = table_atom.renderTable()
        assert isinstance(table, TypstTable)
        assert table.headers == ["高度", "120m", "140m"]
        assert table.data[0] == ["120m", "1.000", "1.000"]
        assert len(table.data[1][2].split(".")[1]) == 3  # 3 decimals
        assert table.caption == "M1 同塔不同高度层风速相关系数矩阵"

    def test_matrix_table_em_dash_for_null(self):
        atom = CorrelationMatrixAtom.create(
            schema=CorrelationLongSchema,
            df=pl.DataFrame(
                {
                    "x_label": ["120m", "140m"],
                    "y_label": ["140m", "120m"],
                    "r": [None, 0.5],
                }
            ),
            meta=CorrelationMatrixAtomMeta(
                mast_name="M1", labels=["120m", "140m"], caption="c"
            ),
        )
        table = atom.renderTable()
        # row y=120m: (x=120,y=120) absent → —, (x=140,y=120) = 0.5
        # row y=140m: (x=120,y=140) = null → —, (x=140,y=140) absent → —
        assert table.data[0] == ["120m", "—", "0.500"]
        assert table.data[1] == ["140m", "—", "—"]

    def test_scatter_atom_caption_and_hash_filename(self, tmp_path):
        section = self._same_tower_section()
        scatter = next(
            a for a in section._atoms if isinstance(a, ScatterRegressionAtom)
        )
        assert scatter.default_image_caption == (
            "M1 同塔不同高度层风速散点及回归直线"
        )
        image = scatter.renderImage(Path(tmp_path))
        assert image.exists()
        assert image.name.startswith("M1_same_tower_")


class TestScatterCompactPacking:
    """Compact packing: one wrapped panel per actual pair, no empty cells."""

    def _same_tower_atom(
        self, heights: list[float], n: int = 30
    ) -> ScatterRegressionAtom:
        rng = np.random.default_rng(11)
        base = rng.normal(8, 2, n).clip(0.5)
        stage = _stage_series(
            {
                f"ws_{int(h)}": list(base + 0.1 * i)
                for i, h in enumerate(heights)
            },
            _ten_minute_grid(n),
            heights=heights,
        )
        section = ImputationSameTowerSection.from_inputs(
            [_item("M1", stage, heights)]
        )
        return next(
            a for a in section._atoms if isinstance(a, ScatterRegressionAtom)
        )

    def _spec(self, atom: ScatterRegressionAtom) -> dict:
        points = atom.meta.pairs_df.drop_nulls(["x", "y"]).to_pandas()
        return atom._build_chart(points).to_dict()

    def _spec_rows(self, spec: dict) -> list[dict]:
        return [r for ds in spec["datasets"].values() for r in ds]

    def test_multi_x_wraps_three_per_row_in_pair_order(self):
        spec = self._spec(self._same_tower_atom([120.0, 140.0, 160.0]))

        assert spec["facet"]["field"] == "panel"
        assert spec["columns"] == 3
        # upper-triangle pairs in (y, x) height order — no empty cells
        assert spec["facet"]["sort"] == [
            "120m ← 140m",
            "120m ← 160m",
            "140m ← 160m",
        ]

    def test_five_heights_ten_panels(self):
        spec = self._spec(
            self._same_tower_atom([80.0, 100.0, 120.0, 140.0, 160.0])
        )
        sort = spec["facet"]["sort"]

        assert len(sort) == 10  # C(5, 2) panels, wrapped 3+3+3+1
        assert spec["columns"] == 3
        assert sort[:3] == ["80m ← 100m", "80m ← 120m", "80m ← 140m"]

    def test_data_holds_only_actual_pair_rows(self):
        spec = self._spec(self._same_tower_atom([120.0, 140.0, 160.0]))
        rows = self._spec_rows(spec)

        panels = {(r["x_label"], r["y_label"]) for r in rows}
        assert panels == {
            ("140m", "120m"),
            ("160m", "120m"),
            ("160m", "140m"),
        }
        assert {r["kind"] for r in rows} == {"point", "line", "text"}

    def test_single_x_keeps_bare_height_headers(self):
        n = 30
        rng = np.random.default_rng(11)
        base = rng.normal(8, 2, n).clip(0.5)
        heights = [120.0, 140.0, 160.0]
        stage = _stage_series(
            {
                f"ws_{int(h)}": list(base + 0.1 * i)
                for i, h in enumerate(heights)
            },
            _ten_minute_grid(n),
            heights=heights,
        )
        section = ImputationMesoSection.from_inputs(
            [
                _item(
                    "M1",
                    stage,
                    heights,
                    meso_payload=_meso_payload(
                        list(0.9 * base + 0.2), _ten_minute_grid(n)
                    ),
                )
            ]
        )
        atom = next(
            a for a in section._atoms if isinstance(a, ScatterRegressionAtom)
        )
        spec = self._spec(atom)

        # 2.3.7 single-x layout unchanged: bare height headers, ≤4 per row
        assert spec["facet"]["field"] == "panel"
        assert spec["facet"]["sort"] == ["120m", "140m", "160m"]
        assert spec["columns"] == 3

    def test_sampling_respects_altair_budget(self):
        atom = self._same_tower_atom([120.0, 140.0], n=6000)
        rows = self._spec_rows(self._spec(atom))

        # 5000-row Altair budget: 4996 sampled points + 4 overlay rows
        assert len(rows) == 5000


# ── Section rendering ───────────────────────────────────────────────────


class TestSectionsRender:
    def _items(self) -> list[SingleMastAnalysisInput]:
        n = 30
        rng = np.random.default_rng(23)
        base = rng.normal(8, 2, n).clip(0.5)
        stage_a = _stage_series(
            {"ws_120": list(base), "ws_140": list(base + 1)},
            _ten_minute_grid(n),
            heights=[120.0, 140.0],
        )
        stage_b = _stage_series(
            {"ws_120": list(0.9 * base + 0.5), "ws_140": list(0.8 * base + 1)},
            _ten_minute_grid(n),
            heights=[120.0, 140.0],
        )
        meso_payload = _meso_payload(list(0.8 * base + 0.7), _ten_minute_grid(n))
        return [
            _item("M1", stage_a, [120.0, 140.0], meso_payload=meso_payload),
            _item("M2", stage_b, [120.0, 140.0], meso_payload=meso_payload),
        ]

    def test_same_tower_section_renders(self, tmp_path):
        ir = ImputationSameTowerSection.from_inputs(self._items()).render_ir(
            Path(tmp_path)
        )
        assert ir.heading.text == "同塔插补"
        paragraphs = [b for b in ir.body if hasattr(b, "text")]
        assert any(
            p.text == "同塔不同高度层风速相关性见下表及下图。" for p in paragraphs
        )
        assert len([b for b in ir.body if isinstance(b, TypstTable)]) == 2
        assert len([b for b in ir.body if isinstance(b, TypstFigure)]) == 2

    def test_cross_mast_section_renders(self, tmp_path):
        ir = ImputationCrossMastSection.from_inputs(self._items()).render_ir(
            Path(tmp_path)
        )
        assert ir.heading.text == "异塔插补"
        paragraphs = [b for b in ir.body if hasattr(b, "text")]
        assert any(
            p.text == "各测风塔间风速相关性及回归系数见下图。" for p in paragraphs
        )
        figures = [b for b in ir.body if isinstance(b, TypstFigure)]
        assert len(figures) == 2  # M1←M2 and M2←M1

    def test_meso_section_renders(self, tmp_path):
        ir = ImputationMesoSection.from_inputs(self._items()).render_ir(
            Path(tmp_path)
        )
        assert ir.heading.text == "中尺度插补"
        paragraphs = [b for b in ir.body if hasattr(b, "text")]
        assert any(
            p.text.startswith("根据 2.2.2 节所选 ERA5 数据源") for p in paragraphs
        )
        figures = [b for b in ir.body if isinstance(b, TypstFigure)]
        assert len(figures) == 2
        # renderImageTypst stores paths relative to images_dir.parent
        assert all(
            (Path(tmp_path).parent / f.content).exists() for f in figures
        )

    def test_empty_items_render_heading_only(self, tmp_path):
        for cls, title in [
            (ImputationSameTowerSection, "同塔插补"),
            (ImputationCrossMastSection, "异塔插补"),
            (ImputationMesoSection, "中尺度插补"),
        ]:
            ir = cls.from_inputs([]).render_ir(Path(tmp_path))
            assert ir.heading.text == title
            assert ir.body == []

    def test_no_exhibits_renders_heading_only(self, tmp_path):
        """Every mast skipped (single height) → no intro referencing nothing."""
        n = 10
        stage = _stage_series(
            {"ws_120": [7.0] * n}, _ten_minute_grid(n), heights=[120.0]
        )
        item = _item("M1", stage, [120.0])
        for cls in (
            ImputationSameTowerSection,
            ImputationCrossMastSection,
            ImputationMesoSection,
        ):
            ir = cls.from_inputs([item]).render_ir(Path(tmp_path))
            assert ir.body == []
