"""Tests for report compilation functions."""

from pathlib import Path
from unittest.mock import patch

import pytest
from cleanmast.subdomains.assessment.infrastructure import AssessmentReportBuilder


class TestBuildPdf:
    """Tests for PDF compilation via the build() method."""

    def test_build_pdf_success(self, tmp_path: Path):
        """Test successful PDF compilation through build()."""
        output_dir = tmp_path / "output"

        builder = AssessmentReportBuilder("Test Report", output_dir)

        with (
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.compile_typst_to_pdf"
            ) as mock_compile_pdf,
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.compile_typst_to_docx"
            ) as mock_compile_docx,
        ):
            mock_compile_pdf.side_effect = (
                lambda *args, **kwargs: output_dir / "report.pdf"
            )
            mock_compile_docx.side_effect = (
                lambda *args, **kwargs: output_dir / "report.docx"
            )

            results = builder.build(compile_pdf=True, compile_docx=True)

        assert results["pdf"] == output_dir / "report.pdf"
        assert results["typ"] == output_dir / "report.typ"
        mock_compile_pdf.assert_called_once()

    def test_build_pdf_disabled(self, tmp_path: Path):
        """Test that PDF compilation can be disabled."""
        output_dir = tmp_path / "output"

        builder = AssessmentReportBuilder("Test Report", output_dir)

        with (
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.compile_typst_to_pdf"
            ) as mock_compile_pdf,
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.compile_typst_to_docx"
            ) as mock_compile_docx,
        ):
            mock_compile_docx.side_effect = (
                lambda *args, **kwargs: output_dir / "report.docx"
            )

            results = builder.build(compile_pdf=False, compile_docx=True)

        assert "pdf" not in results
        mock_compile_pdf.assert_not_called()
        assert "docx" in results

    def test_build_pdf_failure_raises_error(self, tmp_path: Path):
        """Test that PDF compilation failure raises RuntimeError."""
        output_dir = tmp_path / "output"

        builder = AssessmentReportBuilder("Test Report", output_dir)

        with patch(
            "cleanmast.subdomains.assessment.infrastructure.report_builder.compile_typst_to_pdf"
        ) as mock_compile_pdf:
            mock_compile_pdf.side_effect = RuntimeError("Typst CLI failed")

            with pytest.raises(RuntimeError, match="PDF generation failed"):
                builder.build(compile_pdf=True, compile_docx=False)
