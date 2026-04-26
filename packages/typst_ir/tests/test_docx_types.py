"""Tests for DOCX-specific enriched types."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError
from typst_ir.enriched.docx_types import (
    DocxMeta,
    EnrichedBlock,
    PathMeta,
    path_to_id,
)
from typst_ir.nodes import TypstParagraph


def test_path_meta_creation_and_immutability() -> None:
    """PathMeta can be created and is frozen."""
    meta = PathMeta(depth=2, path=[("section", 0), ("body", 1)])
    assert meta.depth == 2
    assert meta.path == [("section", 0), ("body", 1)]

    with pytest.raises(FrozenInstanceError):
        meta.depth = 99  # type: ignore

    with pytest.raises(FrozenInstanceError):
        meta.path = [("section", 1)]  # type: ignore


def test_docx_meta_creation_and_immutability() -> None:
    """DocxMeta can be created and is frozen."""
    meta = DocxMeta(
        depth=1,
        path=[("section", 0)],
        section_index="1",
        table_index="1-1",
        figure_index=None,
    )
    assert meta.depth == 1
    assert meta.path == [("section", 0)]
    assert meta.section_index == "1"
    assert meta.table_index == "1-1"
    assert meta.figure_index is None

    with pytest.raises(FrozenInstanceError):
        meta.section_index = "2"  # type: ignore


def test_path_to_id_concatenates_correctly() -> None:
    """path_to_id concatenates context and index pairs."""
    path = [("section", 0), ("body", 2), ("table", 0)]
    assert path_to_id(path) == "section0body2table0"


def test_path_to_id_empty_path() -> None:
    """path_to_id returns empty string for empty path."""
    assert path_to_id([]) == ""


def test_enriched_block_instantiation() -> None:
    """EnrichedBlock instantiates with a TypstBodyBlock and DocxMeta."""
    paragraph = TypstParagraph(text="Hello, world!")
    meta = DocxMeta(
        depth=0,
        path=[("body", 0)],
        section_index="1",
    )
    block = EnrichedBlock(block=paragraph, meta=meta)

    assert block.block.text == "Hello, world!"
    assert block.meta.depth == 0
    assert block.meta.section_index == "1"


def test_enriched_block_immutability() -> None:
    """Frozen EnrichedBlock rejects mutation attempts."""
    paragraph = TypstParagraph(text="Hello!")
    meta = DocxMeta(depth=0, path=[("body", 0)], section_index="1")
    block = EnrichedBlock(block=paragraph, meta=meta)

    with pytest.raises(ValidationError):
        block.block = TypstParagraph(text="World!")  # type: ignore

    with pytest.raises(ValidationError):
        block.meta = DocxMeta(depth=1, path=[("body", 1)], section_index="2")  # type: ignore
