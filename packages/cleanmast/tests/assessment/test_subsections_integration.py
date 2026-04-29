"""Integration tests for multi-mast subsection renderers and full pipeline.

Tests cover all 6 subsection types with 1, 2, and 3 masts:
- WindRoseSection
- WindTemporalSubsection
- WeibullSubsection
- WindFrequencySubsection
- TurbulenceSubsection
- VerticalProfileSubsection

Each test verifies exact IR node counts to ensure structural correctness
of the multi-mast refactor.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import tomli_w
from cleanmast.subdomains.assessment.domain.entities.single_mast.daily_pattern import (
    SingleMastDailyPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.daily_power_pattern import (
    SingleMastDailyPowerPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_daily_power import (
    SingleMastMonthlyDailyPowerAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_daily_wind import (
    SingleMastMonthlyDailyWindAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_pattern import (
    SingleMastMonthlyPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.monthly_power_pattern import (
    SingleMastMonthlyPowerPatternAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.timeseries import (
    SingleMastWindTimeseriesAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_multi import (
    SingleMastTurbulenceMultiHeightAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_summary import (
    SingleMastTurbulenceSummaryAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_subgrid import (
    SingleMastWeibullSubgridAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_distribution_subgrid import (
    SingleMastWindDistributionSubgridAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_frequency_hours import (
    SingleMastWindFrequencyHoursAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_power_hours import (
    SingleMastWindPowerHoursAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_productive_range import (
    SingleMastWindProductiveRangeAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_rose import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_rose_grid import (
    SingleMastMonthlyWindRoseGridAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_rose_power_grid import (
    SingleMastMonthlyWindPowerRoseGridAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_shear_matrix import (
    SingleMastWindShearExponentAtom,
)
from cleanmast.subdomains.assessment.domain.services.sections.turbulence_subsection import (
    TurbulenceSubsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.vertical_profile_subsection import (
    VerticalProfileSubsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.weibull_subsection import (
    WeibullSubsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.wind_frequency_subsection import (
    WindFrequencySubsection,
)
from cleanmast.subdomains.assessment.domain.services.sections.wind_rose import (
    WindRoseSection,
)
from cleanmast.subdomains.assessment.domain.services.sections.wind_temporal_subsection import (
    WindTemporalSubsection,
)
from cleanmast.subdomains.assessment.domain.types import (
    TypstDocument,
    TypstFigure,
    TypstHeading,
    TypstParagraph,
    TypstSection,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.value_objects import (
    AtomCollection,
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.schemas import (
    VerticalProfileSchema,
    WindShearSchema,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TemporalPatternSchema,
    TurbulenceSchema,
    WeibullSchema,
    WindFrequencySchema,
    WindRoseSchema,
)
from cleanmast.subdomains.assessment.infrastructure import AssessmentReportBuilder

# =============================================================================
# Sample Data Helpers
# =============================================================================


def _sample_temporal_df() -> pl.DataFrame:
    timestamps = pl.datetime_range(
        start=datetime(2024, 1, 1),
        end=datetime(2024, 1, 3),
        interval="1h",
        eager=True,
    )
    rows = []
    for height in [80.0, 140.0]:
        marker = "外推" if height > 100 else None
        for ts in timestamps:
            hour = ts.hour
            month = ts.month
            wind_speed = 5.0 + np.sin(hour * np.pi / 12) * 2 + (height - 80) * 0.02
            wind_power = 0.5 * 1.225 * wind_speed ** 3
            rows.append(
                {
                    "timestamp": ts,
                    "hour": hour,
                    "month": month,
                    "wind_speed": wind_speed,
                    "wind_power": wind_power,
                    "height": height,
                    "mean_speed": wind_speed * 1.1,
                    "mean_power": wind_power * 1.2,
                    "interpolation_marker": marker,
                }
            )
    return pl.DataFrame(rows)


def _sample_wind_rose_df() -> pl.DataFrame:
    sector_names = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    ]
    rows = []
    for month in [1, 2, 3]:
        month_name = f"{month}月"
        for height in [80.0, 120.0]:
            marker = "外推" if height > 100 else None
            for sector, name in enumerate(sector_names):
                freq = 0.2 if sector == 0 else 0.05
                power = 300.0 if sector == 0 else 100.0
                rows.append(
                    {
                        "month": month,
                        "month_name": month_name,
                        "sector": sector,
                        "sector_name": name,
                        "height": height,
                        "frequency": freq,
                        "energy_frequency": 0.8 * freq,
                        "wind_power_density": power,
                        "interpolation_marker": marker,
                    }
                )
    return pl.DataFrame(rows)


def _sample_turbulence_df() -> pl.DataFrame:
    rows = []
    for height in [80.0, 120.0]:
        marker = "外推" if height > 100 else None
        for wind_speed in range(3, 16, 2):
            mean_ti = 0.18 - (wind_speed - 3) * 0.005 - (height - 80) * 0.0002
            std_ti = 0.03
            rep_ti = mean_ti + 1.28 * std_ti
            iec_cat = "A+" if rep_ti > 0.18 else "A" if rep_ti > 0.16 else "B"
            rows.append(
                {
                    "wind_speed_bin": wind_speed,
                    "height": height,
                    "interpolation_marker": marker,
                    "mean_ti": mean_ti,
                    "std_ti": std_ti,
                    "representative_ti": rep_ti,
                    "iec_category": iec_cat,
                    "count": 42,
                }
            )
    return pl.DataFrame(rows)


def _sample_weibull_df() -> pl.DataFrame:
    bin_centers = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5]
    rows = []
    for height in [80.0, 140.0]:
        marker = "外推" if height > 100 else None
        shape_k = 2.0 + (height - 80) * 0.005
        scale_c = 7.0 + (height - 80) * 0.02
        mean_speed = scale_c * np.exp(1 / shape_k * np.log(1 + 1 / shape_k))
        observed_density = []
        fitted_density = []
        for b in bin_centers:
            x = b / scale_c
            pdf_val = (
                (shape_k / scale_c)
                * (x ** (shape_k - 1))
                * np.exp(-(x ** shape_k))
            )
            observed_density.append(max(0.001, pdf_val))
            fitted_density.append(max(0.001, pdf_val * 0.95))
        rows.append(
            {
                "height": height,
                "interpolation_marker": marker,
                "shape_k": shape_k,
                "scale_c": scale_c,
                "mean_speed": mean_speed,
                "bin_centers": bin_centers,
                "observed_density": observed_density,
                "fitted_density": fitted_density,
            }
        )
    return pl.DataFrame(rows)


def _sample_wind_frequency_df() -> pl.DataFrame:
    rows = []
    for height in [80.0, 140.0]:
        marker = "外推" if height > 100 else None
        for bin_start in range(0, 15):
            bin_end = bin_start + 1
            bin_center = bin_start + 0.5
            freq = 0.15 * (bin_center / 7) ** 2 * np.exp(-(bin_center / 7) ** 2)
            occurrence_hours = freq * 8760
            power_freq = freq * (bin_center ** 3) / 500
            power_hours = power_freq * 8760
            rows.append(
                {
                    "height": height,
                    "interpolation_marker": marker,
                    "bin_start": float(bin_start),
                    "bin_end": float(bin_end),
                    "bin_center": bin_center,
                    "frequency": freq,
                    "occurrence_hours": occurrence_hours,
                    "power_frequency": power_freq,
                    "power_hours": power_hours,
                }
            )
    return pl.DataFrame(rows)


def _sample_vertical_profile_df() -> pl.DataFrame:
    rows = []
    heights = [50.0, 80.0, 100.0, 120.0]
    alpha = 0.15
    ref_speed = 5.5
    ref_height = 80.0
    for i, height in enumerate(heights):
        marker = "外推" if height > 100 else None
        wind_speed = ref_speed * (height / ref_height) ** alpha
        rows.append(
            {
                "height": height,
                "interpolation_marker": marker,
                "wind_speed_mean": wind_speed,
                "wind_speed_std": wind_speed * 0.15,
                "alpha": alpha if i == 0 else None,
                "r_squared": 0.98 if i == 0 else None,
            }
        )
    return pl.DataFrame(rows)


# =============================================================================
# Atom Collection Helpers
# =============================================================================


def _make_wind_rose_collection(n: int) -> AtomCollection:
    d: dict[str, list[Any]] = {}
    for i in range(n):
        meta = SingleMastMeta(mast_name=f"M{i + 1:02d}")
        df = _sample_wind_rose_df()
        d[f"M{i + 1:02d}"] = [
            SingleMastMonthlyWindFrequencyRoseAtom.create(
                schema=WindRoseSchema, df=df, meta=meta
            ),
            SingleMastWindPowerRoseAtom.create(
                schema=WindRoseSchema, df=df, meta=meta
            ),
            SingleMastMonthlyWindRoseGridAtom.create(
                schema=WindRoseSchema, df=df, meta=meta
            ),
            SingleMastMonthlyWindPowerRoseGridAtom.create(
                schema=WindRoseSchema, df=df, meta=meta
            ),
        ]
    return AtomCollection.from_dict(d)


def _make_temporal_collection(n: int) -> AtomCollection:
    d: dict[str, list[Any]] = {}
    for i in range(n):
        meta = SingleMastMeta(mast_name=f"M{i + 1:02d}")
        df = _sample_temporal_df()
        d[f"M{i + 1:02d}"] = [
            SingleMastWindTimeseriesAtom.create(
                schema=TemporalPatternSchema, df=df, meta=meta
            ),
            SingleMastDailyPatternAtom.create(
                schema=TemporalPatternSchema, df=df, meta=meta
            ),
            SingleMastDailyPowerPatternAtom.create(
                schema=TemporalPatternSchema, df=df, meta=meta
            ),
            SingleMastMonthlyPatternAtom.create(
                schema=TemporalPatternSchema, df=df, meta=meta
            ),
            SingleMastMonthlyPowerPatternAtom.create(
                schema=TemporalPatternSchema, df=df, meta=meta
            ),
            SingleMastMonthlyDailyWindAtom.create(
                schema=TemporalPatternSchema, df=df, meta=meta
            ),
            SingleMastMonthlyDailyPowerAtom.create(
                schema=TemporalPatternSchema, df=df, meta=meta
            ),
        ]
    return AtomCollection.from_dict(d)


def _make_weibull_collection(n: int) -> AtomCollection:
    d: dict[str, list[Any]] = {}
    for i in range(n):
        meta = SingleMastMeta(mast_name=f"M{i + 1:02d}")
        df = _sample_weibull_df()
        d[f"M{i + 1:02d}"] = [
            SingleMastWeibullSubgridAtom.create(
                schema=WeibullSchema, df=df, meta=meta
            ),
        ]
    return AtomCollection.from_dict(d)


def _make_wind_frequency_collection(n: int) -> AtomCollection:
    d: dict[str, list[Any]] = {}
    for i in range(n):
        meta = SingleMastMeta(mast_name=f"M{i + 1:02d}")
        df = _sample_wind_frequency_df()
        d[f"M{i + 1:02d}"] = [
            SingleMastWindFrequencyHoursAtom.create(
                schema=WindFrequencySchema, df=df, meta=meta
            ),
            SingleMastWindPowerHoursAtom.create(
                schema=WindFrequencySchema, df=df, meta=meta
            ),
            SingleMastWindDistributionSubgridAtom.create(
                schema=WindFrequencySchema, df=df, meta=meta
            ),
            SingleMastWindProductiveRangeAtom.create(
                schema=WindFrequencySchema, df=df, meta=meta
            ),
        ]
    return AtomCollection.from_dict(d)


def _make_turbulence_collection(n: int) -> AtomCollection:
    d: dict[str, list[Any]] = {}
    for i in range(n):
        meta = SingleMastMeta(mast_name=f"M{i + 1:02d}")
        df1 = _sample_turbulence_df()
        d[f"M{i + 1:02d}"] = [
            SingleMastTurbulenceSummaryAtom.create(
                schema=TurbulenceSchema, df=df1, meta=meta
            ),
            SingleMastTurbulenceMultiHeightAtom.create(
                schema=TurbulenceSchema, df=df1, meta=meta
            ),
        ]
    return AtomCollection.from_dict(d)


def _make_vertical_profile_collection(n: int) -> AtomCollection:
    d: dict[str, list[Any]] = {}
    shear_df = pl.DataFrame({
        "from_height": [50.0, 50.0, 80.0],
        "to_height": [80.0, 120.0, 120.0],
        "alpha_mean": [0.15, 0.14, 0.13],
        "alpha_std": [0.03, 0.025, 0.02],
        "alpha_min": [0.08, 0.07, 0.06],
        "alpha_max": [0.25, 0.22, 0.20],
    })
    for i in range(n):
        meta = SingleMastMeta(mast_name=f"M{i + 1:02d}")
        profile_df = _sample_vertical_profile_df()
        d[f"M{i + 1:02d}"] = [
            SingleMastWindShearExponentAtom.create(
                profile_schema=VerticalProfileSchema,
                profile_df=profile_df,
                shear_schema=WindShearSchema,
                shear_df=shear_df,
                meta=meta,
            )
        ]
    return AtomCollection.from_dict(d)


# =============================================================================
# Node Count Helper
# =============================================================================


def _count_nodes(section: TypstSection) -> dict[str, int]:
    nodes = [section.heading] + list(section.body)
    return {
        "headings": sum(1 for n in nodes if isinstance(n, TypstHeading)),
        "paragraphs": sum(1 for n in nodes if isinstance(n, TypstParagraph)),
        "tables": sum(1 for n in nodes if isinstance(n, TypstTable)),
        "figures": sum(1 for n in nodes if isinstance(n, TypstFigure)),
        "total": len(nodes),
    }


# =============================================================================
# WindRose Integration Tests
# =============================================================================


class TestWindRoseMultiMastIntegration:
    """Integration tests for WindRoseSection with 1/2/3 masts."""

    def test_one_mast_regression(self, tmp_path: Path) -> None:
        collection = _make_wind_rose_collection(1)
        subsection = WindRoseSection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 2
        assert counts["tables"] == 2
        assert counts["figures"] == 4
        assert counts["total"] == 9

    def test_two_masts_basic(self, tmp_path: Path) -> None:
        collection = _make_wind_rose_collection(2)
        subsection = WindRoseSection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 2
        assert counts["tables"] == 4
        assert counts["figures"] == 8
        assert counts["total"] == 15

    def test_three_masts_stress(self, tmp_path: Path) -> None:
        collection = _make_wind_rose_collection(3)
        subsection = WindRoseSection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 2
        assert counts["tables"] == 6
        assert counts["figures"] == 12
        assert counts["total"] == 21

    def test_has_chinese_title(self, tmp_path: Path) -> None:
        collection = _make_wind_rose_collection(2)
        subsection = WindRoseSection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        assert "风向风能分布" in section_node.heading.text

    def test_all_nodes_are_valid_ir_types(self, tmp_path: Path) -> None:
        collection = _make_wind_rose_collection(2)
        subsection = WindRoseSection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        nodes = [section_node.heading] + list(section_node.body)
        valid_types = (TypstHeading, TypstParagraph, TypstTable, TypstFigure)
        assert all(isinstance(n, valid_types) for n in nodes)


# =============================================================================
# WindTemporal Integration Tests
# =============================================================================


class TestWindTemporalMultiMastIntegration:
    """Integration tests for WindTemporalSubsection with 1/2/3 masts."""

    def test_one_mast_regression(self, tmp_path: Path) -> None:
        collection = _make_temporal_collection(1)
        subsection = WindTemporalSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 4
        assert counts["tables"] == 4
        assert counts["figures"] == 6
        assert counts["total"] == 15

    def test_two_masts_basic(self, tmp_path: Path) -> None:
        collection = _make_temporal_collection(2)
        subsection = WindTemporalSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 4
        assert counts["tables"] == 8
        assert counts["figures"] == 12
        assert counts["total"] == 25

    def test_three_masts_stress(self, tmp_path: Path) -> None:
        collection = _make_temporal_collection(3)
        subsection = WindTemporalSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 4
        assert counts["tables"] == 12
        assert counts["figures"] == 18
        assert counts["total"] == 35

    def test_has_chinese_title(self, tmp_path: Path) -> None:
        collection = _make_temporal_collection(2)
        subsection = WindTemporalSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        assert "风速时序分析" in section_node.heading.text


# =============================================================================
# Weibull Integration Tests
# =============================================================================


class TestWeibullMultiMastIntegration:
    """Integration tests for WeibullSubsection with 1/2/3 masts."""

    def test_one_mast_regression(self, tmp_path: Path) -> None:
        collection = _make_weibull_collection(1)
        subsection = WeibullSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 1
        assert counts["tables"] == 1
        assert counts["figures"] == 1
        assert counts["total"] == 4

    def test_two_masts_basic(self, tmp_path: Path) -> None:
        collection = _make_weibull_collection(2)
        subsection = WeibullSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 1
        assert counts["tables"] == 2
        assert counts["figures"] == 2
        assert counts["total"] == 6

    def test_three_masts_stress(self, tmp_path: Path) -> None:
        collection = _make_weibull_collection(3)
        subsection = WeibullSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 1
        assert counts["tables"] == 3
        assert counts["figures"] == 3
        assert counts["total"] == 8

    def test_has_chinese_title(self, tmp_path: Path) -> None:
        collection = _make_weibull_collection(2)
        subsection = WeibullSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        assert "Weibull分布拟合" in section_node.heading.text


# =============================================================================
# WindFrequency Integration Tests
# =============================================================================


class TestWindFrequencyMultiMastIntegration:
    """Integration tests for WindFrequencySubsection with 1/2/3 masts."""

    def test_one_mast_regression(self, tmp_path: Path) -> None:
        collection = _make_wind_frequency_collection(1)
        subsection = WindFrequencySubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 1
        assert counts["tables"] == 3
        assert counts["figures"] == 1
        assert counts["total"] == 6

    def test_two_masts_basic(self, tmp_path: Path) -> None:
        collection = _make_wind_frequency_collection(2)
        subsection = WindFrequencySubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 1
        assert counts["tables"] == 6
        assert counts["figures"] == 2
        assert counts["total"] == 10

    def test_three_masts_stress(self, tmp_path: Path) -> None:
        collection = _make_wind_frequency_collection(3)
        subsection = WindFrequencySubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 1
        assert counts["tables"] == 9
        assert counts["figures"] == 3
        assert counts["total"] == 14

    def test_has_chinese_title(self, tmp_path: Path) -> None:
        collection = _make_wind_frequency_collection(2)
        subsection = WindFrequencySubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        assert "风速频率分析" in section_node.heading.text


# =============================================================================
# Turbulence Integration Tests
# =============================================================================


class TestTurbulenceMultiMastIntegration:
    """Integration tests for TurbulenceSubsection with 1/2/3 masts."""

    def test_one_mast_regression(self, tmp_path: Path) -> None:
        collection = _make_turbulence_collection(1)
        subsection = TurbulenceSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 2
        assert counts["tables"] == 1
        assert counts["figures"] == 1
        assert counts["total"] == 5

    def test_two_masts_basic(self, tmp_path: Path) -> None:
        collection = _make_turbulence_collection(2)
        subsection = TurbulenceSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 2
        assert counts["tables"] == 2
        assert counts["figures"] == 2
        assert counts["total"] == 7

    def test_three_masts_stress(self, tmp_path: Path) -> None:
        collection = _make_turbulence_collection(3)
        subsection = TurbulenceSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 2
        assert counts["tables"] == 3
        assert counts["figures"] == 3
        assert counts["total"] == 9

    def test_has_chinese_title(self, tmp_path: Path) -> None:
        collection = _make_turbulence_collection(2)
        subsection = TurbulenceSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        assert "湍流强度分析" in section_node.heading.text


# =============================================================================
# VerticalProfile Integration Tests
# =============================================================================


class TestVerticalProfileMultiMastIntegration:
    """Integration tests for VerticalProfileSubsection with 1/2/3 masts."""

    def test_one_mast_regression(self, tmp_path: Path) -> None:
        collection = _make_vertical_profile_collection(1)
        subsection = VerticalProfileSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 3
        assert counts["tables"] == 1
        assert counts["figures"] == 1
        assert counts["total"] == 6

    def test_two_masts_basic(self, tmp_path: Path) -> None:
        collection = _make_vertical_profile_collection(2)
        subsection = VerticalProfileSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 3
        assert counts["tables"] == 2
        assert counts["figures"] == 2
        assert counts["total"] == 8

    def test_three_masts_stress(self, tmp_path: Path) -> None:
        collection = _make_vertical_profile_collection(3)
        subsection = VerticalProfileSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        counts = _count_nodes(section_node)

        assert counts["headings"] == 1
        assert counts["paragraphs"] == 3
        assert counts["tables"] == 3
        assert counts["figures"] == 3
        assert counts["total"] == 10

    def test_has_chinese_title(self, tmp_path: Path) -> None:
        collection = _make_vertical_profile_collection(2)
        subsection = VerticalProfileSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        assert "垂直风廓线" in section_node.heading.text


# =============================================================================
# Full Pipeline Integration Test
# =============================================================================


def _create_three_mast_toml_config(tmp_path: Path) -> Path:
    masts = [
        {"name": f"M{i + 1}", "air_density": 1.225, "input": {"data": f"./M{i + 1}.parquet"}}
        for i in range(3)
    ]
    config = {
        "document": {
            "section": [
                {
                    "title": "风资源分析",
                    "subsections": [
                        {
                            "type": "timeseries",
                            "title": "测风年风资源分析",
                            "masts": masts,
                            "subsections": [
                                {"type": "wind_frequency"},
                                {"type": "temporal"},
                                {"type": "weibull"},
                                {"type": "vertical_profile"},
                                {"type": "turbulence"},
                                {"type": "wind_rose"},
                            ],
                        }
                    ],
                }
            ]
        }
    }
    path = tmp_path / "rep-ts-report.toml"
    with open(path, "wb") as f:
        tomli_w.dump(config, f)
    return path


class TestFullPipelineConfigToDocument:
    """Full pipeline test from TOML config to rendered Typst document."""

    def test_three_mast_toml_config_parses_correctly(self, tmp_path: Path) -> None:
        from cleanmast.subdomains.assessment.domain.value_objects.rep_ts_report_config import (
            RepTsReportConfig,
        )

        config_path = _create_three_mast_toml_config(tmp_path)
        config = RepTsReportConfig.from_toml(config_path)

        assert len(config.document.sections) == 1
        section = config.document.sections[0]
        assert section.title == "风资源分析"
        assert section.subsections is not None
        assert len(section.subsections) == 1
        ts_subsection = section.subsections[0]
        assert ts_subsection.type == "timeseries"
        assert ts_subsection.masts is not None
        assert len(ts_subsection.masts) == 3
        mast_names = [m.name for m in ts_subsection.masts]
        assert mast_names == ["M1", "M2", "M3"]
        assert ts_subsection.subsections is not None
        assert len(ts_subsection.subsections) == 6

    def test_three_mast_builder_produces_typst_document(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "typst_output"
        builder = AssessmentReportBuilder("风资源分析", output_dir)

        builder.add_section(
            WindRoseSection(atoms=_make_wind_rose_collection(3))
        )
        builder.add_section(
            WindTemporalSubsection(atoms=_make_temporal_collection(3))
        )
        builder.add_section(
            WeibullSubsection(atoms=_make_weibull_collection(3))
        )
        builder.add_section(
            WindFrequencySubsection(atoms=_make_wind_frequency_collection(3))
        )
        builder.add_section(
            TurbulenceSubsection(atoms=_make_turbulence_collection(3))
        )
        builder.add_section(
            VerticalProfileSubsection(atoms=_make_vertical_profile_collection(3))
        )

        document = builder.build_typst()
        assert isinstance(document, TypstDocument)
        assert len(document.children) > 0

        sections = [c for c in document.children if isinstance(c, TypstSection)]
        section_headings = [sec.heading for sec in sections]
        assert len(sections) == 6

        type_counts = {
            TypstHeading: len(section_headings) + len(sections),
            TypstParagraph: 0,
            TypstTable: 0,
            TypstFigure: 0,
        }
        for sec in sections:
            for child in sec.body:
                for typ in (TypstParagraph, TypstTable, TypstFigure):
                    if isinstance(child, typ):
                        type_counts[typ] += 1

        assert type_counts[TypstHeading] >= 6
        assert type_counts[TypstParagraph] >= 1
        assert type_counts[TypstTable] >= 1
        assert type_counts[TypstFigure] >= 1

    def test_three_mast_builder_produces_typst_content(self, tmp_path: Path) -> None:
        from typst_ir import serialize

        output_dir = tmp_path / "typst_output"
        builder = AssessmentReportBuilder("风资源分析", output_dir)

        builder.add_section(
            WindRoseSection(atoms=_make_wind_rose_collection(3))
        )
        builder.add_section(
            WindTemporalSubsection(atoms=_make_temporal_collection(3))
        )
        builder.add_section(
            WeibullSubsection(atoms=_make_weibull_collection(3))
        )
        builder.add_section(
            WindFrequencySubsection(atoms=_make_wind_frequency_collection(3))
        )
        builder.add_section(
            TurbulenceSubsection(atoms=_make_turbulence_collection(3))
        )
        builder.add_section(
            VerticalProfileSubsection(atoms=_make_vertical_profile_collection(3))
        )

        document = builder.build_typst()
        assert isinstance(document, TypstDocument)

        typ_content = serialize(document)
        assert "风向风能分布" in typ_content
        assert "风速时序分析" in typ_content
        assert "Weibull分布拟合" in typ_content
        assert "风速频率分析" in typ_content
        assert "湍流强度分析" in typ_content
        assert "垂直风廓线" in typ_content
