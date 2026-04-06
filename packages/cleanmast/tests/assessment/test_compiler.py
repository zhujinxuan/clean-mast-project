"""Tests for report compilation functions."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cleanmast.subdomains.assessment.infrastructure import (
    compile_typst_to_pdf,
)


class TestCompileTypstToPdf:
    def test_compile_typst_to_pdf_success(self, tmp_path: Path):
        typ_path = tmp_path / "report.typ"
        typ_path.write_text("#test content")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = compile_typst_to_pdf(typ_path, output_dir)

        assert result == output_dir / "report.pdf"
        assert mock_run.call_count == 2

    def test_compile_typst_to_pdf_typst_not_installed(self, tmp_path: Path):
        typ_path = tmp_path / "report.typ"
        typ_path.write_text("#test content")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("typst not found")

            with pytest.raises(RuntimeError, match="Typst CLI not found"):
                compile_typst_to_pdf(typ_path, output_dir)
