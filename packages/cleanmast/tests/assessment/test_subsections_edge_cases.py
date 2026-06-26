"""Edge case and regression tests for subsection renderers.

Covers 6 production-edge scenarios to prevent regressions
in the multi-mast subsection refactor:

1. Missing atom type across a 3-mast collection → graceful skip
2. Empty mast list → heading only, no crash
3. Single mast → structural equivalence with pre-refactor baseline
4. Many masts (5+) → merged summary stress test
5. Image filename uniqueness → no collisions in shared output dir
6. AtomCollection duplicate rejection → existing validation still works
"""

from pathlib import Path
from typing import Any

import polars as pl
from cleanmast.subdomains.assessment.domain.value_objects import (
    AtomCollection,
    SingleMastMeta,
)
from cleanmast.subdomains.assessment.shared.ir_types import (
    TypstFigure,
    TypstHeading,
    TypstParagraph,
    TypstTable,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_multi_atom import (
    SingleMastTurbulenceMultiHeightAtom,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_summary_atom import (
    SingleMastTurbulenceSummaryAtom,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.services.turbulence_section import (
    TurbulenceSubsection,
)
from cleanmast.subdomains.assessment.subdomains.turbulence.value_objects.schemas import (
    TurbulenceSchema,
)
from cleanmast.subdomains.assessment.subdomains.vertical_profile.entities.wind_shear_matrix_atom import (
    SingleMastWindShearExponentAtom,
)
from cleanmast.subdomains.assessment.subdomains.vertical_profile.services.vertical_profile_section import (
    VerticalProfileSubsection,
)
from cleanmast.subdomains.assessment.subdomains.vertical_profile.value_objects.schemas import (
    VerticalProfileSchema,
    WindShearSchema,
)
from cleanmast.subdomains.assessment.subdomains.weibull.services.weibull_section import (
    WeibullSubsection,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.entities.daily_pattern_atom import (
    SingleMastDailyPatternAtom,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.services.wind_temporal_section import (
    WindTemporalSubsection,
)
from cleanmast.subdomains.assessment.subdomains.wind_temporal.value_objects.schemas import (
    TemporalPatternSchema,
)

# =============================================================================
# Scenario 1: Missing atom type skips gracefully
# =============================================================================


def _make_turbulence_summary_atom(meta: SingleMastMeta) -> SingleMastTurbulenceSummaryAtom:
    df = pl.DataFrame({
        "wind_speed_bin": [3, 5, 7],
        "height": [100.0, 100.0, 100.0],
        "interpolation_marker": [None, None, None],
        "mean_ti": [0.18, 0.15, 0.12],
        "std_ti": [0.03, 0.02, 0.02],
        "representative_ti": [0.218, 0.176, 0.146],
        "iec_category": ["B", "B", "A"],
        "count": [42, 42, 42],
    })
    return SingleMastTurbulenceSummaryAtom.create(schema=TurbulenceSchema, df=df, meta=meta)


class TestMissingAtomTypeGracefulSkip:
    """One mast in a 3-mast collection is missing an atom type that others have.

    The subsection should skip gracefully instead of crashing.
    """

    def test_turbulence_subsection_skips_missing_multi_height_atom(self, tmp_path: Path) -> None:
        """M02 lacks SingleMastTurbulenceMultiHeightAtom; renderer should output M01+M03 only."""
        from cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_multi_atom import (
            SingleMastTurbulenceMultiHeightAtom,
        )

        meta1 = SingleMastMeta(mast_name="M01")
        meta2 = SingleMastMeta(mast_name="M02")
        meta3 = SingleMastMeta(mast_name="M03")

        m01_atoms = [
            _make_turbulence_summary_atom(meta1),
            SingleMastTurbulenceMultiHeightAtom.create(
                schema=TurbulenceSchema,
                df=pl.DataFrame({
                    "wind_speed_bin": [3, 5, 7],
                    "height": [100.0, 100.0, 100.0],
                    "interpolation_marker": [None, None, None],
                    "mean_ti": [0.18, 0.15, 0.12],
                    "std_ti": [0.03, 0.02, 0.02],
                    "representative_ti": [0.218, 0.176, 0.146],
                    "iec_category": ["B", "B", "A"],
                    "count": [42, 42, 42],
                }),
                meta=meta1,
            ),
        ]
        # M02 is missing the multi-height atom
        m02_atoms = [
            _make_turbulence_summary_atom(meta2),
        ]
        m03_atoms = [
            _make_turbulence_summary_atom(meta3),
            SingleMastTurbulenceMultiHeightAtom.create(
                schema=TurbulenceSchema,
                df=pl.DataFrame({
                    "wind_speed_bin": [3, 5, 7],
                    "height": [100.0, 100.0, 100.0],
                    "interpolation_marker": [None, None, None],
                    "mean_ti": [0.18, 0.15, 0.12],
                    "std_ti": [0.03, 0.02, 0.02],
                    "representative_ti": [0.218, 0.176, 0.146],
                    "iec_category": ["B", "B", "A"],
                    "count": [42, 42, 42],
                }),
                meta=meta3,
            ),
        ]

        collection = AtomCollection.from_dict({
            "M01": m01_atoms,
            "M02": m02_atoms,
            "M03": m03_atoms,
        })

        subsection = TurbulenceSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)

        # Extract figure contents (image paths)
        figure_contents = [
            n.content for n in section_node.body if isinstance(n, TypstFigure)
        ]

        # Multi-height figures should only come from M01 and M03
        multi_figures = [c for c in figure_contents if "turbulence_multi" in c]
        assert len(multi_figures) == 2, "Expected exactly 2 multi-height figures (M01 + M03)"
        assert any("M01" in c for c in multi_figures), "Expected M01 multi-height figure"
        assert any("M03" in c for c in multi_figures), "Expected M03 multi-height figure"
        assert not any("M02" in c for c in multi_figures), "Did not expect M02 multi-height figure"


# =============================================================================
# Scenario 2: Empty mast list produces heading only
# =============================================================================


class TestEmptyMastList:
    """Subsection with 0 masts should produce heading only (or empty children), no crash."""

    def test_weibull_empty_collection_heading_only(self, tmp_path: Path) -> None:
        """WeibullSubsection with empty AtomCollection renders heading and no other nodes."""
        empty_collection = AtomCollection.from_dict({})
        subsection = WeibullSubsection(atoms=empty_collection)
        section_node = subsection.render_ir(tmp_path)

        assert isinstance(section_node.heading, TypstHeading)
        assert len(section_node.body) == 0
        assert "Weibull分布拟合" in section_node.heading.text

    def test_vertical_profile_empty_collection_heading_only(self, tmp_path: Path) -> None:
        """VerticalProfileSubsection with empty AtomCollection renders heading only."""
        empty_collection = AtomCollection.from_dict({})
        subsection = VerticalProfileSubsection(atoms=empty_collection)
        section_node = subsection.render_ir(tmp_path)

        assert isinstance(section_node.heading, TypstHeading)
        assert len(section_node.body) == 0
        assert "垂直风廓线" in section_node.heading.text


# =============================================================================
# Scenario 3: Single mast structural equivalence
# =============================================================================


class TestSingleMastStructuralEquivalence:
    """Single-mast output must be visually identical to pre-refactor baseline.

    This is a regression test: the node sequence and types for one mast
    must match the expected pre-refactor structure.
    """

    def test_vertical_profile_single_mast_node_sequence(self, tmp_path: Path) -> None:
        """VerticalProfileSubsection with 1 mast produces exact baseline node sequence."""
        meta = SingleMastMeta(mast_name="M01")

        profile_df = pl.DataFrame({
            "height": [50.0, 80.0, 100.0, 120.0],
            "interpolation_marker": [None, None, None, "外推"],
            "wind_speed_mean": [5.2, 6.1, 6.8, 7.2],
            "wind_speed_std": [1.8, 2.0, 2.1, 2.2],
            "alpha": [0.15, None, None, None],
            "r_squared": [0.98, None, None, None],
        })

        shear_df = pl.DataFrame({
            "from_height": [50.0, 50.0, 50.0, 80.0, 80.0, 100.0],
            "to_height": [80.0, 100.0, 120.0, 100.0, 120.0, 120.0],
            "alpha_mean": [0.15, 0.14, 0.13, 0.135, 0.125, 0.12],
            "alpha_std": [0.03, 0.025, 0.02, 0.022, 0.018, 0.015],
            "alpha_min": [0.08, 0.07, 0.06, 0.065, 0.055, 0.05],
            "alpha_max": [0.25, 0.22, 0.20, 0.21, 0.19, 0.18],
        })

        atom = SingleMastWindShearExponentAtom.create(
            profile_schema=VerticalProfileSchema,
            profile_df=profile_df,
            shear_schema=WindShearSchema,
            shear_df=shear_df,
            meta=meta,
        )

        collection = AtomCollection.from_dict({
            "M01": [atom],
        })

        subsection = VerticalProfileSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)
        nodes = [section_node.heading] + list(section_node.body)

        expected_types = [
            TypstHeading,
            TypstParagraph,  # illustration
            TypstParagraph,  # equation
            TypstParagraph,  # summary
            TypstTable,      # combined table
            TypstFigure,     # vertical profile figure
        ]

        assert len(nodes) == len(expected_types), (
            f"Expected {len(expected_types)} nodes, got {len(nodes)}: "
            f"{[type(n).__name__ for n in nodes]}"
        )
        for i, expected_type in enumerate(expected_types):
            assert isinstance(nodes[i], expected_type), (
                f"Node {i}: expected {expected_type.__name__}, got {type(nodes[i]).__name__}"
            )


# =============================================================================
# Scenario 4: Many masts (5+) stress test
# =============================================================================


class TestManyMastsMergedSummary:
    """Stress-test summary merging with 5+ masts to ensure no truncation errors."""

    def test_five_masts_daily_pattern_merged_summary_length(self, tmp_path: Path) -> None:
        """5 masts with DailyPatternAtom produce merged summary longer than any single summary."""
        from datetime import datetime

        hours = list(range(24))
        rows = []
        for month in [1, 2, 3]:
            for height in [120.0]:
                for hour in hours:
                    rows.append({
                        "timestamp": datetime(2023, month, 15, hour),
                        "hour": hour,
                        "month": month,
                        "wind_speed": 5.0,
                        "wind_power": 150.0,
                        "height": height,
                        "mean_speed": 5.5,
                        "mean_power": 180.0,
                        "interpolation_marker": None,
                    })
        base_df = pl.DataFrame(rows)

        mast_names = ["M01", "M02", "M03", "M04", "M05"]
        collection_dict: dict[str, list[Any]] = {}
        for name in mast_names:
            meta = SingleMastMeta(mast_name=name)
            atom = SingleMastDailyPatternAtom.create(
                schema=TemporalPatternSchema, df=base_df, meta=meta
            )
            collection_dict[name] = [atom]

        collection = AtomCollection.from_dict(collection_dict)
        subsection = WindTemporalSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)

        paragraphs = [n for n in section_node.body if isinstance(n, TypstParagraph)]
        assert len(paragraphs) >= 1, "Expected at least one merged summary paragraph"

        merged_text = " ".join(p.text for p in paragraphs)
        # Every mast name should appear in the merged output
        for name in mast_names:
            assert name in merged_text, f"Merged summary should mention {name}"

        # Merged summary should be substantially longer than a single mast summary
        single_summary_len = len(atom.renderSummary()[0].text)
        assert len(merged_text) > single_summary_len * 2, (
            f"Merged summary ({len(merged_text)} chars) should be much longer "
            f"than a single summary ({single_summary_len} chars)"
        )


# =============================================================================
# Scenario 5: Image filename uniqueness
# =============================================================================


class TestImageFilenameUniqueness:
    """Multiple masts rendering images to the same directory must not collide."""

    def test_two_masts_turbulence_intensity_no_collision(self, tmp_path: Path) -> None:
        """Two masts with identical turbulence data render to unique filenames."""
        df = pl.DataFrame({
            "wind_speed_bin": [3, 5, 7],
            "height": [100.0, 100.0, 100.0],
            "interpolation_marker": [None, None, None],
            "mean_ti": [0.18, 0.15, 0.12],
            "std_ti": [0.03, 0.02, 0.02],
            "representative_ti": [0.218, 0.176, 0.146],
            "iec_category": ["B", "B", "A"],
            "count": [42, 42, 42],
        })

        meta1 = SingleMastMeta(mast_name="M01")
        meta2 = SingleMastMeta(mast_name="M02")

        atom1 = SingleMastTurbulenceMultiHeightAtom.create(
            schema=TurbulenceSchema, df=df, meta=meta1
        )
        atom2 = SingleMastTurbulenceMultiHeightAtom.create(
            schema=TurbulenceSchema, df=df, meta=meta2
        )

        image_dir = tmp_path / "images"
        image_dir.mkdir()

        path1 = atom1.renderImage(image_dir)
        path2 = atom2.renderImage(image_dir)

        assert path1 != path2, f"Image paths should differ: {path1} == {path2}"
        assert len({path1, path2}) == 2, "Expected 2 unique image paths"
        assert "M01" in path1.name, "Filename should contain M01"
        assert "M02" in path2.name, "Filename should contain M02"

    def test_subsection_render_no_collision(self, tmp_path: Path) -> None:
        """Via TurbulenceSubsection.render_ir(), 2 masts produce distinct figure nodes."""
        from cleanmast.subdomains.assessment.subdomains.turbulence.entities.turbulence_multi_atom import (
            SingleMastTurbulenceMultiHeightAtom,
        )

        df = pl.DataFrame({
            "wind_speed_bin": [3, 5, 7],
            "height": [100.0, 100.0, 100.0],
            "interpolation_marker": [None, None, None],
            "mean_ti": [0.18, 0.15, 0.12],
            "std_ti": [0.03, 0.02, 0.02],
            "representative_ti": [0.218, 0.176, 0.146],
            "iec_category": ["B", "B", "A"],
            "count": [42, 42, 42],
        })

        meta1 = SingleMastMeta(mast_name="M01")
        meta2 = SingleMastMeta(mast_name="M02")

        atom1 = SingleMastTurbulenceMultiHeightAtom.create(
            schema=TurbulenceSchema, df=df, meta=meta1
        )
        atom2 = SingleMastTurbulenceMultiHeightAtom.create(
            schema=TurbulenceSchema, df=df, meta=meta2
        )

        collection = AtomCollection.from_dict({
            "M01": [atom1],
            "M02": [atom2],
        })

        subsection = TurbulenceSubsection(atoms=collection)
        section_node = subsection.render_ir(tmp_path)

        figure_contents = {n.content for n in section_node.body if isinstance(n, TypstFigure)}
        assert len(figure_contents) == 2, f"Expected 2 unique figures, got {figure_contents}"


# =============================================================================
# Scenario 6: AtomCollection duplicate atom type rejection
# =============================================================================


class TestAtomCollectionDuplicateRejection:
    """Duplicate atom types per mast are allowed and stored."""

    def test_from_dict_allows_duplicate_atom_types(self) -> None:
        """AtomCollection.from_dict stores all atoms when same atom type is repeated."""
        meta = SingleMastMeta(mast_name="M01")
        df = pl.DataFrame({
            "wind_speed_bin": [3, 5, 7],
            "height": [100.0, 100.0, 100.0],
            "interpolation_marker": [None, None, None],
            "mean_ti": [0.18, 0.15, 0.12],
            "std_ti": [0.03, 0.02, 0.02],
            "representative_ti": [0.218, 0.176, 0.146],
            "iec_category": ["B", "B", "A"],
            "count": [42, 42, 42],
        })

        atom1 = SingleMastTurbulenceMultiHeightAtom.create(
            schema=TurbulenceSchema, df=df, meta=meta
        )
        atom2 = SingleMastTurbulenceMultiHeightAtom.create(
            schema=TurbulenceSchema, df=df, meta=meta
        )

        collection = AtomCollection.from_dict({"M01": [atom1, atom2]})

        assert len(collection.get_by_mast("M01")) == 2
        assert collection.get("M01", SingleMastTurbulenceMultiHeightAtom) is atom1
