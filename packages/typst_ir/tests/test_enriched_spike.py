"""Spike test for Pydantic v2 recursive generic types.

Tests whether EnrichedSectionFFix[DepthMeta, str] can handle self-referential
structures with JSON serialization/deserialization roundtrips.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Inline minimal types for the spike
# ---------------------------------------------------------------------------


class DepthMeta(BaseModel):
    """Minimal metadata type for testing."""

    model_config = ConfigDict(frozen=True)
    depth: int
    label: str | None = None


M = TypeVar("M")
T = TypeVar("T")


class EnrichedSectionFFix(BaseModel, Generic[M, T]):
    """Self-referential generic section for the spike test."""

    model_config = ConfigDict(frozen=True)

    meta: M
    content: list[T]
    subsections: list["EnrichedSectionFFix[M, T]"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRecursiveGenericInstantiation:
    """Verify recursive generic models can be instantiated."""

    def test_level_1_instantiation(self) -> None:
        """A single-level section should instantiate cleanly."""
        section = EnrichedSectionFFix[DepthMeta, str](
            meta=DepthMeta(depth=0, label="root"),
            content=["hello"],
            subsections=[],
        )
        assert section.meta.depth == 0
        assert section.content == ["hello"]
        assert section.subsections == []

    def test_level_3_nesting(self) -> None:
        """A 3-level nested structure should instantiate cleanly."""
        leaf = EnrichedSectionFFix[DepthMeta, str](
            meta=DepthMeta(depth=2, label="leaf"),
            content=["level 2"],
            subsections=[],
        )
        mid = EnrichedSectionFFix[DepthMeta, str](
            meta=DepthMeta(depth=1, label="mid"),
            content=["level 1"],
            subsections=[leaf],
        )
        root = EnrichedSectionFFix[DepthMeta, str](
            meta=DepthMeta(depth=0, label="root"),
            content=["level 0"],
            subsections=[mid],
        )
        assert root.meta.depth == 0
        assert root.subsections[0].meta.depth == 1
        assert root.subsections[0].subsections[0].meta.depth == 2
        assert root.subsections[0].subsections[0].content == ["level 2"]


class TestRecursiveGenericRoundtrip:
    """Verify JSON serialization and deserialization roundtrip."""

    def test_model_dump_json_and_validate(self) -> None:
        """3-level model should roundtrip through JSON."""
        leaf = EnrichedSectionFFix[DepthMeta, str](
            meta=DepthMeta(depth=2, label="leaf"),
            content=["level 2"],
            subsections=[],
        )
        mid = EnrichedSectionFFix[DepthMeta, str](
            meta=DepthMeta(depth=1, label="mid"),
            content=["level 1"],
            subsections=[leaf],
        )
        original = EnrichedSectionFFix[DepthMeta, str](
            meta=DepthMeta(depth=0, label="root"),
            content=["level 0"],
            subsections=[mid],
        )

        json_str = original.model_dump_json()
        restored = EnrichedSectionFFix[DepthMeta, str].model_validate_json(json_str)

        assert restored == original
        assert restored.subsections[0].subsections[0].meta.label == "leaf"

    def test_json_structure_contains_expected_fields(self) -> None:
        """Serialized JSON should contain nested structure."""
        section = EnrichedSectionFFix[DepthMeta, str](
            meta=DepthMeta(depth=0),
            content=["a"],
            subsections=[
                EnrichedSectionFFix[DepthMeta, str](
                    meta=DepthMeta(depth=1),
                    content=["b"],
                    subsections=[],
                ),
            ],
        )
        json_str = section.model_dump_json()
        assert '"meta":{"depth":0' in json_str
        assert '"content":["a"]' in json_str
        assert '"subsections":[' in json_str


# ---------------------------------------------------------------------------
# Fallback spike: frozen dataclass with identical shape
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FrozenDepthMeta:
    """Frozen dataclass version of DepthMeta."""

    depth: int
    label: str | None = None


@dataclass(frozen=True)
class FrozenEnrichedSectionFFix(Generic[M, T]):
    """Frozen dataclass fallback for recursive generic section."""

    meta: M
    content: list[T]
    subsections: list["FrozenEnrichedSectionFFix[M, T]"]


class TestFrozenDataclassFallback:
    """Verify frozen dataclass fallback works for recursive generics."""

    def test_frozen_dataclass_level_3(self) -> None:
        """3-level nesting with frozen dataclasses should work."""
        leaf = FrozenEnrichedSectionFFix[FrozenDepthMeta, str](
            meta=FrozenDepthMeta(depth=2, label="leaf"),
            content=["level 2"],
            subsections=[],
        )
        mid = FrozenEnrichedSectionFFix[FrozenDepthMeta, str](
            meta=FrozenDepthMeta(depth=1, label="mid"),
            content=["level 1"],
            subsections=[leaf],
        )
        root = FrozenEnrichedSectionFFix[FrozenDepthMeta, str](
            meta=FrozenDepthMeta(depth=0, label="root"),
            content=["level 0"],
            subsections=[mid],
        )
        assert root.subsections[0].subsections[0].meta.depth == 2
