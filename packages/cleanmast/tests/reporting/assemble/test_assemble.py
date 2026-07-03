"""Tests for reporting assembly layer."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from cleanmast.subdomains.configuration import (
    DatasetConfig,
    FlatReportConfig,
    FlatSubsectionConfig,
)
from cleanmast.subdomains.reporting.assemble import (
    SECTION_REGISTRY,
    AssembledSectionNode,
    SectionNode,
    assemble_section_tree,
    build_section_tree,
    flatten_tree,
)
from cleanmast.subdomains.reporting.subdomains.air_density import AirDensitySection
from cleanmast.subdomains.reporting.subdomains.wind_rose import WindRoseSection
from typst_ir import TypstHeading, TypstSection


@dataclass(frozen=True)
class FakeSection:
    title: str = "fake"
    atoms: Sequence = field(default_factory=list)

    def render_ir(self, images_dir: Path) -> TypstSection:
        return TypstSection(
            heading=TypstHeading(text="fake"),
            body=[],
            subsections=[],
        )


class TestTreeBuilder:
    """Tests for SectionNode and build_section_tree."""

    def test_empty_input_returns_empty_list(self):
        result = build_section_tree([])
        assert result == []

    def test_single_subsection_no_nesting(self):
        subsections = [
            FlatSubsectionConfig(index="1", type="wind_rose", datasets=["ds"]),
        ]
        result = build_section_tree(subsections)
        assert len(result) == 1
        assert result[0].index == "1"
        assert result[0].type == "wind_rose"
        assert result[0].children == ()

    def test_auto_creates_placeholder_parent(self):
        subsections = [
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["ds"]),
        ]
        result = build_section_tree(subsections)
        assert len(result) == 2
        assert result[0].index == "1"
        assert result[0].is_placeholder is True
        root = result[1]
        assert root.index == "2"
        assert root.is_placeholder is True
        assert len(root.children) == 4
        placeholder = root.children[3]
        assert placeholder.index == "2.4"
        assert placeholder.is_placeholder is True
        assert len(placeholder.children) == 1
        assert placeholder.children[0].index == "2.4.1"
        assert placeholder.children[0].is_placeholder is False

    def test_section_node_is_frozen(self):
        node = SectionNode(index="1", type="wind_rose")
        assert node.__dataclass_params__.frozen is True

    def test_children_are_tuple(self):
        subsections = [
            FlatSubsectionConfig(index="1", type="wind_rose", datasets=["ds"]),
        ]
        result = build_section_tree(subsections)
        assert isinstance(result[0].children, tuple)

    def test_flatten_tree_roundtrip(self):
        subsections = [
            FlatSubsectionConfig(index="2.4", type="timeseries", datasets=["ds"]),
            FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["ds"]),
            FlatSubsectionConfig(
                index="2.4.2", type="temporal", title="Monthly", datasets=["ds"]
            ),
        ]
        tree = build_section_tree(subsections)
        flat = flatten_tree(tree)

        assert len(flat) == 3
        indices = [s.index for s in flat]
        assert indices == ["2.4", "2.4.1", "2.4.2"]


class TestSectionAssembler:
    """Tests for section_assembler."""

    def test_registry_contains_nine_capabilities(self):
        capability_types = {
            "air_density",
            "wind_rose",
            "wind_frequency",
            "weibull",
            "turbulence",
            "temporal",
            "vertical_profile",
            "representative_year_calibration",
            "extreme_wind",
        }
        for stype in capability_types:
            assert stype in SECTION_REGISTRY
            section_cls = SECTION_REGISTRY[stype]
            assert callable(getattr(section_cls, "from_time_series", None)) or callable(
                getattr(section_cls, "from_inputs", None)
            ) or callable(getattr(section_cls, "_from_computed_results", None)) or callable(
                getattr(section_cls, "from_mast_data", None)
            )

    def test_registry_maps_wind_rose_and_air_density(self):
        assert SECTION_REGISTRY["wind_rose"] is WindRoseSection
        assert SECTION_REGISTRY["air_density"] is AirDensitySection

    def test_assemble_section_tree_with_placeholders(self):
        config = FlatReportConfig(
            datasets=[DatasetConfig(name="ds")],
            subsections=[
                FlatSubsectionConfig(index="2.4.1", type="wind_rose", datasets=["ds"]),
            ],
        )
        tree = assemble_section_tree(config, {})
        assert len(tree) == 2
        assert tree[0].index == "1"
        assert tree[0].section is None
        root = tree[1]
        assert root.index == "2"
        assert root.section is None
        placeholder = root.children[3]
        assert placeholder.index == "2.4"
        assert placeholder.section is None
        leaf = placeholder.children[0]
        assert leaf.index == "2.4.1"
        assert leaf.section is None

    def test_assemble_section_tree_maps_sections(self):
        config = FlatReportConfig(
            datasets=[DatasetConfig(name="ds")],
            subsections=[
                FlatSubsectionConfig(index="1", type="wind_rose", datasets=["ds"]),
            ],
        )
        fake_section = FakeSection()
        tree = assemble_section_tree(config, {"1": fake_section})
        assert len(tree) == 1
        assert tree[0].section is fake_section
        assert isinstance(tree[0], AssembledSectionNode)
