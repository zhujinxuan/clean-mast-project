"""Tests for enrich_section anamorphism and DepthMeta helpers."""

from __future__ import annotations

from typst_ir.enriched.enrich import (
    depth_for_section,
    enrich_section,
    enrich_with_depth,
    identity_block,
)
from typst_ir.enriched.types import DepthMeta
from typst_ir.nodes import TypstHeading, TypstParagraph, TypstSection


def test_depth_for_section() -> None:
    """depth_for_section increments parent depth by one."""
    section = TypstSection(
        heading=TypstHeading(text="Unused"),
        body=[],
        subsections=[],
    )
    parent = DepthMeta(depth=2)
    result = depth_for_section(section, parent)
    assert result.depth == 3


def test_identity_block() -> None:
    """identity_block returns the block unchanged."""
    block = TypstParagraph(text="Hello")
    meta = DepthMeta(depth=1)
    assert identity_block(block, meta) is block


def test_enrich_section_empty_body_and_subsections() -> None:
    """enrich_section handles empty body and subsections correctly."""
    section = TypstSection(
        heading=TypstHeading(text="Empty Section"),
        body=[],
        subsections=[],
    )
    enriched = enrich_section(
        section,
        DepthMeta(0),
        depth_for_section,
        identity_block,
    )
    assert enriched.unfix.meta.depth == 1
    assert enriched.unfix.heading.text == "Empty Section"
    assert enriched.unfix.body == []
    assert enriched.unfix.subsections == []


def test_enrich_section_depth_propagation_three_levels() -> None:
    """Depth propagates correctly through 3 levels of nesting."""
    level3 = TypstSection(
        heading=TypstHeading(text="Level 3"),
        body=[TypstParagraph(text="l3 body")],
        subsections=[],
    )
    level2 = TypstSection(
        heading=TypstHeading(text="Level 2"),
        body=[TypstParagraph(text="l2 body")],
        subsections=[level3],
    )
    level1 = TypstSection(
        heading=TypstHeading(text="Level 1"),
        body=[TypstParagraph(text="l1 body")],
        subsections=[level2],
    )

    enriched = enrich_section(
        level1,
        DepthMeta(0),
        depth_for_section,
        identity_block,
    )

    # Level 1
    assert enriched.unfix.meta.depth == 1
    assert enriched.unfix.heading.text == "Level 1"
    assert len(enriched.unfix.body) == 1
    assert isinstance(enriched.unfix.body[0], TypstParagraph)
    assert enriched.unfix.body[0].text == "l1 body"

    # Level 2
    assert len(enriched.unfix.subsections) == 1
    e2 = enriched.unfix.subsections[0]
    assert e2.unfix.meta.depth == 2
    assert e2.unfix.heading.text == "Level 2"
    assert len(e2.unfix.body) == 1
    assert e2.unfix.body[0].text == "l2 body"

    # Level 3
    assert len(e2.unfix.subsections) == 1
    e3 = e2.unfix.subsections[0]
    assert e3.unfix.meta.depth == 3
    assert e3.unfix.heading.text == "Level 3"
    assert len(e3.unfix.body) == 1
    assert e3.unfix.body[0].text == "l3 body"
    assert e3.unfix.subsections == []


def test_enrich_with_depth_convenience() -> None:
    """enrich_with_depth uses default helpers starting from depth 0."""
    child = TypstSection(
        heading=TypstHeading(text="Child"),
        body=[],
        subsections=[],
    )
    parent = TypstSection(
        heading=TypstHeading(text="Parent"),
        body=[TypstParagraph(text="para")],
        subsections=[child],
    )

    enriched = enrich_with_depth(parent)
    assert enriched.unfix.meta.depth == 1
    assert enriched.unfix.heading.text == "Parent"
    assert enriched.unfix.body[0].text == "para"

    e_child = enriched.unfix.subsections[0]
    assert e_child.unfix.meta.depth == 2
    assert e_child.unfix.heading.text == "Child"


def test_enrich_section_preserves_body_blocks() -> None:
    """Body blocks are passed through identity_block unchanged."""
    para = TypstParagraph(text="Keep me")
    section = TypstSection(
        heading=TypstHeading(text="Section"),
        body=[para],
        subsections=[],
    )
    enriched = enrich_with_depth(section)
    assert enriched.unfix.body[0] is para
