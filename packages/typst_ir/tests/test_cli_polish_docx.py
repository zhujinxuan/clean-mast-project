"""CLI integration tests for polish-docx command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner
from typst_ir.cli import app

runner = CliRunner()


def test_polish_docx_help() -> None:
    result = runner.invoke(app, ["polish-docx", "--help"])
    assert result.exit_code == 0
    assert "Polish a DOCX using Typst IR instructions" in result.output


def test_polish_docx_missing_docx(tmp_path: Path) -> None:
    ir_json = tmp_path / "ir.json"
    ir_json.write_text("{}", encoding="utf-8")
    result = runner.invoke(
        app, [
            "polish-docx",
            str(tmp_path / "missing.docx"),
            str(ir_json),
            str(tmp_path / "output.docx"),
        ]
    )
    assert result.exit_code == 1
    assert "not found" in result.output


def test_polish_docx_missing_ir_json(tmp_path: Path) -> None:
    docx = tmp_path / "input.docx"
    docx.write_text("fake docx", encoding="utf-8")
    result = runner.invoke(
        app, [
            "polish-docx",
            str(docx),
            str(tmp_path / "missing.json"),
            str(tmp_path / "output.docx"),
        ]
    )
    assert result.exit_code == 1
    assert "not found" in result.output


def test_polish_docx_error_from_polish(tmp_path: Path) -> None:
    docx = tmp_path / "input.docx"
    docx.write_text("fake docx", encoding="utf-8")
    ir_json = tmp_path / "ir.json"
    ir_json.write_text("{}", encoding="utf-8")

    with patch("typst_ir.cli.polish_docx") as mock_polish:
        mock_polish.side_effect = RuntimeError("section map extraction failed")
        result = runner.invoke(
            app, [
                "polish-docx",
                str(docx),
                str(ir_json),
                str(tmp_path / "output.docx"),
            ]
        )

    assert result.exit_code == 1
    assert "Error" in result.output


def test_polish_docx_valid_input(tmp_path: Path) -> None:
    docx = tmp_path / "input.docx"
    docx.write_text("fake docx", encoding="utf-8")
    ir_json = tmp_path / "ir.json"
    ir_json.write_text("{}", encoding="utf-8")
    output = tmp_path / "output.docx"

    def mock_polish(docx_path: Path, ir_path: Path, out_path: Path) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("polished", encoding="utf-8")

    with patch("typst_ir.cli.polish_docx", side_effect=mock_polish):
        result = runner.invoke(
            app, ["polish-docx", str(docx), str(ir_json), str(output)]
        )

    assert result.exit_code == 0
    assert "Polished DOCX saved to" in result.output
    assert output.exists()
