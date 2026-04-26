"""Tests for core enriched types."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError
from typst_ir.enriched.types import (
    BaseMeta,
    DepthMeta,
    EnrichedSectionF,
    EnrichedSectionFFix,
)
from typst_ir.nodes import TypstHeading


def test_enriched_section_f_instantiation() -> None:
    """EnrichedSectionF instantiates with various Meta, B, A types."""
    heading = TypstHeading(text="Hello")

    layer = EnrichedSectionF(
        meta=DepthMeta(depth=1),
        heading=heading,
        body=["paragraph"],
        subsections=[42],
    )
    assert layer.meta.depth == 1
    assert layer.body == ["paragraph"]
    assert layer.subsections == [42]

    layer2 = EnrichedSectionF(
        meta=BaseMeta(node_id="a", path="b", depth=2, section_idx=0),
        heading=heading,
        body=[(1, 2)],
        subsections=["sub"],
    )
    assert layer2.meta.node_id == "a"
    assert layer2.body == [(1, 2)]
    assert layer2.subsections == ["sub"]

    layer3 = EnrichedSectionF(
        meta={"key": "value"},
        heading=heading,
        body=[1, 2, 3],
        subsections=["a", "b"],
    )
    assert layer3.meta == {"key": "value"}
    assert layer3.body == [1, 2, 3]
    assert layer3.subsections == ["a", "b"]


def test_enriched_section_f_immutability() -> None:
    """Frozen Pydantic model rejects mutation attempts."""
    layer = EnrichedSectionF(
        meta=DepthMeta(depth=1),
        heading=TypstHeading(text="Hello"),
        body=[],
        subsections=[],
    )
    with pytest.raises(ValidationError):
        layer.meta = DepthMeta(depth=2)


def test_enriched_section_f_fix_recursive_two_levels() -> None:
    """EnrichedSectionFFix builds a parent -> child -> grandchild tree."""
    grandchild = EnrichedSectionFFix(
        unfix=EnrichedSectionF(
            meta=DepthMeta(depth=3),
            heading=TypstHeading(text="Grandchild"),
            body=["gc-body"],
            subsections=[],
        )
    )

    child = EnrichedSectionFFix(
        unfix=EnrichedSectionF(
            meta=DepthMeta(depth=2),
            heading=TypstHeading(text="Child"),
            body=["c-body"],
            subsections=[grandchild],
        )
    )

    parent = EnrichedSectionFFix(
        unfix=EnrichedSectionF(
            meta=DepthMeta(depth=1),
            heading=TypstHeading(text="Parent"),
            body=["p-body"],
            subsections=[child],
        )
    )

    assert parent.unfix.meta.depth == 1
    assert parent.unfix.heading.text == "Parent"
    assert parent.unfix.body == ["p-body"]

    child_layer = parent.unfix.subsections[0]
    assert child_layer.unfix.meta.depth == 2
    assert child_layer.unfix.heading.text == "Child"
    assert child_layer.unfix.body == ["c-body"]

    gc_layer = child_layer.unfix.subsections[0]
    assert gc_layer.unfix.meta.depth == 3
    assert gc_layer.unfix.heading.text == "Grandchild"
    assert gc_layer.unfix.body == ["gc-body"]
    assert gc_layer.unfix.subsections == []


def test_enriched_section_f_fix_immutability() -> None:
    """Frozen fixed-point model rejects mutation attempts."""
    fix = EnrichedSectionFFix(
        unfix=EnrichedSectionF(
            meta=DepthMeta(depth=1),
            heading=TypstHeading(text="Hello"),
            body=[],
            subsections=[],
        )
    )
    with pytest.raises(ValidationError):
        fix.unfix = EnrichedSectionF(
            meta=DepthMeta(depth=2),
            heading=TypstHeading(text="World"),
            body=[],
            subsections=[],
        )


def test_depth_meta_creation_and_immutability() -> None:
    """DepthMeta can be created and is frozen."""
    meta = DepthMeta(depth=5)
    assert meta.depth == 5

    with pytest.raises(FrozenInstanceError):
        meta.depth = 10  # type: ignore


def test_base_meta_creation_and_immutability() -> None:
    """BaseMeta can be created and is frozen."""
    meta = BaseMeta(node_id="n1", path="doc.children.0", depth=2, section_idx=1)
    assert meta.node_id == "n1"
    assert meta.path == "doc.children.0"
    assert meta.depth == 2
    assert meta.section_idx == 1

    with pytest.raises(FrozenInstanceError):
        meta.depth = 99  # type: ignore
