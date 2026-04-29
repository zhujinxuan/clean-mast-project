"""Integration tests for all report subsections.

Tests cover all 6 subsections:
- WindRoseSubsection
- WindTemporalSubsection  
- WeibullSubsection
- WindFrequencySubsection
- TurbulenceSubsection
- VerticalProfileSubsection

Each test verifies:
- render_ir() produces valid IR nodes
- Chinese titles are present in IR nodes
- Config toggles work correctly
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.entities.report_atom import ReportAtom
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
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_intensity import (
    SingleMastTurbulenceIntensityAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_multi import (
    SingleMastTurbulenceMultiHeightAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_per_height import (
    SingleMastTurbulencePerHeightAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_sector import (
    SingleMastTurbulenceSectorAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_summary import (
    SingleMastTurbulenceSummaryAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.weibull_subgrid import (
    SingleMastWeibullSubgridAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_frequency_hours import (
    SingleMastWindFrequencyHoursAtom,
)
from cleanmast.subdomains.assessment.domain.entities.single_mast.wind_rose import (
    SingleMastMonthlyWindFrequencyRoseAtom,
    SingleMastWindPowerRoseAtom,
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
    TypstFigure,
    TypstHeading,
    TypstParagraph,
    TypstSection,
    TypstTable,
)
from cleanmast.subdomains.assessment.domain.value_objects import (
    AtomCollection,
    ReportSubsectionConfig,
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TemporalPatternSchema,
    TurbulenceSchema,
    TurbulenceSectorSchema,
    WeibullSchema,
    WindFrequencySchema,
    WindRoseSchema,
)

# =============================================================================
# Fixtures - Sample Data
# =============================================================================


@pytest.fixture
def sample_mast_meta() -> SingleMastMeta:
    """Create sample SingleMastMeta for testing."""
    return SingleMastMeta(mast_name="M01")


@pytest.fixture
def sample_wind_rose_df() -> pl.DataFrame:
    """Create sample wind rose DataFrame."""
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


@pytest.fixture
def sample_temporal_df() -> pl.DataFrame:
    """Create sample temporal pattern DataFrame."""
    timestamps = pl.datetime_range(
        start=datetime(2024, 1, 1),
        end=datetime(2024, 1, 3),
        interval="1h",
        eager=True,
    )
    
    rows = []
    for height in [80.0, 120.0]:
        marker = "外推" if height > 100 else None
        for ts in timestamps:
            hour = ts.hour
            month = ts.month
            wind_speed = 5.0 + np.sin(hour * np.pi / 12) * 2 + (height - 80) * 0.02
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
                "interpolation_marker": marker,
            })
    return pl.DataFrame(rows)


@pytest.fixture
def sample_weibull_df() -> pl.DataFrame:
    """Create sample Weibull distribution DataFrame."""
    bin_centers = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5]
    
    rows = []
    for height in [80.0, 120.0]:
        marker = "外推" if height > 100 else None
        shape_k = 2.0 + (height - 80) * 0.005
        scale_c = 7.0 + (height - 80) * 0.02
        mean_speed = scale_c * np.exp(1 / shape_k * np.log(1 + 1 / shape_k))
        
        # Generate some realistic density values - ensure no NaN
        observed_density = []
        fitted_density = []
        for b in bin_centers:
            # Weibull PDF formula: (k/c) * (v/c)^(k-1) * exp(-(v/c)^k)
            x = b / scale_c
            pdf_val = (shape_k / scale_c) * (x ** (shape_k - 1)) * np.exp(-(x ** shape_k))
            observed_density.append(max(0.001, pdf_val))  # Ensure positive
            fitted_density.append(max(0.001, pdf_val * 0.95))  # Slightly different
        
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


@pytest.fixture
def sample_wind_frequency_df() -> pl.DataFrame:
    """Create sample wind frequency distribution DataFrame."""
    rows = []
    for height in [80.0, 120.0]:
        marker = "外推" if height > 100 else None
        for bin_start in range(0, 15):
            bin_end = bin_start + 1 if bin_start < 14 else bin_start + 1
            bin_center = bin_start + 0.5
            # Weibull-like distribution
            freq = 0.15 * (bin_center / 7) ** 2 * np.exp(-(bin_center / 7) ** 2)
            occurrence_hours = freq * 8760
            power_freq = freq * (bin_center ** 3) / 500  # Simplified power relation
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


@pytest.fixture
def sample_turbulence_df() -> pl.DataFrame:
    """Create sample turbulence intensity DataFrame."""
    rows = []
    for height in [80.0, 120.0]:
        marker = "外推" if height > 100 else None
        for wind_speed in range(3, 16, 2):
            # TI decreases with wind speed and height
            mean_ti = 0.18 - (wind_speed - 3) * 0.005 - (height - 80) * 0.0002
            std_ti = 0.03
            rep_ti = mean_ti + 1.28 * std_ti
            # Classify by TI
            if rep_ti > 0.18:
                iec_cat = "A+"
            elif rep_ti > 0.16:
                iec_cat = "A"
            elif rep_ti > 0.14:
                iec_cat = "B"
            else:
                iec_cat = "C"
            
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


@pytest.fixture
def sample_turbulence_sector_df() -> pl.DataFrame:
    """Create sample turbulence sector DataFrame."""
    sector_names = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    
    rows = []
    for height in [80.0, 120.0]:
        marker = "外推" if height > 100 else None
        for sector, name in enumerate(sector_names):
            mean_ti = 0.15 + (sector % 4) * 0.01
            rep_ti = mean_ti * 1.2
            iec_cat = "A" if rep_ti > 0.16 else "B"
            
            rows.append({
                "sector": sector,
                "sector_name": name,
                "height": height,
                "interpolation_marker": marker,
                "mean_ti": mean_ti,
                "representative_ti": rep_ti,
                "iec_category": iec_cat,
            })
    return pl.DataFrame(rows)


@pytest.fixture
def sample_vertical_profile_df() -> pl.DataFrame:
    """Create sample vertical profile DataFrame."""
    rows = []
    heights = [50.0, 80.0, 100.0, 120.0]
    alpha = 0.15  # Wind shear exponent
    
    for i, height in enumerate(heights):
        marker = "外推" if height > 100 else None
        # Power law profile
        ref_speed = 5.5
        ref_height = 80.0
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


# =============================================================================
# Fixtures - Atoms
# =============================================================================


@pytest.fixture
def wind_rose_atoms(
    sample_wind_rose_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> tuple[SingleMastMonthlyWindFrequencyRoseAtom, SingleMastWindPowerRoseAtom]:
    """Create wind rose atoms."""
    freq_atom = SingleMastMonthlyWindFrequencyRoseAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_df,
        meta=sample_mast_meta,
    )
    power_atom = SingleMastWindPowerRoseAtom.create(
        schema=WindRoseSchema,
        df=sample_wind_rose_df,
        meta=sample_mast_meta,
    )
    return freq_atom, power_atom


@pytest.fixture
def wind_temporal_atoms(
    sample_temporal_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> list[ReportAtom[Any, Any]]:
    """Create wind temporal atoms."""
    atoms = [
        SingleMastWindTimeseriesAtom.create(
            schema=TemporalPatternSchema,
            df=sample_temporal_df,
            meta=sample_mast_meta,
        ),
        SingleMastDailyPatternAtom.create(
            schema=TemporalPatternSchema,
            df=sample_temporal_df,
            meta=sample_mast_meta,
        ),
        SingleMastDailyPowerPatternAtom.create(
            schema=TemporalPatternSchema,
            df=sample_temporal_df,
            meta=sample_mast_meta,
        ),
        SingleMastMonthlyPatternAtom.create(
            schema=TemporalPatternSchema,
            df=sample_temporal_df,
            meta=sample_mast_meta,
        ),
        SingleMastMonthlyPowerPatternAtom.create(
            schema=TemporalPatternSchema,
            df=sample_temporal_df,
            meta=sample_mast_meta,
        ),
        SingleMastMonthlyDailyWindAtom.create(
            schema=TemporalPatternSchema,
            df=sample_temporal_df,
            meta=sample_mast_meta,
        ),
        SingleMastMonthlyDailyPowerAtom.create(
            schema=TemporalPatternSchema,
            df=sample_temporal_df,
            meta=sample_mast_meta,
        ),
    ]
    return atoms


@pytest.fixture
def weibull_atoms(
    sample_weibull_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> list[ReportAtom[Any, Any]]:
    """Create Weibull atoms."""
    subgrid_atom = SingleMastWeibullSubgridAtom.create(
        schema=WeibullSchema,
        df=sample_weibull_df,
        meta=sample_mast_meta,
    )
    return [subgrid_atom]


@pytest.fixture
def wind_frequency_atom(
    sample_wind_frequency_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastWindFrequencyHoursAtom:
    """Create wind frequency hours atom."""
    return SingleMastWindFrequencyHoursAtom.create(
        schema=WindFrequencySchema,
        df=sample_wind_frequency_df,
        meta=sample_mast_meta,
    )


@pytest.fixture
def turbulence_atoms(
    sample_turbulence_df: pl.DataFrame,
    sample_turbulence_sector_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> list[ReportAtom[Any, Any]]:
    """Create turbulence atoms."""
    intensity_atom = SingleMastTurbulenceIntensityAtom.create(
        schema=TurbulenceSchema,
        df=sample_turbulence_df,
        meta=sample_mast_meta,
    )
    summary_atom = SingleMastTurbulenceSummaryAtom.create(
        schema=TurbulenceSchema,
        df=sample_turbulence_df,
        meta=sample_mast_meta,
    )
    sector_atom = SingleMastTurbulenceSectorAtom.create(
        schema=TurbulenceSectorSchema,
        df=sample_turbulence_sector_df,
        meta=sample_mast_meta,
    )
    # Multi-height uses turbulence schema
    multi_atom = SingleMastTurbulenceMultiHeightAtom.create(
        schema=TurbulenceSchema,
        df=sample_turbulence_df,
        meta=sample_mast_meta,
    )
    per_height_80 = SingleMastTurbulencePerHeightAtom.create_with_height(
        schema=TurbulenceSchema,
        df=sample_turbulence_df,
        meta=sample_mast_meta,
        height=80.0,
    )
    per_height_120 = SingleMastTurbulencePerHeightAtom.create_with_height(
        schema=TurbulenceSchema,
        df=sample_turbulence_df,
        meta=sample_mast_meta,
        height=120.0,
    )
    return [intensity_atom, summary_atom, sector_atom, multi_atom, per_height_80, per_height_120]


# =============================================================================
# Fixtures - Atom Collections
# =============================================================================


@pytest.fixture
def wind_rose_collection(
    wind_rose_atoms: tuple,
) -> AtomCollection:
    """Create AtomCollection with wind rose atoms."""
    return AtomCollection.from_dict({
        "M01": list(wind_rose_atoms),
    })


@pytest.fixture
def wind_temporal_collection(
    wind_temporal_atoms: list,
) -> AtomCollection:
    """Create AtomCollection with wind temporal atoms."""
    return AtomCollection.from_dict({
        "M01": wind_temporal_atoms,
    })


@pytest.fixture
def weibull_collection(
    weibull_atoms: list,
) -> AtomCollection:
    """Create AtomCollection with Weibull atoms."""
    return AtomCollection.from_dict({
        "M01": weibull_atoms,
    })


@pytest.fixture
def wind_frequency_collection(
    wind_frequency_atom: SingleMastWindFrequencyHoursAtom,
) -> AtomCollection:
    """Create AtomCollection with wind frequency atom."""
    return AtomCollection.from_dict({
        "M01": [wind_frequency_atom],
    })


@pytest.fixture
def turbulence_collection(
    turbulence_atoms: list,
) -> AtomCollection:
    """Create AtomCollection with turbulence atoms."""
    return AtomCollection.from_dict({
        "M01": turbulence_atoms,
    })


@pytest.fixture
def vertical_profile_collection(
    wind_shear_matrix_atom: SingleMastWindShearExponentAtom,
) -> AtomCollection:
    """Create AtomCollection with vertical profile atom."""
    return AtomCollection.from_dict({
        "M01": [wind_shear_matrix_atom],
    })


# =============================================================================
# Tests - WindRoseSubsection
# =============================================================================


class TestWindRoseSubsection:
    """Tests for WindRoseSubsection."""

    def test_render_ir_produces_nodes(self, wind_rose_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() produces valid IR nodes."""
        subsection = WindRoseSection(atoms=wind_rose_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert isinstance(section_node, TypstSection)
        assert isinstance(section_node.heading, TypstHeading)

    def test_render_ir_has_chinese_title(self, wind_rose_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() includes Chinese title in heading."""
        subsection = WindRoseSection(atoms=wind_rose_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert "风向风能分布" in section_node.heading.text

    def test_render_ir_has_table_nodes(self, wind_rose_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() includes TypstTable nodes."""
        subsection = WindRoseSection(atoms=wind_rose_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert any(isinstance(n, TypstTable) for n in section_node.body)

    def test_render_ir_has_figure_nodes(self, wind_rose_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() includes TypstFigure nodes."""
        subsection = WindRoseSection(atoms=wind_rose_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert any(isinstance(n, TypstFigure) for n in section_node.body)

    def test_custom_title(self, wind_rose_collection: AtomCollection, tmp_path: Path) -> None:
        """Test custom title can be set."""
        subsection = WindRoseSection(
            atoms=wind_rose_collection,
            title="自定义风玫瑰标题",
        )
        section_node = subsection.render_ir(tmp_path)
        
        assert "自定义风玫瑰标题" in section_node.heading.text


# =============================================================================
# Tests - WindTemporalSubsection
# =============================================================================


class TestWindTemporalSubsection:
    """Tests for WindTemporalSubsection."""

    def test_render_ir_produces_nodes(self, wind_temporal_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() produces valid IR nodes."""
        subsection = WindTemporalSubsection(atoms=wind_temporal_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert isinstance(section_node, TypstSection)
        assert isinstance(section_node.heading, TypstHeading)

    def test_render_ir_has_chinese_title(self, wind_temporal_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() includes Chinese title."""
        subsection = WindTemporalSubsection(atoms=wind_temporal_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert "风速时序分析" in section_node.heading.text

    def test_render_ir_has_figure_nodes(self, wind_temporal_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() includes TypstFigure nodes."""
        subsection = WindTemporalSubsection(atoms=wind_temporal_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert any(isinstance(n, TypstFigure) for n in section_node.body)

    def test_custom_title(self, wind_temporal_collection: AtomCollection, tmp_path: Path) -> None:
        """Test custom title can be set."""
        subsection = WindTemporalSubsection(
            atoms=wind_temporal_collection,
            title="自定义时序标题",
        )
        section_node = subsection.render_ir(tmp_path)
        
        assert "自定义时序标题" in section_node.heading.text


# =============================================================================
# Tests - WeibullSubsection
# =============================================================================


class TestWeibullSubsection:
    """Tests for WeibullSubsection."""

    def test_render_ir_produces_nodes(self, weibull_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() produces valid IR nodes."""
        subsection = WeibullSubsection(atoms=weibull_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert isinstance(section_node, TypstSection)
        assert isinstance(section_node.heading, TypstHeading)

    def test_render_ir_has_chinese_title(self, weibull_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() includes Chinese title."""
        subsection = WeibullSubsection(atoms=weibull_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert "Weibull分布拟合" in section_node.heading.text

    def test_render_ir_has_table_nodes(self, weibull_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() includes TypstTable nodes."""
        subsection = WeibullSubsection(atoms=weibull_collection)
        section_node = subsection.render_ir(tmp_path)

        assert any(isinstance(n, TypstTable) for n in section_node.body)


class TestWindFrequencySubsection:
    """Tests for WindFrequencySubsection."""

    def test_render_ir_produces_nodes(self, wind_frequency_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() produces valid IR nodes."""
        subsection = WindFrequencySubsection(atoms=wind_frequency_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert isinstance(section_node, TypstSection)
        assert isinstance(section_node.heading, TypstHeading)

    def test_render_ir_has_chinese_title(self, wind_frequency_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() includes Chinese title."""
        subsection = WindFrequencySubsection(atoms=wind_frequency_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert "风速频率分析" in section_node.heading.text

    def test_render_ir_has_heading_nodes(self, wind_frequency_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() includes TypstHeading nodes."""
        subsection = WindFrequencySubsection(atoms=wind_frequency_collection)
        section_node = subsection.render_ir(tmp_path)

        assert isinstance(section_node.heading, TypstHeading)


class TestTurbulenceSubsection:
    """Tests for TurbulenceSubsection."""

    def test_render_ir_produces_nodes(self, turbulence_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() produces valid IR nodes."""
        subsection = TurbulenceSubsection(atoms=turbulence_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert isinstance(section_node, TypstSection)
        assert isinstance(section_node.heading, TypstHeading)

    def test_render_ir_has_chinese_title(self, turbulence_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() includes Chinese title."""
        subsection = TurbulenceSubsection(atoms=turbulence_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert "湍流强度分析" in section_node.heading.text

    def test_render_ir_has_figure_nodes(self, turbulence_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() includes TypstFigure nodes."""
        subsection = TurbulenceSubsection(atoms=turbulence_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert any(isinstance(n, TypstFigure) for n in section_node.body)

    def test_render_ir_has_table_nodes(self, turbulence_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() includes TypstTable nodes."""
        subsection = TurbulenceSubsection(atoms=turbulence_collection)
        section_node = subsection.render_ir(tmp_path)

        assert any(isinstance(n, TypstTable) for n in section_node.body)


class TestVerticalProfileSubsection:
    """Tests for VerticalProfileSubsection."""

    def test_render_ir_produces_nodes(self, vertical_profile_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() produces valid IR nodes."""
        subsection = VerticalProfileSubsection(atoms=vertical_profile_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert isinstance(section_node, TypstSection)
        assert isinstance(section_node.heading, TypstHeading)

    def test_render_ir_has_chinese_title(self, vertical_profile_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() includes Chinese title."""
        subsection = VerticalProfileSubsection(atoms=vertical_profile_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert "垂直风廓线" in section_node.heading.text

    def test_render_ir_has_table_nodes(self, vertical_profile_collection: AtomCollection, tmp_path: Path) -> None:
        """Test render_ir() includes TypstTable nodes."""
        subsection = VerticalProfileSubsection(atoms=vertical_profile_collection)
        section_node = subsection.render_ir(tmp_path)
        
        assert any(isinstance(n, TypstTable) for n in section_node.body)


# =============================================================================
# Tests - Config Toggles
# =============================================================================


class TestConfigToggles:
    """Tests for report config subsection toggles."""

    def test_subsection_config_defaults(self) -> None:
        """Test ReportSubsectionConfig defaults all enabled."""
        config = ReportSubsectionConfig()
        
        assert config.windrose is True
        assert config.windtemporal is True
        assert config.weibull is True
        assert config.windfrequency is True
        assert config.turbulence is True
        assert config.verticalprofile is True

    def test_subsection_config_can_disable(self) -> None:
        """Test ReportSubsectionConfig can disable subsections."""
        config = ReportSubsectionConfig(
            windrose=False,
            weibull=False,
            turbulence=False,
        )
        
        assert config.windrose is False
        assert config.windtemporal is True  # Still enabled
        assert config.weibull is False
        assert config.windfrequency is True  # Still enabled
        assert config.turbulence is False
        assert config.verticalprofile is True  # Still enabled

    def test_subsection_config_all_disabled(self) -> None:
        """Test ReportSubsectionConfig with all disabled."""
        config = ReportSubsectionConfig(
            windrose=False,
            windtemporal=False,
            weibull=False,
            windfrequency=False,
            turbulence=False,
            verticalprofile=False,
        )
        
        assert config.windrose is False
        assert config.windtemporal is False
        assert config.weibull is False
        assert config.windfrequency is False
        assert config.turbulence is False
        assert config.verticalprofile is False


# =============================================================================
# Tests - Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_collection_wind_rose(self, tmp_path: Path) -> None:
        """Test WindRoseSubsection with empty collection."""
        empty_collection = AtomCollection.from_dict({})
        subsection = WindRoseSection(atoms=empty_collection)
        section_node = subsection.render_ir(tmp_path)
        
        # Should still produce heading
        assert isinstance(section_node.heading, TypstHeading)
        assert "风向风能分布" in section_node.heading.text

    def test_empty_collection_wind_temporal(self, tmp_path: Path) -> None:
        """Test WindTemporalSubsection with empty collection."""
        empty_collection = AtomCollection.from_dict({})
        subsection = WindTemporalSubsection(atoms=empty_collection)
        section_node = subsection.render_ir(tmp_path)
        
        # Should still produce heading
        assert isinstance(section_node.heading, TypstHeading)
        assert "风速时序分析" in section_node.heading.text

    def test_empty_collection_weibull(self, tmp_path: Path) -> None:
        """Test WeibullSubsection with empty collection."""
        empty_collection = AtomCollection.from_dict({})
        subsection = WeibullSubsection(atoms=empty_collection)
        section_node = subsection.render_ir(tmp_path)
        
        # Should still produce heading
        assert isinstance(section_node.heading, TypstHeading)
        assert "Weibull分布拟合" in section_node.heading.text

    def test_empty_collection_wind_frequency(self, tmp_path: Path) -> None:
        """Test WindFrequencySubsection with empty collection."""
        empty_collection = AtomCollection.from_dict({})
        subsection = WindFrequencySubsection(atoms=empty_collection)
        section_node = subsection.render_ir(tmp_path)
        
        # Should still produce heading
        assert isinstance(section_node.heading, TypstHeading)
        assert "风速频率分析" in section_node.heading.text

    def test_empty_collection_turbulence(self, tmp_path: Path) -> None:
        """Test TurbulenceSubsection with empty collection."""
        empty_collection = AtomCollection.from_dict({})
        subsection = TurbulenceSubsection(atoms=empty_collection)
        section_node = subsection.render_ir(tmp_path)
        
        # Should still produce heading
        assert isinstance(section_node.heading, TypstHeading)
        assert "湍流强度分析" in section_node.heading.text

    def test_empty_collection_vertical_profile(self, tmp_path: Path) -> None:
        """Test VerticalProfileSubsection with empty collection."""
        empty_collection = AtomCollection.from_dict({})
        subsection = VerticalProfileSubsection(atoms=empty_collection)
        section_node = subsection.render_ir(tmp_path)
        
        # Should still produce heading
        assert isinstance(section_node.heading, TypstHeading)
        assert "垂直风廓线" in section_node.heading.text

    def test_multiple_masts(self, sample_wind_rose_df: pl.DataFrame, tmp_path: Path) -> None:
        """Test subsection with multiple masts."""
        meta1 = SingleMastMeta(mast_name="M01")
        meta2 = SingleMastMeta(mast_name="M02")
        
        atom1 = SingleMastMonthlyWindFrequencyRoseAtom.create(
            schema=WindRoseSchema,
            df=sample_wind_rose_df,
            meta=meta1,
        )
        atom2 = SingleMastMonthlyWindFrequencyRoseAtom.create(
            schema=WindRoseSchema,
            df=sample_wind_rose_df,
            meta=meta2,
        )
        
        collection = AtomCollection.from_dict({
            "M01": [atom1],
            "M02": [atom2],
        })
        
        subsection = WindRoseSection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        
        # Check that nodes contain text with both mast names
        all_text = section_node.heading.text + " " + " ".join(str(n) for n in section_node.body)
        assert "M01" in all_text
        assert "M02" in all_text


# =============================================================================
# Tests - Integration
# =============================================================================


class TestIntegration:
    """Integration tests for all subsections together."""

    def test_all_subsections_render_ir(
        self,
        wind_rose_collection: AtomCollection,
        wind_temporal_collection: AtomCollection,
        weibull_collection: AtomCollection,
        wind_frequency_collection: AtomCollection,
        turbulence_collection: AtomCollection,
        vertical_profile_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        """Test all 6 subsections can render_ir without errors."""
        subsections = [
            ("WindRose", WindRoseSection(wind_rose_collection)),
            ("WindTemporal", WindTemporalSubsection(wind_temporal_collection)),
            ("Weibull", WeibullSubsection(weibull_collection)),
            ("WindFrequency", WindFrequencySubsection(wind_frequency_collection)),
            ("Turbulence", TurbulenceSubsection(turbulence_collection)),
            ("VerticalProfile", VerticalProfileSubsection(vertical_profile_collection)),
        ]
        
        for name, subsection in subsections:
            section_node = subsection.render_ir(tmp_path)
            assert isinstance(section_node, TypstSection), f"{name} should return TypstSection"
            assert isinstance(section_node.heading, TypstHeading), f"{name} should produce a heading"

    def test_all_subsections_have_chinese_titles(
        self,
        wind_rose_collection: AtomCollection,
        wind_temporal_collection: AtomCollection,
        weibull_collection: AtomCollection,
        wind_frequency_collection: AtomCollection,
        turbulence_collection: AtomCollection,
        vertical_profile_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        """Test all subsections have Chinese titles in IR nodes."""
        subsections = [
            (WindRoseSection(wind_rose_collection), "风向风能分布"),
            (WindTemporalSubsection(wind_temporal_collection), "风速时序分析"),
            (WeibullSubsection(weibull_collection), "Weibull分布拟合"),
            (WindFrequencySubsection(wind_frequency_collection), "风速频率分析"),
            (TurbulenceSubsection(turbulence_collection), "湍流强度分析"),
            (VerticalProfileSubsection(vertical_profile_collection), "垂直风廓线"),
        ]
        
        for subsection, expected_title in subsections:
            section_node = subsection.render_ir(tmp_path)
            assert expected_title in section_node.heading.text, f"Should contain '{expected_title}'"

    def test_all_subsections_produce_ir_nodes(
        self,
        wind_rose_collection: AtomCollection,
        wind_temporal_collection: AtomCollection,
        weibull_collection: AtomCollection,
        wind_frequency_collection: AtomCollection,
        turbulence_collection: AtomCollection,
        vertical_profile_collection: AtomCollection,
        tmp_path: Path,
    ) -> None:
        """Test all subsections produce valid IR nodes."""
        subsections = [
            WindRoseSection(wind_rose_collection),
            WindTemporalSubsection(wind_temporal_collection),
            WeibullSubsection(weibull_collection),
            WindFrequencySubsection(wind_frequency_collection),
            TurbulenceSubsection(turbulence_collection),
            VerticalProfileSubsection(vertical_profile_collection),
        ]
        
        for subsection in subsections:
            section_node = subsection.render_ir(tmp_path)
            combined = [section_node.heading] + list(section_node.body)
            # Should have at least heading
            assert any(isinstance(n, TypstHeading) for n in combined), "Should contain TypstHeading nodes"
            # All items should be valid IR node types
            valid_types = (TypstHeading, TypstParagraph, TypstTable, TypstFigure)
            assert all(isinstance(n, valid_types) for n in combined), "All nodes should be valid IR types"
