from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner
from typst_ir import TypstDocument, TypstHeading, TypstParagraph, TypstSection
from typst_ir.cli import app

runner = CliRunner()


def test_render_pdf_help() -> None:
    result = runner.invoke(app, ["render-pdf", "--help"])
    assert result.exit_code == 0
    assert "Render JSON IR to PDF" in result.output


def test_render_pdf_missing_input() -> None:
    result = runner.invoke(app, ["render-pdf", "nonexistent.json", "/tmp/out"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_render_pdf_invalid_json(tmp_path: Path) -> None:
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("not json", encoding="utf-8")
    result = runner.invoke(app, ["render-pdf", str(bad_json), str(tmp_path / "out")])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_render_pdf_missing_tools(tmp_path: Path) -> None:
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

    with patch("typst_ir.cli.render_to_pdf") as mock_render:
        mock_render.side_effect = RuntimeError("typst not found")
        result = runner.invoke(app, ["render-pdf", str(json_path), str(tmp_path / "out")])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_render_pdf_valid_input(tmp_path: Path) -> None:
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

    with patch("typst_ir.cli.render_to_pdf") as mock_render:
        mock_render.return_value = tmp_path / "out" / "report.pdf"
        result = runner.invoke(app, ["render-pdf", str(json_path), str(tmp_path / "out")])

    assert result.exit_code == 0
    assert "Created:" in result.output
