"""Tests for cata_enriched catamorphism."""

from __future__ import annotations

from typst_ir.enriched import (
    DepthMeta,
    EnrichedSectionF,
    EnrichedSectionFFix,
    cata_enriched,
)
from typst_ir.nodes import TypstHeading


def _make_tree() -> EnrichedSectionFFix[DepthMeta, str]:
    """Build a three-level tree for testing.

    Structure:
        Parent (depth=1)
        └── Child (depth=2)
            └── Grandchild (depth=3)
    """
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

    return parent


def test_count_algebra() -> None:
    """Count algebra returns total number of nodes in the tree."""

    def count_algebra(layer: EnrichedSectionF[DepthMeta, str, int]) -> int:
        return 1 + sum(layer.subsections)

    tree = _make_tree()
    result = cata_enriched(tree, count_algebra)
    assert result == 3


def test_collect_depths_algebra() -> None:
    """Collect-depth algebra returns all depths in the tree."""

    def collect_depths(
        layer: EnrichedSectionF[DepthMeta, str, list[int]],
    ) -> list[int]:
        depths = [layer.meta.depth]
        for sub_depths in layer.subsections:
            depths.extend(sub_depths)
        return depths

    tree = _make_tree()
    result = cata_enriched(tree, collect_depths)
    assert result == [1, 2, 3]


def test_count_algebra_single_node() -> None:
    """Count algebra on a single-node tree returns 1."""

    def count_algebra(layer: EnrichedSectionF[DepthMeta, str, int]) -> int:
        return 1 + sum(layer.subsections)

    tree = EnrichedSectionFFix(
        unfix=EnrichedSectionF(
            meta=DepthMeta(depth=1),
            heading=TypstHeading(text="Root"),
            body=["body"],
            subsections=[],
        )
    )
    result = cata_enriched(tree, count_algebra)
    assert result == 1


def test_collect_depths_algebra_empty_tree() -> None:
    """Collect-depth algebra on a single-node tree returns its depth."""

    def collect_depths(
        layer: EnrichedSectionF[DepthMeta, str, list[int]],
    ) -> list[int]:
        depths = [layer.meta.depth]
        for sub_depths in layer.subsections:
            depths.extend(sub_depths)
        return depths

    tree = EnrichedSectionFFix(
        unfix=EnrichedSectionF(
            meta=DepthMeta(depth=5),
            heading=TypstHeading(text="Lonely"),
            body=[],
            subsections=[],
        )
    )
    result = cata_enriched(tree, collect_depths)
    assert result == [5]
