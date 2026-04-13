"""Tests for polish IR types.

Verifies frozen Pydantic models for style operations, renumber operations,
and the root PolishIR container. Includes JSON round-trip and immutability tests.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from typst_ir.polish import PolishIR, RenumberOp, StyleOp


class TestStyleOp:
    """Tests for StyleOp model."""

    def test_style_op_creation_minimal(self) -> None:
        """StyleOp can be created with just style_name."""
        op = StyleOp(style_name="Heading 1")
        assert op.style_name == "Heading 1"
        assert op.font_name is None
        assert op.font_size is None

    def test_style_op_creation_full(self) -> None:
        """StyleOp can be created with all optional fields."""
        op = StyleOp(
            style_name="Body Text",
            font_name="Times New Roman",
            font_name_chinese="SimSun",
            font_name_latin="Times New Roman",
            font_size=12.0,
            font_style="normal",
            font_color="#000000",
            line_spacing_before=6.0,
            line_spacing_after=6.0,
            line_spacing=1.15,
        )
        assert op.style_name == "Body Text"
        assert op.font_name == "Times New Roman"
        assert op.font_name_chinese == "SimSun"
        assert op.font_name_latin == "Times New Roman"
        assert op.font_size == 12.0
        assert op.font_style == "normal"
        assert op.font_color == "#000000"
        assert op.line_spacing_before == 6.0
        assert op.line_spacing_after == 6.0
        assert op.line_spacing == 1.15

    def test_style_op_is_frozen(self) -> None:
        """StyleOp is immutable (frozen model)."""
        op = StyleOp(style_name="Heading 1")
        with pytest.raises(ValidationError):
            op.style_name = "Heading 2"

    def test_style_op_json_roundtrip(self) -> None:
        """StyleOp serializes and deserializes correctly."""
        original = StyleOp(
            style_name="Caption",
            font_size=10.5,
            font_style="italic",
        )
        json_str = original.model_dump_json()
        restored = StyleOp.model_validate_json(json_str)
        assert restored == original

    def test_style_op_line_spacing(self) -> None:
        """StyleOp accepts line_spacing field."""
        op = StyleOp(style_name="Normal", line_spacing=1.15)
        assert op.line_spacing == 1.15

    def test_style_op_missing_style_name(self) -> None:
        """StyleOp requires style_name field."""
        with pytest.raises(ValidationError):
            StyleOp(font_size=12.0)  # ty: ignore[missing-argument]


class TestPolishIRBackwardCompat:
    """Tests for PolishIR backward compatibility."""

    def test_old_json_without_line_spacing_deserializes(self) -> None:
        """Old PolishIR JSON without line_spacing still deserializes."""
        json_str = '{"version":"1.0.0","styles":[{"style_name":"Normal","font_size":12.0}],"renumber":[]}'
        ir = PolishIR.model_validate_json(json_str)
        assert ir.styles[0].line_spacing is None


class TestRenumberOp:
    """Tests for RenumberOp model."""

    def test_renumber_op_creation(self) -> None:
        """RenumberOp can be created with required fields."""
        op = RenumberOp(element_type="heading")
        assert op.element_type == "heading"

    def test_renumber_op_various_types(self) -> None:
        """RenumberOp accepts all valid element types."""
        for etype in ["heading", "figure", "table"]:
            op = RenumberOp(element_type=etype)
            assert op.element_type == etype

    def test_renumber_op_is_frozen(self) -> None:
        """RenumberOp is immutable (frozen model)."""
        op = RenumberOp(element_type="figure")
        with pytest.raises(ValidationError):
            op.element_type = "table"

    def test_renumber_op_json_roundtrip(self) -> None:
        """RenumberOp serializes and deserializes correctly."""
        original = RenumberOp(element_type="table")
        json_str = original.model_dump_json()
        restored = RenumberOp.model_validate_json(json_str)
        assert restored == original

    def test_renumber_op_missing_field(self) -> None:
        """RenumberOp requires element_type field."""
        with pytest.raises(ValidationError):
            RenumberOp()  # ty: ignore[missing-argument]


class TestPolishIR:
    """Tests for PolishIR root container."""

    def test_polish_ir_empty(self) -> None:
        """PolishIR can be created with defaults."""
        ir = PolishIR()
        assert ir.version == "1.0.0"
        assert ir.styles == []
        assert ir.renumber == []

    def test_polish_ir_with_children(self) -> None:
        """PolishIR can contain styles and renumber operations."""
        ir = PolishIR(
            styles=[
                StyleOp(style_name="Heading 1", font_size=16.0),
                StyleOp(style_name="Heading 2", font_size=14.0),
            ],
            renumber=[
                RenumberOp(element_type="heading"),
                RenumberOp(element_type="figure"),
            ],
        )
        assert len(ir.styles) == 2
        assert len(ir.renumber) == 2
        assert ir.styles[0].font_size == 16.0
        assert ir.renumber[1].element_type == "figure"

    def test_polish_ir_is_frozen(self) -> None:
        """PolishIR is immutable (frozen model)."""
        ir = PolishIR()
        with pytest.raises(ValidationError):
            ir.version = "2.0.0"

    def test_polish_ir_json_roundtrip(self) -> None:
        """PolishIR serializes and deserializes correctly."""
        original = PolishIR(
            version="1.0.0",
            styles=[
                StyleOp(style_name="Title", font_name="Arial", font_size=18.0),
            ],
            renumber=[RenumberOp(element_type="table")],
        )
        json_str = original.model_dump_json()
        restored = PolishIR.model_validate_json(json_str)
        assert restored == original

    def test_polish_ir_json_roundtrip_empty(self) -> None:
        """Empty PolishIR round-trips correctly."""
        original = PolishIR()
        json_str = original.model_dump_json()
        restored = PolishIR.model_validate_json(json_str)
        assert restored == original
        assert restored.styles == []
        assert restored.renumber == []
