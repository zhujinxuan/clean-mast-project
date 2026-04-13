"""Tests for Typst IR serializer.

Tests for serialization of IR nodes to Typst markup strings.
"""

from __future__ import annotations

import pytest
from typst_ir import (
    TypstBulletList,
    TypstDocument,
    TypstFigure,
    TypstHeading,
    TypstOrderedList,
    TypstParagraph,
    TypstSection,
    TypstTable,
    serialize,
)


class TestSerializeBasicNodes:
    """Test serialization of basic IR node types."""

    def test_serialize_heading_level1(self) -> None:
        """Test level 1 heading serialization."""
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Introduction"),
                body=[],
                subsections=[],
            )
        ])
        result = serialize(doc)
        assert "= Introduction" in result

    def test_serialize_heading_level2(self) -> None:
        """Test level 2 heading serialization."""
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Outer"),
                body=[],
                subsections=[
                    TypstSection(
                        heading=TypstHeading(text="Inner"),
                        body=[],
                        subsections=[]
                    )
                ]
            )
        ])
        result = serialize(doc)
        assert "= Outer" in result
        assert "== Inner" in result

    def test_serialize_heading_level3(self) -> None:
        """Test level 3 heading serialization."""
        level3 = TypstSection(heading=TypstHeading(text="Details"), body=[], subsections=[])
        level2 = TypstSection(heading=TypstHeading(text="Mid"), body=[], subsections=[level3])
        level1 = TypstSection(heading=TypstHeading(text="Top"), body=[], subsections=[level2])
        doc = TypstDocument(children=[level1])
        result = serialize(doc)
        assert "= Top" in result
        assert "== Mid" in result
        assert "=== Details" in result

    def test_serialize_paragraph(self) -> None:
        """Test paragraph serialization."""
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Intro"),
                body=[TypstParagraph(text="This is a test paragraph.")],
                subsections=[],
            )
        ])
        result = serialize(doc)
        assert "This is a test paragraph." in result


class TestSerializeTable:
    """Test table serialization to Typst markup."""

    def test_serialize_table_basic(self) -> None:
        """Test basic table serialization."""
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Data"),
                    body=[
                        TypstTable(
                            data=[["1", "2"], ["3", "4"]],
                            headers=["A", "B"],
                        )
                    ],
                    subsections=[],
                )
            ]
        )
        result = serialize(doc)
        assert "#table(" in result
        assert "columns: (auto, auto)" in result
        assert "[A]" in result
        assert "[B]" in result
        assert "[1]" in result
        assert "[4]" in result

    def test_serialize_table_with_caption(self) -> None:
        """Test table serialization with caption (wrapped in figure)."""
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Data"),
                    body=[
                        TypstTable(
                            data=[["x", "y"]],
                            headers=["X", "Y"],
                            caption="Test Table",
                        )
                    ],
                    subsections=[],
                )
            ]
        )
        result = serialize(doc)
        assert "#figure(" in result
        assert "table(" in result  # Nested without leading #
        assert 'caption: [Test Table]' in result

    def test_serialize_table_empty_data_raises(self) -> None:
        """Test that empty table data raises ValueError."""
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Data"),
                    body=[
                        TypstTable(
                            data=[],
                            headers=["A"],
                        )
                    ],
                    subsections=[],
                )
            ]
        )
        with pytest.raises(ValueError, match="Table data cannot be empty"):
            serialize(doc)

    def test_serialize_table_column_mismatch_raises(self) -> None:
        """Test that column count mismatch raises ValueError."""
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Data"),
                    body=[
                        TypstTable(
                            data=[["1", "2", "3"]],  # 3 columns
                            headers=["A", "B"],  # 2 columns
                        )
                    ],
                    subsections=[],
                )
            ]
        )
        with pytest.raises(ValueError, match="Header column count"):
            serialize(doc)


class TestSerializeFigure:
    """Test figure serialization to Typst markup."""

    def test_serialize_figure_basic(self) -> None:
        """Test basic figure serialization."""
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Chart"),
                    body=[
                        TypstFigure(
                            content="images/chart.png",
                            caption="Wind Speed Chart",
                        )
                    ],
                    subsections=[],
                )
            ]
        )
        result = serialize(doc)
        assert "#figure(" in result
        assert 'image("images/chart.png", width: 80%)' in result
        assert "caption: [Wind Speed Chart]" in result

    def test_serialize_figure_empty_content_raises(self) -> None:
        """Test that empty figure content raises ValueError."""
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Chart"),
                    body=[
                        TypstFigure(
                            content="",
                            caption="Empty Figure",
                        )
                    ],
                    subsections=[],
                )
            ]
        )
        with pytest.raises(ValueError, match="Figure content.*cannot be empty"):
            serialize(doc)


class TestSerializeDocument:
    """Test full document serialization."""

    def test_serialize_empty_document(self) -> None:
        """Test empty document serialization."""
        doc = TypstDocument(children=[])
        result = serialize(doc)
        assert result == ""

    def test_serialize_mixed_content(self) -> None:
        """Test document with mixed content types."""
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Report"),
                    body=[
                        TypstParagraph(text="This is the introduction."),
                        TypstTable(data=[["A", "B"]], headers=["Col1", "Col2"]),
                    ],
                    subsections=[
                        TypstSection(
                            heading=TypstHeading(text="Data"),
                            body=[TypstParagraph(text="Data section.")],
                            subsections=[]
                        )
                    ]
                )
            ]
        )
        result = serialize(doc)
        assert "= Report" in result
        assert "This is the introduction." in result
        assert "== Data" in result
        assert "#table(" in result

    def test_serialize_non_document_root_raises(self) -> None:
        """Test that non-TypstDocument root raises TypeError."""
        with pytest.raises(TypeError, match="Expected TypstDocument root"):
            serialize(TypstHeading(text="Not a document"))  # type: ignore[arg-type]


class TestSerializeHeadingNormalization:
    """Test heading level normalization during serialization."""

    def test_heading_level_below1_normalized(self) -> None:
        """Test that serializer normalizes level to minimum of 1."""
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Test"),
                body=[],
                subsections=[],
            )
        ])
        result = serialize(doc)
        assert "= Test" in result
        assert "==" not in result

    def test_heading_level_above3_preserved(self) -> None:
        """Test that deeply nested sections produce high heading levels."""
        inner = TypstSection(heading=TypstHeading(text="Test"), body=[], subsections=[])
        for _ in range(4):
            inner = TypstSection(heading=TypstHeading(text="Parent"), body=[], subsections=[inner])
        doc = TypstDocument(children=[inner])
        result = serialize(doc)
        assert "===== Test" in result


class TestSerializeBodyHeadings:
    """Test body heading level serialization based on section depth."""

    def test_body_heading_depth1(self) -> None:
        """Test body heading at section depth 1 gets one equals sign."""
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Section"),
                body=[TypstHeading(text="Body Heading")],
                subsections=[],
            )
        ])
        result = serialize(doc)
        assert "= Body Heading\n" in result

    def test_body_heading_depth2(self) -> None:
        """Test body heading at section depth 2 gets two equals signs."""
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Outer"),
                body=[],
                subsections=[
                    TypstSection(
                        heading=TypstHeading(text="Inner"),
                        body=[TypstHeading(text="Body Heading")],
                        subsections=[],
                    )
                ],
            )
        ])
        result = serialize(doc)
        assert "== Body Heading\n" in result

    def test_body_heading_depth3(self) -> None:
        """Test body heading at section depth 3 gets three equals signs."""
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Level1"),
                body=[],
                subsections=[
                    TypstSection(
                        heading=TypstHeading(text="Level2"),
                        body=[],
                        subsections=[
                            TypstSection(
                                heading=TypstHeading(text="Level3"),
                                body=[TypstHeading(text="Body Heading")],
                                subsections=[],
                            )
                        ],
                    )
                ],
            )
        ])
        result = serialize(doc)
        assert "=== Body Heading\n" in result

    def test_bullet_list_heading_depth2(self) -> None:
        """Test bullet list heading at section depth 2 gets two equals signs."""
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Outer"),
                body=[],
                subsections=[
                    TypstSection(
                        heading=TypstHeading(text="Inner"),
                        body=[
                            TypstBulletList(items=[[TypstHeading(text="List Heading")]])
                        ],
                        subsections=[],
                    )
                ],
            )
        ])
        result = serialize(doc)
        assert "== List Heading\n" in result

    def test_ordered_list_heading_depth2(self) -> None:
        """Test ordered list heading at section depth 2 gets two equals signs."""
        doc = TypstDocument(children=[
            TypstSection(
                heading=TypstHeading(text="Outer"),
                body=[],
                subsections=[
                    TypstSection(
                        heading=TypstHeading(text="Inner"),
                        body=[
                            TypstOrderedList(items=[[TypstHeading(text="List Heading")]])
                        ],
                        subsections=[],
                    )
                ],
            )
        ])
        result = serialize(doc)
        assert "== List Heading\n" in result
