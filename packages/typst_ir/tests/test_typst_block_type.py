"""Tests for typst_block_type module.

Covers TypstBlockType construction and build_block_type_map behavior.
"""

from __future__ import annotations

import pytest
from typst_ir.nodes import (
    TypstDocument,
    TypstHeading,
    TypstParagraph,
    TypstSection,
    TypstTable,
)
from typst_ir.typst_block_type import TypstBlockType, build_block_type_map


class TestTypstBlockType:
    def test_construction(self) -> None:
        bt = TypstBlockType(path="section0body2", block_type=TypstParagraph)
        assert bt.path == "section0body2"
        assert bt.block_type == TypstParagraph
        assert bt.heading_level is None
        assert bt.has_caption is False

    def test_with_heading_level(self) -> None:
        bt = TypstBlockType(
            path="section0heading0", block_type=TypstHeading, heading_level=1
        )
        assert bt.heading_level == 1

    def test_with_caption(self) -> None:
        bt = TypstBlockType(
            path="section0body0table0", block_type=TypstTable, has_caption=True
        )
        assert bt.has_caption is True

    def test_is_frozen(self) -> None:
        bt = TypstBlockType(path="section0body2", block_type=TypstParagraph)
        with pytest.raises(AttributeError):
            bt.path = "other"


class TestBuildBlockTypeMap:
    def test_empty_document(self) -> None:
        doc = TypstDocument(children=[])
        result = build_block_type_map(doc)
        assert result == {}

    def test_single_section_with_heading(self) -> None:
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[],
                    subsections=[],
                )
            ]
        )
        result = build_block_type_map(doc)
        assert "section0heading0" in result
        assert result["section0heading0"].block_type == TypstHeading
        assert result["section0heading0"].heading_level == 1

    def test_section_with_paragraph(self) -> None:
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[TypstParagraph(text="Hello")],
                    subsections=[],
                )
            ]
        )
        result = build_block_type_map(doc)
        assert "section0body0" in result
        assert result["section0body0"].block_type == TypstParagraph
        assert result["section0body0"].has_caption is False

    def test_table_with_caption(self) -> None:
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[
                        TypstTable(
                            headers=["A", "B"],
                            data=[["1", "2"]],
                            caption="Table caption",
                        )
                    ],
                    subsections=[],
                )
            ]
        )
        result = build_block_type_map(doc)
        assert "section0body0table0" in result
        assert result["section0body0table0"].block_type == TypstTable
        assert result["section0body0table0"].has_caption is True

    def test_table_without_caption(self) -> None:
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[
                        TypstTable(
                            headers=["A", "B"],
                            data=[["1", "2"]],
                            caption=None,
                        )
                    ],
                    subsections=[],
                )
            ]
        )
        result = build_block_type_map(doc)
        assert result["section0body0table0"].has_caption is False

    def test_nested_sections(self) -> None:
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Outer"),
                    body=[],
                    subsections=[
                        TypstSection(
                            heading=TypstHeading(text="Inner"),
                            body=[TypstParagraph(text="Nested")],
                            subsections=[],
                        )
                    ],
                )
            ]
        )
        result = build_block_type_map(doc)
        assert "section0heading0" in result
        assert result["section0heading0"].heading_level == 1
        assert "section0section0heading0" in result
        assert result["section0section0heading0"].heading_level == 2
        assert "section0section0body0" in result
        assert result["section0section0body0"].block_type == TypstParagraph

    def test_multiple_tables(self) -> None:
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[
                        TypstTable(
                            headers=["A"],
                            data=[["1"]],
                            caption="Table 1",
                        ),
                        TypstTable(
                            headers=["B"],
                            data=[["2"]],
                            caption="Table 2",
                        ),
                    ],
                    subsections=[],
                )
            ]
        )
        result = build_block_type_map(doc)
        assert "section0body0table0" in result
        assert "section0body1table1" in result
