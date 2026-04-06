"""Tests for vertical profile atoms."""

from pathlib import Path

import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.entities.single_mast.vertical_profile import (
    SingleMastVerticalProfileAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects.schemas import (
    VerticalProfileSchema,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)


@pytest.fixture
def sample_meta() -> SingleMastMeta:
    return SingleMastMeta(
        mast_name="TestMast",
        air_density=1.225,
        caption="Test caption",
    )


@pytest.fixture
def vertical_profile_data() -> pl.DataFrame:
    return pl.DataFrame({
        "height": [100.0, 120.0, 140.0],
        "interpolation_marker": [None, None, None],
        "wind_speed_mean": [8.0, 8.5, 9.0],
        "wind_speed_std": [1.5, 1.6, 1.7],
        "alpha": [0.143, 0.143, 0.143],
        "r_squared": [0.998, 0.998, 0.998],
    })


class TestSingleMastVerticalProfileAtom:
    def test_render_table_basic(
        self, sample_meta: SingleMastMeta, vertical_profile_data: pl.DataFrame
    ) -> None:
        atom = SingleMastVerticalProfileAtom.create(
            schema=VerticalProfileSchema, df=vertical_profile_data,
            meta=sample_meta
        )
        
        table = atom.renderTable()
        
        assert "#table(" in table
        assert "高度" in table
        assert "100m" in table
    
    def test_render_image_basic(
        self,
        sample_meta: SingleMastMeta,
        vertical_profile_data: pl.DataFrame,
        tmp_path: Path,
    ) -> None:
        atom = SingleMastVerticalProfileAtom.create(
            schema=VerticalProfileSchema, df=vertical_profile_data,
            meta=sample_meta
        )
        
        image_path = atom.renderImage(tmp_path)
        
        assert image_path is not None
        assert image_path.suffix == ".png"
        assert image_path.exists()
    
    def test_render_summary_basic(
        self, sample_meta: SingleMastMeta, vertical_profile_data: pl.DataFrame
    ) -> None:
        atom = SingleMastVerticalProfileAtom.create(
            schema=VerticalProfileSchema, df=vertical_profile_data,
            meta=sample_meta
        )
        
        summary = atom.renderSummary()
        
        assert "TestMast" in summary
        assert "测风塔" in summary
