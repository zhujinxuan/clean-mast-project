"""CLI integration tests for draft-docx command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner
from typst_ir import TypstDocument, TypstHeading, TypstParagraph, TypstSection
from typst_ir.cli import app

runner = CliRunner()


def test_missing_input() -> None:
    result = runner.invoke(app, ["draft-docx", "nonexistent.json"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_invalid_json(tmp_path: Path) -> None:
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("not json", encoding="utf-8")
    result = runner.invoke(app, ["draft-docx", str(bad_json)])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_missing_tools(tmp_path: Path) -> None:
    doc = TypstDocument(
        children=[
            TypstSection(
                heading=TypstHeading(text="Test"),
                body=[TypstParagraph(text="Hello")],
                subsections=[],
            )
        ]
    )
    json_path = tmp_path / "input.json"
    json_path.write_text(doc.model_dump_json(), encoding="utf-8")

    with patch("typst_ir.cli.draft_docx_impl") as mock_impl:
        mock_impl.side_effect = RuntimeError("typst not found in PATH")
        result = runner.invoke(app, ["draft-docx", str(json_path)])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_valid_input(tmp_path: Path) -> None:
    doc = TypstDocument(
        children=[
            TypstSection(
                heading=TypstHeading(text="Test"),
                body=[TypstParagraph(text="Hello")],
                subsections=[],
            )
        ]
    )
    json_path = tmp_path / "input.json"
    json_path.write_text(doc.model_dump_json(), encoding="utf-8")
    result = runner.invoke(app, ["draft-docx", str(json_path)])
    assert result.exit_code == 0
    assert "Created:" in result.output
    assert (tmp_path / "input_draft.docx").exists()
