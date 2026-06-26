"""Failing TDD scaffold for subsection renderer merged-summary behavior.

Waves 2-3 RED phase: these tests assert that each subsection renderer
produces merged summary paragraphs across multiple masts using
merge_paragraphs(). They are expected to FAIL until renderers are refactored.
"""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import polars as pl
import pytest
from cleanmast.subdomains.assessment.subdomains.wind_temporal.entities.daily_pattern_atom import (
    SingleMastDailyPatternAtom,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_multi_atom import (
    SingleMastTurbulenceMultiHeightAtom,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_summary_atom import (
    SingleMastTurbulenceSummaryAtom,
)
from cleanmast.subdomains.assessment.subdomains.weibull.entities.weibull_subgrid_atom import (
    SingleMastWeibullSubgridAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_frequency.entities.wind_frequency_hours_atom import (
    SingleMastWindFrequencyHoursAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.entities.wind_rose_atom import (
    SingleMastMonthlyWindFrequencyRoseAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.entities.wind_rose_grid_atom import (
    SingleMastMonthlyWindRoseGridAtom,
)
from cleanmast.subdomains.assessment.subdomains.vertical_profile.entities.wind_shear_matrix_atom import (
    SingleMastWindShearExponentAtom,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.services.turbulence_section import (
    TurbulenceSubsection,
)
from cleanmast.subdomains.assessment.subdomains.vertical_profile.services.vertical_profile_section import (
    VerticalProfileSubsection,
)
from cleanmast.subdomains.assessment.subdomains.weibull.services.weibull_section import (
    WeibullSubsection,
)
from cleanmast.subdomains.assessment.subdomains.wind_frequency.services.wind_frequency_section import (
    WindFrequencySubsection,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.services.wind_rose_section import (
    WindRoseSection,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.services.wind_temporal_section import (
    WindTemporalSubsection,
)
from cleanmast.subdomains.assessment.shared.ir_types import (
    TypstFigure,
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.value_objects import (
    AtomCollection,
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.subdomains.vertical_profile.value_objects.schemas import (
    VerticalProfileSchema,
    WindShearSchema,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.value_objects.schemas import (
    TemporalPatternSchema,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.value_objects.schemas import (
    TurbulenceSchema,
)
from cleanmast.subdomains.assessment.subdomains.weibull.value_objects.schemas import (
    WeibullSchema,
)
from cleanmast.subdomains.assessment.subdomains.wind_frequency.value_objects.schemas import (
    WindFrequencySchema,
)
from cleanmast.subdomains.assessment.subdomains.wind_rose.value_objects.schemas import (
    WindRoseSchema,
)


def _sample_turbulence_df() -> pl.DataFrame:
    rows = []
    for height in [80.0, 120.0]:
        marker = "外推" if height > 100 else None
        for wind_speed in range(3, 16, 2):
            mean_ti = 0.18 - (wind_speed - 3) * 0.005 - (height - 80) * 0.0002
            std_ti = 0.03
            rep_ti = mean_ti + 1.28 * std_ti
            iec_cat = "A+" if rep_ti > 0.18 else "A" if rep_ti > 0.16 else "B"
            rows.append({
                "wind_speed_bin": wind_speed,
                "height": height,
                "interpolation_marker": marker,
                "mean_ti": mean_ti,
                "std_ti": std_ti,
                "representative_ti": rep_ti,
                "iec_category": iec_cat,
                "count": 42,
            })
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
        rows.append({
            "height": height,
            "interpolation_marker": marker,
            "wind_speed_mean": wind_speed,
            "wind_speed_std": wind_speed * 0.15,
            "alpha": alpha if i == 0 else None,
            "r_squared": 0.98 if i == 0 else None,
        })
    return pl.DataFrame(rows)


def _sample_weibull_df() -> pl.DataFrame:
    bin_centers = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5]
    rows = []
    for height in [80.0, 120.0]:
        marker = "外推" if height > 100 else None
        shape_k = 2.0 + (height - 80) * 0.005
        scale_c = 7.0 + (height - 80) * 0.02
        mean_speed = scale_c * np.exp(1 / shape_k * np.log(1 + 1 / shape_k))
        observed_density = []
        fitted_density = []
        for b in bin_centers:
            x = b / scale_c
            pdf_val = (shape_k / scale_c) * (x ** (shape_k - 1)) * np.exp(-(x ** shape_k))
            observed_density.append(max(0.001, pdf_val))
            fitted_density.append(max(0.001, pdf_val * 0.95))
        rows.append({
            "height": height,
            "interpolation_marker": marker,
            "shape_k": shape_k,
            "scale_c": scale_c,
            "mean_speed": mean_speed,
            "bin_centers": bin_centers,
            "observed_density": observed_density,
            "fitted_density": fitted_density,
        })
    return pl.DataFrame(rows)


def _sample_wind_frequency_df() -> pl.DataFrame:
    rows = []
    for height in [80.0, 120.0]:
        marker = "外推" if height > 100 else None
        for bin_start in range(0, 15):
            bin_end = bin_start + 1
            bin_center = bin_start + 0.5
            freq = 0.15 * (bin_center / 7) ** 2 * np.exp(-(bin_center / 7) ** 2)
            occurrence_hours = freq * 8760
            power_freq = freq * (bin_center ** 3) / 500
            power_hours = power_freq * 8760
            rows.append({
                "height": height,
                "interpolation_marker": marker,
                "bin_start": float(bin_start),
                "bin_end": float(bin_end),
                "bin_center": bin_center,
                "frequency": freq,
                "occurrence_hours": occurrence_hours,
                "power_frequency": power_freq,
                "power_hours": power_hours,
            })
    return pl.DataFrame(rows)


def _sample_wind_rose_df() -> pl.DataFrame:
    sector_names = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    rows = []
    for month in [1, 2, 3]:
        month_name = f"{month}月"
        for height in [80.0, 120.0]:
            marker = "外推" if height > 100 else None
            for sector, name in enumerate(sector_names):
                freq = 0.2 if sector == 0 else 0.05
                power = 300.0 if sector == 0 else 100.0
                rows.append({
                    "month": month,
                    "month_name": month_name,
                    "sector": sector,
                    "sector_name": name,
                    "height": height,
                    "frequency": freq,
                    "energy_frequency": 0.8 * freq,
                    "wind_power_density": power,
                    "interpolation_marker": marker,
                })
    return pl.DataFrame(rows)


def _sample_temporal_df() -> pl.DataFrame:
    from datetime import datetime
    timestamps = pl.datetime_range(
        start=datetime(2024, 1, 1),
        end=datetime(2024, 1, 2),
        interval="1h",
        eager=True,
    )
    rows = []
    for height in [80.0, 120.0]:
        for ts in timestamps:
            hour = ts.hour
            month = ts.month
            wind_speed = 5.0 + np.sin(hour * np.pi / 12) * 2
            wind_power = 0.5 * 1.225 * wind_speed ** 3
            rows.append({
                "timestamp": ts,
                "hour": hour,
                "month": month,
                "wind_speed": wind_speed,
                "wind_power": wind_power,
                "height": height,
                "mean_speed": wind_speed * 1.1,
                "mean_power": wind_power * 1.2,
                "interpolation_marker": None,
            })
    return pl.DataFrame(rows)


@pytest.fixture
def multi_mast_turbulence_collection() -> AtomCollection:
    meta1 = SingleMastMeta(mast_name="M01")
    meta2 = SingleMastMeta(mast_name="M02")
    df = _sample_turbulence_df()
    atom1 = SingleMastTurbulenceSummaryAtom.create(
        schema=TurbulenceSchema,
        df=df,
        meta=meta1,
    )
    atom2 = SingleMastTurbulenceSummaryAtom.create(
        schema=TurbulenceSchema,
        df=df,
        meta=meta2,
    )
    atom3 = SingleMastTurbulenceMultiHeightAtom.create(
        schema=TurbulenceSchema,
        df=df,
        meta=meta1,
    )
    atom4 = SingleMastTurbulenceMultiHeightAtom.create(
        schema=TurbulenceSchema,
        df=df,
        meta=meta2,
    )
    return AtomCollection.from_dict({
        "M01": [atom1, atom3],
        "M02": [atom2, atom4],
    })


@pytest.fixture
def multi_mast_vertical_profile_collection() -> AtomCollection:
    meta1 = SingleMastMeta(mast_name="M01")
    meta2 = SingleMastMeta(mast_name="M02")
    profile_df = _sample_vertical_profile_df()
    shear_df = pl.DataFrame({
        "from_height": [50.0, 50.0, 80.0],
        "to_height": [80.0, 120.0, 120.0],
        "alpha_mean": [0.15, 0.14, 0.13],
        "alpha_std": [0.03, 0.025, 0.02],
        "alpha_min": [0.08, 0.07, 0.06],
        "alpha_max": [0.25, 0.22, 0.20],
    })
    atom1 = SingleMastWindShearExponentAtom.create(
        profile_schema=VerticalProfileSchema,
        profile_df=profile_df,
        shear_schema=WindShearSchema,
        shear_df=shear_df,
        meta=meta1,
    )
    atom2 = SingleMastWindShearExponentAtom.create(
        profile_schema=VerticalProfileSchema,
        profile_df=profile_df,
        shear_schema=WindShearSchema,
        shear_df=shear_df,
        meta=meta2,
    )
    return AtomCollection.from_dict({
        "M01": [atom1],
        "M02": [atom2],
    })


@pytest.fixture
def multi_mast_weibull_collection() -> AtomCollection:
    meta1 = SingleMastMeta(mast_name="M01")
    meta2 = SingleMastMeta(mast_name="M02")
    df = _sample_weibull_df()
    m01_subgrid = SingleMastWeibullSubgridAtom.create(
        schema=WeibullSchema,
        df=df,
        meta=meta1,
    )
    m02_subgrid = SingleMastWeibullSubgridAtom.create(
        schema=WeibullSchema,
        df=df,
        meta=meta2,
    )
    return AtomCollection.from_dict({
        "M01": [m01_subgrid],
        "M02": [m02_subgrid],
    })


@pytest.fixture
def multi_mast_wind_frequency_collection() -> AtomCollection:
    meta1 = SingleMastMeta(mast_name="M01")
    meta2 = SingleMastMeta(mast_name="M02")
    df = _sample_wind_frequency_df()
    atom1 = SingleMastWindFrequencyHoursAtom.create(
        schema=WindFrequencySchema,
        df=df,
        meta=meta1,
    )
    atom2 = SingleMastWindFrequencyHoursAtom.create(
        schema=WindFrequencySchema,
        df=df,
        meta=meta2,
    )
    return AtomCollection.from_dict({
        "M01": [atom1],
        "M02": [atom2],
    })


@pytest.fixture
def multi_mast_wind_temporal_collection() -> AtomCollection:
    meta1 = SingleMastMeta(mast_name="M01")
    meta2 = SingleMastMeta(mast_name="M02")
    df = _sample_temporal_df()
    atom1 = SingleMastDailyPatternAtom.create(
        schema=TemporalPatternSchema,
        df=df,
        meta=meta1,
    )
    atom2 = SingleMastDailyPatternAtom.create(
        schema=TemporalPatternSchema,
        df=df,
        meta=meta2,
    )
    return AtomCollection.from_dict({
        "M01": [atom1],
        "M02": [atom2],
    })


@pytest.fixture
def multi_mast_wind_rose_collection() -> AtomCollection:
    meta1 = SingleMastMeta(mast_name="M01")
    meta2 = SingleMastMeta(mast_name="M02")
    df = _sample_wind_rose_df()
    rose1 = SingleMastMonthlyWindFrequencyRoseAtom.create(
        schema=WindRoseSchema,
        df=df,
        meta=meta1,
    )
    rose2 = SingleMastMonthlyWindFrequencyRoseAtom.create(
        schema=WindRoseSchema,
        df=df,
        meta=meta2,
    )
    grid1 = SingleMastMonthlyWindRoseGridAtom.create(
        schema=WindRoseSchema,
        df=df,
        meta=meta1,
    )
    grid2 = SingleMastMonthlyWindRoseGridAtom.create(
        schema=WindRoseSchema,
        df=df,
        meta=meta2,
    )
    return AtomCollection.from_dict({
        "M01": [rose1, grid1],
        "M02": [rose2, grid2],
    })


class TestWindRoseSectionMergedSummary:
    def test_renders_merged_summary_for_multiple_masts(
        self,
        multi_mast_wind_rose_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        with patch(
            "cleanmast.subdomains.assessment.shared.utils.subsection_renderer.merge_paragraphs",
            create=True,
            return_value=TypstParagraph(text="M01 M02 merged summary"),
        ) as mock_merge:
            subsection = WindRoseSection(atoms=multi_mast_wind_rose_collection)
            section_node = subsection.render_ir(tmp_path)

        assert mock_merge.called, "Expected merge_paragraphs to be called for multi-mast summary"

        paragraphs = [n for n in section_node.body if isinstance(n, TypstParagraph)]
        assert len(paragraphs) > 0, "Expected at least one merged summary paragraph"

        merged_text = " ".join(p.text for p in paragraphs)
        assert "M01" in merged_text, "Merged summary should include M01"
        assert "M02" in merged_text, "Merged summary should include M02"


class TestTurbulenceSubsectionMergedSummary:
    def test_renders_merged_summary_for_multiple_masts(
        self,
        multi_mast_turbulence_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        with patch(
            "cleanmast.subdomains.assessment.shared.utils.subsection_renderer.merge_paragraphs",
            return_value=TypstParagraph(text="M01 M02 merged summary"),
        ) as mock_merge:
            subsection = TurbulenceSubsection(atoms=multi_mast_turbulence_collection)
            section_node = subsection.render_ir(tmp_path)

        assert mock_merge.called, "Expected merge_paragraphs to be called for multi-mast summary"

        paragraphs = [n for n in section_node.body if isinstance(n, TypstParagraph)]
        assert len(paragraphs) > 0, "Expected at least one merged summary paragraph"

        merged_text = " ".join(p.text for p in paragraphs)
        assert "M01" in merged_text, "Merged summary should include M01"
        assert "M02" in merged_text, "Merged summary should include M02"


class TestVerticalProfileSubsectionMergedSummary:
    def test_renders_merged_summary_for_multiple_masts(
        self,
        multi_mast_vertical_profile_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        with patch(
            "cleanmast.subdomains.assessment.shared.utils.subsection_renderer.merge_paragraphs",
            return_value=TypstParagraph(text="M01 M02 merged summary"),
        ) as mock_merge:
            subsection = VerticalProfileSubsection(atoms=multi_mast_vertical_profile_collection)
            section_node = subsection.render_ir(tmp_path)

        assert mock_merge.called, "Expected merge_paragraphs to be called for multi-mast summary"

        paragraphs = [n for n in section_node.body if isinstance(n, TypstParagraph)]
        assert len(paragraphs) > 0, "Expected at least one merged summary paragraph"

        merged_text = " ".join(p.text for p in paragraphs)
        assert "M01" in merged_text, "Merged summary should include M01"
        assert "M02" in merged_text, "Merged summary should include M02"


class TestWeibullSubsectionMergedSummary:
    def test_renders_no_summary_and_outputs_tables_and_figures_for_multiple_masts(
        self,
        multi_mast_weibull_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        subsection = WeibullSubsection(atoms=multi_mast_weibull_collection)
        section_node = subsection.render_ir(tmp_path)

        paragraphs = [n for n in section_node.body if isinstance(n, TypstParagraph)]
        assert len(paragraphs) == 0, "WeibullSubsection must produce zero summaries per spec"

        tables = [n for n in section_node.body if isinstance(n, TypstTable)]
        assert len(tables) == 2, "Expected 2 tables for 2 masts with WeibullSubgridAtom"

        figures = [n for n in section_node.body if isinstance(n, TypstFigure)]
        assert len(figures) == 0, "WeibullSubgridAtom produces no figures for test data heights"


class TestWindFrequencySubsectionMergedSummary:
    def test_renders_merged_summary_for_multiple_masts(
        self,
        multi_mast_wind_frequency_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        with patch(
            "cleanmast.subdomains.assessment.shared.utils.subsection_renderer.merge_paragraphs",
            create=True,
            return_value=TypstParagraph(text="M01 M02 merged summary"),
        ) as mock_merge:
            subsection = WindFrequencySubsection(atoms=multi_mast_wind_frequency_collection)
            section_node = subsection.render_ir(tmp_path)

        assert mock_merge.called, "Expected merge_paragraphs to be called for multi-mast summary"

        paragraphs = [n for n in section_node.body if isinstance(n, TypstParagraph)]
        assert len(paragraphs) > 0, "Expected at least one merged summary paragraph"

        merged_text = " ".join(p.text for p in paragraphs)
        assert "M01" in merged_text, "Merged summary should include M01"
        assert "M02" in merged_text, "Merged summary should include M02"


class TestWindTemporalSubsectionMergedSummary:
    def test_renders_merged_summary_for_multiple_masts(
        self,
        multi_mast_wind_temporal_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        with patch(
            "cleanmast.subdomains.assessment.shared.utils.subsection_renderer.merge_paragraphs",
            return_value=TypstParagraph(text="M01 M02 merged summary"),
        ) as mock_merge:
            subsection = WindTemporalSubsection(atoms=multi_mast_wind_temporal_collection)
            section_node = subsection.render_ir(tmp_path)

        assert mock_merge.called, "Expected merge_paragraphs to be called for multi-mast summary"

        paragraphs = [n for n in section_node.body if isinstance(n, TypstParagraph)]
        assert len(paragraphs) > 0, "Expected at least one merged summary paragraph"

        merged_text = " ".join(p.text for p in paragraphs)
        assert "M01" in merged_text, "Merged summary should include M01"
        assert "M02" in merged_text, "Merged summary should include M02"


def _assert_three_phase_ordering(body: list) -> None:
    if not body:
        pytest.skip("Empty body, nothing to verify")

    first_table_idx = next(
        (i for i, n in enumerate(body) if isinstance(n, TypstTable)), None
    )
    first_figure_idx = next(
        (i for i, n in enumerate(body) if isinstance(n, TypstFigure)), None
    )

    if first_table_idx is not None:
        assert all(isinstance(n, TypstParagraph) for n in body[:first_table_idx]), (
            "All nodes before first table must be TypstParagraph"
        )
    else:
        assert all(isinstance(n, TypstParagraph) for n in body), (
            "All nodes must be TypstParagraph when no tables exist"
        )
        return

    if first_figure_idx is not None:
        assert first_table_idx <= first_figure_idx, (
            "Tables must appear before figures"
        )
        assert all(
            isinstance(n, TypstTable) for n in body[first_table_idx:first_figure_idx]
        ), "All nodes between first table and first figure must be TypstTable"
        assert all(isinstance(n, TypstFigure) for n in body[first_figure_idx:]), (
            "All nodes from first figure onward must be TypstFigure"
        )
    else:
        assert all(isinstance(n, TypstTable) for n in body[first_table_idx:]), (
            "All nodes from first table onward must be TypstTable when no figures exist"
        )


class TestSubsectionThreePhaseOrdering:
    def test_wind_temporal_three_phase_ordering(
        self,
        multi_mast_wind_temporal_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        subsection = WindTemporalSubsection(atoms=multi_mast_wind_temporal_collection)
        section_node = subsection.render_ir(tmp_path)
        _assert_three_phase_ordering(section_node.body)

    def test_wind_frequency_three_phase_ordering(
        self,
        multi_mast_wind_frequency_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        subsection = WindFrequencySubsection(atoms=multi_mast_wind_frequency_collection)
        section_node = subsection.render_ir(tmp_path)
        _assert_three_phase_ordering(section_node.body)

    def test_turbulence_three_phase_ordering(
        self,
        multi_mast_turbulence_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        subsection = TurbulenceSubsection(atoms=multi_mast_turbulence_collection)
        section_node = subsection.render_ir(tmp_path)
        _assert_three_phase_ordering(section_node.body)

    def test_weibull_three_phase_ordering(
        self,
        multi_mast_weibull_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        subsection = WeibullSubsection(atoms=multi_mast_weibull_collection)
        section_node = subsection.render_ir(tmp_path)

        paragraphs = [n for n in section_node.body if isinstance(n, TypstParagraph)]
        assert len(paragraphs) == 0, "WeibullSubsection must produce zero summaries per spec"

        _assert_three_phase_ordering(section_node.body)

    def test_vertical_profile_three_phase_ordering(
        self,
        multi_mast_vertical_profile_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        subsection = VerticalProfileSubsection(atoms=multi_mast_vertical_profile_collection)
        section_node = subsection.render_ir(tmp_path)
        _assert_three_phase_ordering(section_node.body)

    def test_wind_rose_three_phase_ordering(
        self,
        multi_mast_wind_rose_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        subsection = WindRoseSection(atoms=multi_mast_wind_rose_collection)
        section_node = subsection.render_ir(tmp_path)
        _assert_three_phase_ordering(section_node.body)
