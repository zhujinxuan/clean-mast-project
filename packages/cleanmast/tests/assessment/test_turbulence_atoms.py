"""Tests for turbulence report atoms."""

from pathlib import Path

import polars as pl
import pytest
from cleanmast.subdomains.assessment.domain.entities.single_mast.turbulence_intensity import (
    SingleMastTurbulenceIntensityAtom,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.report_meta import (
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.domain.value_objects.single_mast.schemas import (
    TurbulenceSchema,
)


@pytest.fixture
def sample_mast_meta() -> SingleMastMeta:
    return SingleMastMeta(mast_name="M01")


@pytest.fixture
def sample_turbulence_df() -> pl.DataFrame:
    return pl.DataFrame({
        "wind_speed_bin": [3, 5, 7, 9, 11, 13],
        "height": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
        "interpolation_marker": [None, None, None, None, None, None],
        "mean_ti": [0.18, 0.15, 0.12, 0.10, 0.09, 0.08],
        "std_ti": [0.03, 0.02, 0.02, 0.015, 0.01, 0.01],
        "representative_ti": [0.218, 0.176, 0.146, 0.119, 0.103, 0.093],
        "iec_category": ["B", "B", "A", "A", "A", "A"],
    })


@pytest.fixture
def turbulence_intensity_atom(
    sample_turbulence_df: pl.DataFrame,
    sample_mast_meta: SingleMastMeta,
) -> SingleMastTurbulenceIntensityAtom:
    return SingleMastTurbulenceIntensityAtom.create(
        schema=TurbulenceSchema,
        df=sample_turbulence_df,
        meta=sample_mast_meta,
    )


class TestSingleMastTurbulenceIntensityAtom:
    def test_render_image(
        self, turbulence_intensity_atom: SingleMastTurbulenceIntensityAtom, tmp_path: Path
    ) -> None:
        image_path = turbulence_intensity_atom.renderImage(tmp_path)
        
        assert image_path.exists()
        assert image_path.suffix == ".png"
        assert image_path.stat().st_size > 0

    def test_render_table(self, turbulence_intensity_atom: SingleMastTurbulenceIntensityAtom) -> None:
        table = turbulence_intensity_atom.renderTable()
        
        assert isinstance(table, str)
        assert len(table) > 0
        assert "#table(" in table
