"""Tests for Polish IR types.

Covers construction, immutability, and validation of ChangeStyle,
CreateStyle, and EditStyle models.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from typst_ir.polish_ir import (
    ApplyTableFormat,
    ChangeStyle,
    CreateStyle,
    EditStyle,
    PolishIR,
    TableBorderEdge,
    TableFormat,
)


class TestChangeStyle:
    def test_construction_with_path_and_indices(self) -> None:
        op = ChangeStyle(
            path="section0body2table0",
            target_style="TableStyle",
            paragraph_indices=(1, 2, 3),
            cell_table_indices=((0, 0, 0), (0, 1, 0)),
        )
        assert op.path == "section0body2table0"
        assert op.target_style == "TableStyle"
        assert op.paragraph_indices == (1, 2, 3)
        assert op.cell_table_indices == ((0, 0, 0), (0, 1, 0))

    def test_construction_with_defaults(self) -> None:
        op = ChangeStyle(path="section0body2", target_style="ParagraphStyle")
        assert op.path == "section0body2"
        assert op.target_style == "ParagraphStyle"
        assert op.paragraph_indices == ()
        assert op.cell_table_indices == ()

    def test_frozen_prevents_mutation(self) -> None:
        op = ChangeStyle(path="section0body2table0", target_style="TableStyle")
        with pytest.raises(ValidationError):
            op.path = "other"

    def test_missing_fields_raises(self) -> None:
        with pytest.raises(ValidationError):
            ChangeStyle(path="section0body2table0")
        with pytest.raises(ValidationError):
            ChangeStyle(target_style="TableStyle")

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            ChangeStyle(path=123, target_style="TableStyle")

    def test_is_hashable(self) -> None:
        op = ChangeStyle(path="section0body2table0", target_style="TableStyle")
        assert hash(op) == hash(op)


class TestCreateStyle:
    def test_construction_with_base(self) -> None:
        op = CreateStyle(
            style_name="CustomHeading",
            base_style="Heading",
            properties={"size": "14pt"},
        )
        assert op.style_name == "CustomHeading"
        assert op.base_style == "Heading"
        assert op.properties == {"size": "14pt"}

    def test_construction_without_base(self) -> None:
        op = CreateStyle(
            style_name="CustomHeading",
            base_style=None,
            properties={"size": "14pt"},
        )
        assert op.base_style is None

    def test_frozen_prevents_mutation(self) -> None:
        op = CreateStyle(
            style_name="CustomHeading",
            base_style=None,
            properties={"size": "14pt"},
        )
        with pytest.raises(ValidationError):
            op.style_name = "Other"

    def test_missing_fields_raises(self) -> None:
        with pytest.raises(ValidationError):
            CreateStyle(style_name="CustomHeading")

    def test_invalid_properties_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            CreateStyle(
                style_name="CustomHeading",
                base_style=None,
                properties="not-a-dict",
            )

    def test_dict_properties_accepted(self) -> None:
        op = CreateStyle(
            style_name="CustomHeading",
            base_style=None,
            properties={"size": "14pt", "nested": {"a": 1}},
        )
        assert op.properties == {"size": "14pt", "nested": {"a": 1}}


class TestEditStyle:
    def test_construction(self) -> None:
        op = EditStyle(
            style_name="CustomHeading",
            properties={"color": "blue"},
        )
        assert op.style_name == "CustomHeading"
        assert op.properties == {"color": "blue"}

    def test_frozen_prevents_mutation(self) -> None:
        op = EditStyle(
            style_name="CustomHeading",
            properties={"color": "blue"},
        )
        with pytest.raises(ValidationError):
            op.properties = {"color": "red"}

    def test_missing_fields_raises(self) -> None:
        with pytest.raises(ValidationError):
            EditStyle(style_name="CustomHeading")

    def test_dict_properties_accepted(self) -> None:
        op = EditStyle(
            style_name="CustomHeading",
            properties={"color": "blue", "nested": {"a": 1}},
        )
        assert op.properties == {"color": "blue", "nested": {"a": 1}}


class TestPolishIRUnion:
    def test_change_is_polish_ir(self) -> None:
        op: PolishIR = ChangeStyle(path="b1", target_style="S1")
        assert isinstance(op, ChangeStyle)

    def test_create_is_polish_ir(self) -> None:
        op: PolishIR = CreateStyle(
            style_name="S1", base_style=None, properties={}
        )
        assert isinstance(op, CreateStyle)

    def test_edit_is_polish_ir(self) -> None:
        op: PolishIR = EditStyle(style_name="S1", properties={})
        assert isinstance(op, EditStyle)

    def test_apply_table_format_is_polish_ir(self) -> None:
        op: PolishIR = ApplyTableFormat(
            path="t0", table_indices=(0,), format=TableFormat()
        )
        assert isinstance(op, ApplyTableFormat)


class TestTableBorderEdge:
    def test_default_values(self) -> None:
        edge = TableBorderEdge()
        assert edge.val == "single"
        assert edge.sz == 4
        assert edge.color == "000000"
        assert edge.space == 0

    def test_custom_values(self) -> None:
        edge = TableBorderEdge(val="double", sz=8, color="FF0000", space=2)
        assert edge.val == "double"
        assert edge.sz == 8
        assert edge.color == "FF0000"
        assert edge.space == 2

    def test_frozen_prevents_mutation(self) -> None:
        edge = TableBorderEdge()
        with pytest.raises(ValidationError):
            edge.val = "double"


class TestTableFormat:
    def test_default_values(self) -> None:
        fmt = TableFormat()
        assert fmt.alignment == "center"
        assert fmt.borders == TableBorderEdge()

    def test_alignment_none(self) -> None:
        fmt = TableFormat(alignment=None, borders=TableBorderEdge())
        assert fmt.alignment is None

    def test_borders_none(self) -> None:
        fmt = TableFormat(alignment="center", borders=None)
        assert fmt.borders is None

    def test_frozen_prevents_mutation(self) -> None:
        fmt = TableFormat()
        with pytest.raises(ValidationError):
            fmt.alignment = "left"


class TestApplyTableFormat:
    def test_construction(self) -> None:
        op = ApplyTableFormat(
            path="t0", table_indices=(0,), format=TableFormat()
        )
        assert op.path == "t0"
        assert op.table_indices == (0,)
        assert op.format == TableFormat()

    def test_table_indices_tuple(self) -> None:
        op = ApplyTableFormat(
            path="t0", table_indices=(0, 1, 2), format=TableFormat()
        )
        assert op.table_indices == (0, 1, 2)

    def test_frozen_prevents_mutation(self) -> None:
        op = ApplyTableFormat(
            path="t0", table_indices=(0,), format=TableFormat()
        )
        with pytest.raises(ValidationError):
            op.path = "t1"
