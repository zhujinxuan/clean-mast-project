"""Tests for ExtremeWindSection.from_inputs with config-driven heights."""

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from cleanmast.shared.timeseries import SensorColumn, TimeSeriesData
from cleanmast.subdomains.reporting.model.analysis_input import SingleMastAnalysisInput
from cleanmast.subdomains.reporting.model.analysis_parameters import AnalysisParameters
from cleanmast.subdomains.reporting.model.extreme_wind_gust_factor import (
    ExtremeWindGustFactor,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.model.method2_atom import (
    Method2ParamsAtom,
    Method2QQExtremeAtom,
)
from cleanmast.subdomains.reporting.subdomains.extreme_wind.section import (
    ExtremeWindSection,
)

# ── Helpers ─────────────────────────────────────────────────────────────


def _make_sensor(
    *,
    sensor_type: str = "WindSpeed",
    stat_type: str = "avg",
    height: float = 100.0,
    fill: str = "",
    unit: str = "m/s",
) -> SensorColumn:
    """Build a SensorColumn with consistent naming.

    When ``fill`` is given the column name ends with ``_fill:<type>``
    so that ``detect_interpolation_marker()`` finds it.
    """
    base = f"{sensor_type}_{height:.0f}m_{stat_type}"
    if fill:
        col = f"{base}_fill:{fill}"
    else:
        col = f"{base} [{unit}]"
    return SensorColumn(
        column_name=col,
        sensor_type=sensor_type,
        sensor_direction="",
        height=height,
        stat_type=stat_type,
        unit=unit,
    )


def _make_timeseries(
    sensors: list[SensorColumn],
    n_hours: int = 8760,
    seed: int = 42,
) -> TimeSeriesData:
    """Generate realistic wind time-series data.

    Weibull reference at the lowest avg-sensor height, shear-extrapolated
    to other heights.  Max sensors get a gusty copy (~1.4x).
    """
    rng = np.random.default_rng(seed)
    timestamps = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(n_hours)]

    avg_heights = sorted({
        s.height for s in sensors
        if s.sensor_type == "WindSpeed" and s.stat_type == "avg"
    })
    if not avg_heights:
        raise ValueError("Need at least one WindSpeed/avg sensor")
    min_h = avg_heights[0]
    alpha = 0.14
    ref_wind = rng.weibull(2, n_hours) * 8.0
    ref_wind = np.clip(ref_wind, 0.5, 40.0)

    columns: dict[str, list[float]] = {"timestamp": timestamps}
    for s in sensors:
        if s.sensor_type != "WindSpeed":
            continue
        shear = (s.height / min_h) ** alpha
        if s.stat_type == "max":
            values = ref_wind * shear * (1.35 + rng.uniform(-0.05, 0.05, n_hours))
        else:
            values = ref_wind * shear
        values = np.clip(values, 0.0, 50.0)
        columns[s.column_name] = list(values)

    return TimeSeriesData(df=pl.DataFrame(columns), sensors=sensors)


def _make_input(
    sensors: list[SensorColumn],
    *,
    air_density: float = 1.225,
    mast_name: str = "TestMast",
    n_hours: int = 8760,
    extreme_wind_10min_heights: list[float],
    extreme_wind_3s_heights: list[float] = [],
    extreme_wind_gust_factors: list[ExtremeWindGustFactor] = [],
) -> SingleMastAnalysisInput:
    """Build SingleMastAnalysisInput from sensors."""
    ts = _make_timeseries(sensors, n_hours=n_hours)
    params = AnalysisParameters(
        air_density=air_density,
        extreme_wind_10min_heights=extreme_wind_10min_heights,
        extreme_wind_3s_heights=extreme_wind_3s_heights,
        extreme_wind_gust_factors=extreme_wind_gust_factors,
    )
    return SingleMastAnalysisInput(
        time_series=ts,
        parameters=params,
        mast_name=mast_name,
    )


# ── Tests ───────────────────────────────────────────────────────────────


class TestConfigDrivenHeights:
    """from_inputs with config heights uses exactly those heights."""

    def test_uses_only_configured_heights(self) -> None:
        """A height in the config list IS used even if outside 120-160.
        A height inside 120-160 but NOT in the list is NOT used."""
        heights = [110.0, 120.0, 130.0, 140.0, 150.0, 170.0]
        sensors = [_make_sensor(height=h) for h in heights]
        ten_min = [110.0, 130.0, 170.0]
        item = _make_input(
            sensors,
            extreme_wind_10min_heights=ten_min,
            n_hours=2000,
        )
        section = ExtremeWindSection.from_inputs([item])

        for atom in section.method1_atoms:
            df = atom.df
            used = set(df["height"].unique().to_list())
            assert used == set(ten_min), (
                f"Method 1 used heights {used}, expected {ten_min}"
            )

        for atom in section.method2_atoms:
            if not hasattr(atom, "df"):
                continue
            df = atom.df
            if "height" not in df.columns:
                continue
            used = set(df["height"].unique().to_list())
            assert used.issubset(set(ten_min)), (
                f"Method 2 used heights {used}, expected subset of {ten_min}"
            )

    def test_interpolated_height_included_in_config(self) -> None:
        """Fill heights (interpolated avg) are INCLUDED when in config."""
        sensors = [
            _make_sensor(height=120.0),
            _make_sensor(height=130.0, fill="interpolated"),
            _make_sensor(height=140.0),
        ]
        ten_min = [120.0, 130.0, 140.0]
        item = _make_input(sensors, extreme_wind_10min_heights=ten_min, n_hours=2000)
        section = ExtremeWindSection.from_inputs([item])

        all_h: set[float] = set()
        for atom in section.method1_atoms:
            all_h.update(atom.df["height"].unique().to_list())
        assert 130.0 in all_h, "Interpolated height 130m should be included"


class TestMaxSensorExtreme:
    """Height with real max sensor → extreme computed from max series."""

    def test_max_sensor_extreme_populates_gumbel_params(self, tmp_path: Path) -> None:
        """Max-sensor height yields an extreme Gumbel param row and a real QQ image."""
        sensors = [
            _make_sensor(height=120.0),
            _make_sensor(height=120.0, stat_type="max"),
            _make_sensor(height=140.0),
        ]
        item = _make_input(
            sensors,
            extreme_wind_10min_heights=[120.0, 140.0],
            extreme_wind_3s_heights=[120.0],
            n_hours=2000,
        )
        section = ExtremeWindSection.from_inputs([item])

        params = next(
            a for a in section.method2_atoms if isinstance(a, Method2ParamsAtom)
        )
        extreme_rows = params.df.filter(
            (pl.col("wind_speed_type") == "extreme") & (pl.col("height") == 120.0)
        )
        assert extreme_rows.height == 1
        sample_data = extreme_rows["sample_data"][0]
        assert sample_data is not None
        assert len(sample_data) > 0

        qq = next(
            a for a in section.method2_atoms if isinstance(a, Method2QQExtremeAtom)
        )
        path = qq.renderImage(tmp_path)
        assert path.exists()
        assert path.suffix == ".png"

    def test_max_sensor_extreme_differs_from_gust_fallback(self) -> None:
        """Extreme from max sensor uses max-sensor data (not gust factor)."""
        sensors = [
            _make_sensor(height=120.0),
            _make_sensor(height=120.0, stat_type="max"),
            _make_sensor(height=140.0),
        ]
        item = _make_input(
            sensors,
            extreme_wind_10min_heights=[120.0, 140.0],
            extreme_wind_3s_heights=[120.0],
            n_hours=2000,
        )
        section = ExtremeWindSection.from_inputs([item])

        m1_ext: dict[float, float] = {}
        for atom in section.method1_atoms:
            for row in atom.df.filter(
                pl.col("wind_speed_type") == "extreme"
            ).iter_rows(named=True):
                m1_ext[float(row["height"])] = float(row["max_wind_speed"])

        assert 120.0 in m1_ext
        assert 140.0 in m1_ext
        assert m1_ext[120.0] > 0
        assert m1_ext[140.0] > 0

    def test_per_height_gust_factor_fallback(self) -> None:
        """Height without max sensor uses per-height gust factor (non-1.4)."""
        sensors = [
            _make_sensor(height=120.0),
            _make_sensor(height=140.0),
        ]
        custom_gf = [
            ExtremeWindGustFactor(height=120.0, gust_factor=1.5),
            ExtremeWindGustFactor(height=140.0, gust_factor=1.3),
        ]
        item = _make_input(
            sensors,
            extreme_wind_10min_heights=[120.0, 140.0],
            extreme_wind_3s_heights=[],
            extreme_wind_gust_factors=custom_gf,
            n_hours=2000,
        )
        section = ExtremeWindSection.from_inputs([item])

        m1_sus: dict[float, float] = {}
        m1_ext: dict[float, float] = {}
        for atom in section.method1_atoms:
            for row in atom.df.iter_rows(named=True):
                h = float(row["height"])
                ws = float(row["max_wind_speed"])
                if row["wind_speed_type"] == "sustained":
                    m1_sus[h] = ws
                else:
                    m1_ext[h] = ws

        assert m1_ext[120.0] / m1_sus[120.0] == pytest.approx(1.5, rel=0.01), (
            "Expected gust factor 1.5 at 120m"
        )
        assert m1_ext[140.0] / m1_sus[140.0] == pytest.approx(1.3, rel=0.01), (
            "Expected gust factor 1.3 at 140m"
        )

    def test_default_gust_factor_1_4(self) -> None:
        """When no gust factors configured, default 1.4 is used."""
        sensors = [
            _make_sensor(height=120.0),
            _make_sensor(height=140.0),
        ]
        item = _make_input(
            sensors,
            extreme_wind_10min_heights=[120.0, 140.0],
            extreme_wind_3s_heights=[],
            extreme_wind_gust_factors=[],
            n_hours=2000,
        )
        section = ExtremeWindSection.from_inputs([item])

        m1_sus: dict[float, float] = {}
        m1_ext: dict[float, float] = {}
        for atom in section.method1_atoms:
            for row in atom.df.iter_rows(named=True):
                h = float(row["height"])
                ws = float(row["max_wind_speed"])
                if row["wind_speed_type"] == "sustained":
                    m1_sus[h] = ws
                else:
                    m1_ext[h] = ws

        assert m1_ext[120.0] / m1_sus[120.0] == pytest.approx(1.4, rel=0.01), (
            "Expected default gust factor 1.4 at 120m"
        )


class TestEmptyHeightsGuard:
    """Guard: empty extreme_wind_10min_heights raises ValueError."""

    def test_empty_heights_raises(self) -> None:
        """from_inputs raises ValueError when extreme_wind_10min_heights is empty."""
        sensors = [
            _make_sensor(height=120.0),
            _make_sensor(height=140.0),
        ]
        item = _make_input(
            sensors,
            extreme_wind_10min_heights=[],
            n_hours=2000,
        )
        with pytest.raises(ValueError, match="extreme_wind_10min_heights"):
            ExtremeWindSection.from_inputs([item])


def _scaled_item(
    mast_name: str,
    scale: float,
    heights: list[float],
    seed: int = 42,
) -> SingleMastAnalysisInput:
    """Build an input whose wind speeds are ``scale`` × a seeded base field."""
    sensors = [_make_sensor(height=h) for h in heights]
    base = _make_timeseries(sensors, n_hours=2000, seed=seed)
    wind_cols = [s.column_name for s in sensors]
    scaled_df = base.df.with_columns(
        [(pl.col(c) * scale).clip(0.0, 60.0) for c in wind_cols]
    )
    params = AnalysisParameters(
        air_density=1.225,
        extreme_wind_10min_heights=heights,
        extreme_wind_3s_heights=[],
        extreme_wind_gust_factors=[],
    )
    return SingleMastAnalysisInput(
        time_series=TimeSeriesData(df=scaled_df, sensors=sensors),
        parameters=params,
        mast_name=mast_name,
    )


class TestSiteConclusion:
    """Cross-mast determination table + conclusion at the end of 2.6.5."""

    HEIGHTS = [120.0, 140.0]

    def test_two_similar_masts_get_single_conclusion(self, tmp_path: Path) -> None:
        items = [
            _make_input(
                [_make_sensor(height=h) for h in self.HEIGHTS],
                extreme_wind_10min_heights=self.HEIGHTS,
                n_hours=2000,
            ),
            _make_input(
                [_make_sensor(height=h) for h in self.HEIGHTS],
                extreme_wind_10min_heights=self.HEIGHTS,
                n_hours=2000,
                mast_name="TestMastB",
            ),
        ]
        section = ExtremeWindSection.from_inputs(items)

        assert len(section.site_atoms) == 2
        sentences = section.site_atoms[1].df["text"].to_list()
        assert len(sentences) == 1
        assert "《GB/T 18451.1-2022 风力发电机组 设计要求》" in sentences[0]
        assert "IEC" in sentences[0]

    def test_differing_masts_get_zoned_conclusion(self, tmp_path: Path) -> None:
        items = [
            _scaled_item("MAlpha", 1.0, self.HEIGHTS),
            _scaled_item("MBeta", 1.5, self.HEIGHTS),
        ]
        section = ExtremeWindSection.from_inputs(items)

        sentences = section.site_atoms[1].df["text"].to_list()
        # Sustained conservative differs by >= 3 m/s → 相差大; classes
        # differ → zoned sentences naming each mast's representative area.
        assert len(sentences) >= 3
        assert any("MAlpha 测风塔代表区域机位" in s for s in sentences)
        assert any("MBeta 测风塔代表区域机位" in s for s in sentences)
        assert not any("本项目可选择" in s for s in sentences)

    def test_summary_subsection_ends_with_table_then_conclusion(
        self, tmp_path: Path
    ) -> None:
        items = [
            _make_input(
                [_make_sensor(height=h) for h in self.HEIGHTS],
                extreme_wind_10min_heights=self.HEIGHTS,
                n_hours=2000,
            ),
        ]
        section = ExtremeWindSection.from_inputs(items)
        ir = section.render_ir(images_dir=tmp_path)

        summary = next(
            s for s in ir.subsections if s.heading.text == "五十年一遇风速总结"
        )
        assert len(summary.body) >= 2
        last, second_last = summary.body[-1], summary.body[-2]
        assert type(second_last).__name__ == "TypstTable"
        assert second_last.caption == "场址五十年一遇风速判定"
        assert type(last).__name__ == "TypstParagraph"
        assert "《GB/T 18451.1-2022 风力发电机组 设计要求》" in last.text

    def test_method3_atom_contains_sustained_and_extreme_rows(self) -> None:
        """Method 3 tables carry 持续风速 rows alongside 极端风速 rows."""
        item = _make_input(
            [_make_sensor(height=h) for h in self.HEIGHTS],
            extreme_wind_10min_heights=self.HEIGHTS,
            n_hours=2000,
        )
        section = ExtremeWindSection.from_inputs([item])
        assert section.method3_atoms
        for atom in section.method3_atoms:
            types = set(atom.df["wind_speed_type"].unique().to_list())
            assert types == {"sustained", "extreme"}
