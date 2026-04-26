"""Tests for polish_styles module.

TDD tests for StyleProperties, StyleDef, and DEFAULT_STYLE_DEFS.
"""

from __future__ import annotations

import pytest
from typst_ir.polish_styles import (
    DEFAULT_STYLE_DEFS,
    LineSpacing,
    StyleDef,
    StyleProperties,
)


class TestStyleProperties:
    """Test StyleProperties construction and behavior."""

    def test_empty_construction(self) -> None:
        """Test that all-optional construction works."""
        props = StyleProperties()
        assert props.font_name is None
        assert props.font_name_east_asia is None
        assert props.font_size is None
        assert props.bold is None
        assert props.alignment is None
        assert props.first_line_indent_chars is None
        assert props.space_before is None
        assert props.space_after is None
        assert props.line_spacing is None

    def test_full_construction(self) -> None:
        """Test construction with all fields."""
        props = StyleProperties(
            font_name="Times New Roman",
            font_name_east_asia="宋体",
            font_size=12,
            bold=True,
            alignment="center",
            first_line_indent_chars=2,
            space_before=6,
            space_after=6,
            line_spacing=LineSpacing(value=1.5, unit="multiplier"),
        )
        assert props.font_name == "Times New Roman"
        assert props.font_name_east_asia == "宋体"
        assert props.font_size == 12
        assert props.bold is True
        assert props.alignment == "center"
        assert props.first_line_indent_chars == 2
        assert props.space_before == 6
        assert props.space_after == 6
        assert props.line_spacing == LineSpacing(value=1.5, unit="multiplier")

    def test_is_frozen(self) -> None:
        """Test that StyleProperties is immutable."""
        props = StyleProperties(font_size=12)
        with pytest.raises(Exception):
            props.font_size = 14

    def test_partial_construction(self) -> None:
        """Test construction with only some fields."""
        props = StyleProperties(font_size=12, bold=True)
        assert props.font_size == 12
        assert props.bold is True
        assert props.font_name is None


class TestStyleDef:
    """Test StyleDef construction and behavior."""

    def test_construction_with_base_style(self) -> None:
        """Test construction with base style and properties."""
        props = StyleProperties(font_size=12)
        style_def = StyleDef(base_style="Normal", properties=props)
        assert style_def.base_style == "Normal"
        assert style_def.properties == props

    def test_construction_without_base_style(self) -> None:
        """Test construction with None base style."""
        props = StyleProperties(font_size=12)
        style_def = StyleDef(base_style=None, properties=props)
        assert style_def.base_style is None
        assert style_def.properties.font_size == 12

    def test_is_frozen(self) -> None:
        """Test that StyleDef is immutable."""
        style_def = StyleDef(
            base_style="Normal",
            properties=StyleProperties(font_size=12),
        )
        with pytest.raises(Exception):
            style_def.base_style = "Heading1"


class TestLineSpacing:
    """Test LineSpacing construction and behavior."""

    def test_pt_construction(self) -> None:
        """Test construction with pt unit."""
        ls = LineSpacing(value=23, unit="pt")
        assert ls.value == 23
        assert ls.unit == "pt"

    def test_multiplier_construction(self) -> None:
        """Test construction with multiplier unit."""
        ls = LineSpacing(value=1.5, unit="multiplier")
        assert ls.value == 1.5
        assert ls.unit == "multiplier"

    def test_is_frozen(self) -> None:
        """Test that LineSpacing is immutable."""
        ls = LineSpacing(value=23, unit="pt")
        with pytest.raises(Exception):
            ls.value = 24


class TestDefaultStyleDefs:
    """Test DEFAULT_STYLE_DEFS registry contents."""

    def test_has_exactly_nine_entries(self) -> None:
        """Test that DEFAULT_STYLE_DEFS contains exactly 9 styles."""
        assert len(DEFAULT_STYLE_DEFS) == 9

    def test_all_keys_use_prefix(self) -> None:
        """Test that all style names use the typst-ir- prefix."""
        for key in DEFAULT_STYLE_DEFS:
            assert key.startswith("typst-ir-"), f"Key '{key}' missing prefix"

    def test_paragraph_style(self) -> None:
        """Test typst-ir-Paragraph style values."""
        style = DEFAULT_STYLE_DEFS["typst-ir-Paragraph"]
        assert style.base_style == "Normal"
        assert style.properties.font_name == "Times New Roman"
        assert style.properties.font_name_east_asia == "宋体"
        assert style.properties.font_size == 12
        assert style.properties.first_line_indent_chars == 2
        assert style.properties.line_spacing == LineSpacing(value=23, unit="pt")
        assert style.properties.bold is None
        assert style.properties.alignment is None
        assert style.properties.space_before == 0
        assert style.properties.space_after == 0

    def test_heading1_style(self) -> None:
        """Test typst-ir-Heading1 style values."""
        style = DEFAULT_STYLE_DEFS["typst-ir-Heading1"]
        assert style.base_style == "Heading 1"
        assert style.properties.font_size == 12
        assert style.properties.bold is True
        assert style.properties.font_name is None

    def test_heading2_style(self) -> None:
        """Test typst-ir-Heading2 style values."""
        style = DEFAULT_STYLE_DEFS["typst-ir-Heading2"]
        assert style.base_style == "Heading 2"
        assert style.properties.font_size == 12
        assert style.properties.bold is True

    def test_heading3_style(self) -> None:
        """Test typst-ir-Heading3 style values."""
        style = DEFAULT_STYLE_DEFS["typst-ir-Heading3"]
        assert style.base_style == "Heading 3"
        assert style.properties.font_size == 12
        assert style.properties.bold is True

    def test_heading4_style(self) -> None:
        """Test typst-ir-Heading4 style values (normal weight)."""
        style = DEFAULT_STYLE_DEFS["typst-ir-Heading4"]
        assert style.base_style == "Heading 4"
        assert style.properties.font_size == 12
        assert style.properties.bold is False

    def test_heading5_style(self) -> None:
        """Test typst-ir-Heading5 style values."""
        style = DEFAULT_STYLE_DEFS["typst-ir-Heading5"]
        assert style.base_style == "Heading 5"
        assert style.properties.font_size == 12
        assert style.properties.bold is True

    def test_table_caption_style(self) -> None:
        """Test typst-ir-TableCaption style values."""
        style = DEFAULT_STYLE_DEFS["typst-ir-TableCaption"]
        assert style.base_style == "Normal"
        assert style.properties.font_name == "Times New Roman"
        assert style.properties.font_name_east_asia == "宋体"
        assert style.properties.font_size == 12
        assert style.properties.alignment == "center"
        assert style.properties.space_before == 5
        assert style.properties.space_after == 0

    def test_figure_caption_style(self) -> None:
        """Test typst-ir-FigureCaption style values."""
        style = DEFAULT_STYLE_DEFS["typst-ir-FigureCaption"]
        assert style.base_style == "Normal"
        assert style.properties.font_name == "Times New Roman"
        assert style.properties.font_name_east_asia == "宋体"
        assert style.properties.font_size == 12
        assert style.properties.alignment == "center"
        assert style.properties.space_before == 0
        assert style.properties.space_after == 5

    def test_table_content_style(self) -> None:
        """Test typst-ir-TableContent style values."""
        style = DEFAULT_STYLE_DEFS["typst-ir-TableContent"]
        assert style.base_style == "Normal"
        assert style.properties.font_name == "Times New Roman"
        assert style.properties.font_name_east_asia == "宋体"
        assert style.properties.font_size == 9
        assert style.properties.space_before == 0
        assert style.properties.space_after == 0
        assert style.properties.bold is None

    def test_expected_keys_present(self) -> None:
        """Test that all expected style names are present."""
        expected = {
            "typst-ir-Paragraph",
            "typst-ir-Heading1",
            "typst-ir-Heading2",
            "typst-ir-Heading3",
            "typst-ir-Heading4",
            "typst-ir-Heading5",
            "typst-ir-TableCaption",
            "typst-ir-FigureCaption",
            "typst-ir-TableContent",
        }
        assert set(DEFAULT_STYLE_DEFS.keys()) == expected
