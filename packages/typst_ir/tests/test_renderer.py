"""Tests for Typst IR renderer.

Tests for rendering JSON IR to Typst markup, PDF, and DOCX.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typst_ir import (
    compile_typst_to_docx,
    compile_typst_to_pdf,
    render_to_docx,
    render_to_pdf,
    render_to_typst,
)


class TestRenderToTypst:
    """Test render_to_typst function."""

    def test_render_simple_heading(self) -> None:
        """Test rendering JSON with heading to Typst markup."""
        json_str = json.dumps({
            "children": [
                {
                    "typst_type": "TypstSection",
                    "heading": {"text": "Hello World", "typst_type": "TypstHeading"},
                    "body": [],
                    "subsections": []
                }
            ]
        })
        result = render_to_typst(json_str)
        assert "= Hello World" in result

    def test_render_heading_and_paragraph(self) -> None:
        """Test rendering JSON with heading and paragraph."""
        json_str = json.dumps({
            "children": [
                {
                    "typst_type": "TypstSection",
                    "heading": {"text": "Title", "typst_type": "TypstHeading"},
                    "body": [
                        {"text": "Content here", "typst_type": "TypstParagraph"}
                    ],
                    "subsections": []
                }
            ]
        })
        result = render_to_typst(json_str)
        assert "= Title" in result
        assert "Content here" in result

    def test_render_invalid_json_raises(self) -> None:
        """Test that invalid JSON raises ValueError."""
        with pytest.raises(ValueError):
            render_to_typst("not valid json")

    def test_render_invalid_document_raises(self) -> None:
        """Test that invalid document structure raises ValidationError."""
        json_str = json.dumps({"invalid": "structure"})
        with pytest.raises(Exception):  # Pydantic ValidationError
            render_to_typst(json_str)


class TestRenderToPDF:
    """Test render_to_pdf function."""

    @patch("typst_ir.renderer._check_typst_cli")
    @patch("typst_ir.renderer.subprocess.run")
    def test_render_to_pdf_success(self, mock_run: MagicMock, mock_check: MagicMock) -> None:
        """Test successful PDF rendering."""
        mock_run.return_value = MagicMock(returncode=0)
        
        json_str = json.dumps({
            "children": [
                {
                    "typst_type": "TypstSection",
                    "heading": {"text": "Report", "typst_type": "TypstHeading"},
                    "body": [],
                    "subsections": []
                }
            ]
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result = render_to_pdf(json_str, output_dir)
            
            assert result.suffix == ".pdf"
            assert result.name == "report.pdf"
            assert result.parent == output_dir
            mock_check.assert_called_once()
            mock_run.assert_called_once()

    @patch("typst_ir.renderer._check_typst_cli")
    @patch("typst_ir.renderer.subprocess.run")
    def test_render_to_pdf_compilation_error(self, mock_run: MagicMock, mock_check: MagicMock) -> None:
        """Test PDF rendering with compilation error."""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, ["typst"], stderr=b"Compilation failed")
        
        json_str = json.dumps({
            "children": [
                {
                    "typst_type": "TypstSection",
                    "heading": {"text": "Report", "typst_type": "TypstHeading"},
                    "body": [],
                    "subsections": []
                }
            ]
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(RuntimeError, match="Typst compilation failed"):
                render_to_pdf(json_str, Path(tmpdir))


class TestRenderToDOCX:
    """Test render_to_docx function."""

    @patch("typst_ir.renderer._check_pandoc")
    @patch("typst_ir.renderer.subprocess.run")
    def test_render_to_docx_success(self, mock_run: MagicMock, mock_check: MagicMock) -> None:
        """Test successful DOCX rendering."""
        mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        
        json_str = json.dumps({
            "children": [
                {
                    "typst_type": "TypstSection",
                    "heading": {"text": "Report", "typst_type": "TypstHeading"},
                    "body": [],
                    "subsections": []
                }
            ]
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result = render_to_docx(json_str, output_dir)
            
            assert result.suffix == ".docx"
            assert result.name == "report.docx"
            assert result.parent == output_dir
            mock_check.assert_called_once()
            mock_run.assert_called_once()

    @patch("typst_ir.renderer._check_pandoc")
    @patch("typst_ir.renderer.subprocess.run")
    def test_render_to_docx_conversion_error(self, mock_run: MagicMock, mock_check: MagicMock) -> None:
        """Test DOCX rendering with conversion error."""
        mock_run.return_value = MagicMock(returncode=1, stdout=b"", stderr=b"Conversion failed")
        
        json_str = json.dumps({
            "children": [
                {
                    "typst_type": "TypstSection",
                    "heading": {"text": "Report", "typst_type": "TypstHeading"},
                    "body": [],
                    "subsections": []
                }
            ]
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(RuntimeError, match="DOCX conversion failed"):
                render_to_docx(json_str, Path(tmpdir))

    @patch("typst_ir.renderer._check_pandoc")
    @patch("typst_ir.renderer.subprocess.run")
    def test_render_to_docx_timeout(self, mock_run: MagicMock, mock_check: MagicMock) -> None:
        """Test DOCX rendering timeout."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("pandoc", 300)
        
        json_str = json.dumps({
            "children": [
                {
                    "typst_type": "TypstSection",
                    "heading": {"text": "Report", "typst_type": "TypstHeading"},
                    "body": [],
                    "subsections": []
                }
            ]
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(RuntimeError, match="timed out"):
                render_to_docx(json_str, Path(tmpdir))


class TestCheckTypstCLI:
    """Test _check_typst_cli helper function."""

    @patch("typst_ir.renderer.subprocess.run")
    def test_check_typst_cli_installed(self, mock_run: MagicMock) -> None:
        """Test check when typst is installed."""
        mock_run.return_value = MagicMock(returncode=0)
        
        # Should not raise
        from typst_ir.renderer import _check_typst_cli
        _check_typst_cli()
        mock_run.assert_called_once_with(
            ["typst", "--version"],
            capture_output=True,
            check=True
        )

    @patch("typst_ir.renderer.subprocess.run")
    def test_check_typst_cli_not_installed(self, mock_run: MagicMock) -> None:
        """Test check when typst is not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        from typst_ir.renderer import _check_typst_cli
        with pytest.raises(RuntimeError, match="Typst CLI not found"):
            _check_typst_cli()


class TestCheckPandoc:
    """Test _check_pandoc helper function."""

    @patch("typst_ir.renderer.shutil.which")
    def test_check_pandoc_installed(self, mock_which: MagicMock) -> None:
        """Test check when pandoc is installed."""
        mock_which.return_value = "/usr/bin/pandoc"
        
        # Should not raise
        from typst_ir.renderer import _check_pandoc
        _check_pandoc()
        mock_which.assert_called_once_with("pandoc")

    @patch("typst_ir.renderer.shutil.which")
    def test_check_pandoc_not_installed(self, mock_which: MagicMock) -> None:
        """Test check when pandoc is not installed."""
        mock_which.return_value = None
        
        from typst_ir.renderer import _check_pandoc
        with pytest.raises(RuntimeError, match="pandoc not found"):
            _check_pandoc()


class TestCompileTypstToPdf:
    """Test compile_typst_to_pdf function."""

    @patch("typst_ir.renderer._check_typst_cli")
    @patch("typst_ir.renderer.subprocess.run")
    def test_compile_typst_to_pdf_with_json(self, mock_run: MagicMock, mock_check: MagicMock, tmp_path: Path) -> None:
        """Test that .typ.json is created when json_content is provided."""
        mock_run.return_value = MagicMock(returncode=0)

        json_str = json.dumps({
            "children": [
                {
                    "typst_type": "TypstSection",
                    "heading": {"text": "Report", "typst_type": "TypstHeading"},
                    "body": [],
                    "subsections": []
                }
            ]
        })

        typ_path = tmp_path / "report.typ"
        typ_path.write_text("= Report", encoding="utf-8")

        result = compile_typst_to_pdf(typ_path, tmp_path, json_content=json_str)

        assert result.suffix == ".pdf"
        json_path = typ_path.with_suffix(".typ.json")
        assert json_path.read_text(encoding="utf-8") == json_str
        mock_check.assert_called_once()
        mock_run.assert_called_once()

    @patch("typst_ir.renderer._check_typst_cli")
    @patch("typst_ir.renderer.subprocess.run")
    def test_compile_typst_to_pdf_without_json(self, mock_run: MagicMock, mock_check: MagicMock, tmp_path: Path) -> None:
        """Test that no .typ.json is created when json_content is None."""
        mock_run.return_value = MagicMock(returncode=0)

        typ_path = tmp_path / "report.typ"
        typ_path.write_text("= Report", encoding="utf-8")

        result = compile_typst_to_pdf(typ_path, tmp_path, json_content=None)

        assert result.suffix == ".pdf"
        json_path = typ_path.with_suffix(".typ.json")
        assert not json_path.exists()
        mock_check.assert_called_once()
        mock_run.assert_called_once()


class TestCompileTypstToDocx:
    """Test compile_typst_to_docx function."""

    @patch("typst_ir.renderer._check_pandoc")
    @patch("typst_ir.renderer.subprocess.run")
    def test_compile_typst_to_docx_with_json(self, mock_run: MagicMock, mock_check: MagicMock, tmp_path: Path) -> None:
        """Test that .typ.json is created when json_content is provided."""
        mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")

        json_str = json.dumps({
            "children": [
                {
                    "typst_type": "TypstSection",
                    "heading": {"text": "Report", "typst_type": "TypstHeading"},
                    "body": [],
                    "subsections": []
                }
            ]
        })

        typ_path = tmp_path / "report.typ"
        typ_path.write_text("= Report", encoding="utf-8")

        result = compile_typst_to_docx(typ_path, tmp_path, json_content=json_str)

        assert result.suffix == ".docx"
        json_path = typ_path.with_suffix(".typ.json")
        assert json_path.read_text(encoding="utf-8") == json_str
        mock_check.assert_called_once()
        mock_run.assert_called_once()

    @patch("typst_ir.renderer._check_pandoc")
    @patch("typst_ir.renderer.subprocess.run")
    def test_compile_typst_to_docx_without_json(self, mock_run: MagicMock, mock_check: MagicMock, tmp_path: Path) -> None:
        """Test that no .typ.json is created when json_content is None."""
        mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")

        typ_path = tmp_path / "report.typ"
        typ_path.write_text("= Report", encoding="utf-8")

        result = compile_typst_to_docx(typ_path, tmp_path, json_content=None)

        assert result.suffix == ".docx"
        json_path = typ_path.with_suffix(".typ.json")
        assert not json_path.exists()
        mock_check.assert_called_once()
        mock_run.assert_called_once()
