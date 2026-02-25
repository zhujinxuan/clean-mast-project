"""Tests for report compilation functions."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cleanmast.report.compiler import compile_typst_to_docx, compile_typst_to_pdf


class TestCompileTypstToPdf:
    """Tests for compile_typst_to_pdf function."""

    def test_compile_typst_to_pdf_success(self, tmp_path: Path):
        """Test successful PDF compilation with mocked subprocess."""
        typ_path = tmp_path / "report.typ"
        typ_path.write_text("#test content")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = compile_typst_to_pdf(typ_path, output_dir)

        assert result == output_dir / "report.pdf"
        assert mock_run.call_count == 2
        # First call: check typst --version
        assert mock_run.call_args_list[0][0][0] == ["typst", "--version"]
        # Second call: compile
        assert mock_run.call_args_list[1][0][0] == [
            "typst",
            "compile",
            str(typ_path),
            str(output_dir / "report.pdf"),
        ]

    def test_compile_typst_to_pdf_typst_not_installed(self, tmp_path: Path):
        """Test RuntimeError when typst CLI is not installed."""
        typ_path = tmp_path / "report.typ"
        typ_path.write_text("#test content")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("typst not found")

            with pytest.raises(RuntimeError, match="Typst CLI not found"):
                compile_typst_to_pdf(typ_path, output_dir)

    def test_compile_typst_to_pdf_compile_error(self, tmp_path: Path):
        """Test RuntimeError when compilation fails."""
        typ_path = tmp_path / "report.typ"
        typ_path.write_text("#test content")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            # First call (version check) succeeds
            # Second call (compile) fails
            def side_effect(*args, **kwargs):
                if args[0] == ["typst", "--version"]:
                    return MagicMock(returncode=0)
                else:
                    error = subprocess.CalledProcessError(
                        returncode=1,
                        cmd=["typst", "compile"],
                        stderr=b"Compilation syntax error",
                    )
                    raise error

            mock_run.side_effect = side_effect

            with pytest.raises(RuntimeError, match="Typst compilation failed"):
                compile_typst_to_pdf(typ_path, output_dir)


class TestCompileTypstToDocx:
    """Tests for compile_typst_to_docx function."""

    def test_compile_typst_to_docx_success(self, tmp_path: Path):
        """Test successful DOCX conversion with mocked typ2docx."""
        typ_path = tmp_path / "report.typ"
        typ_path.write_text("#test content")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_typ2docx = MagicMock()
        mock_typ2docx.convert = MagicMock()

        with patch.dict(sys.modules, {"typ2docx": mock_typ2docx}):
            result = compile_typst_to_docx(typ_path, output_dir)

        assert result == output_dir / "report.docx"
        mock_typ2docx.convert.assert_called_once_with(
            input_path=str(typ_path),
            output_path=str(output_dir / "report.docx"),
        )

    def test_compile_typst_to_docx_import_error(self, tmp_path: Path):
        """Test ImportError when typ2docx is not installed."""
        typ_path = tmp_path / "report.typ"
        typ_path.write_text("#test content")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Simulate typ2docx not being installed by removing it from sys.modules
        # and making __import__ raise ImportError
        modules_without_typ2docx = {
            k: v for k, v in sys.modules.items() if k != "typ2docx"
        }

        with patch.dict(sys.modules, modules_without_typ2docx, clear=True):
            with pytest.raises(ImportError, match="typ2docx not installed"):
                compile_typst_to_docx(typ_path, output_dir)
