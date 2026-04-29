"""Tests for report compilation functions."""

from pathlib import Path
from unittest.mock import patch

import pytest
from cleanmast.subdomains.assessment.infrastructure import AssessmentReportBuilder


class TestBuildCompilation:
    """Tests for compilation via the build() method."""

    def test_build_success(self, tmp_path: Path):
        """Test successful compilation through build()."""
        output_dir = tmp_path / "output"

        builder = AssessmentReportBuilder("Test Report", output_dir)

        with (
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.compile_typst_to_pdf"
            ) as mock_pdf,
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.draft_docx"
            ) as mock_draft,
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.polish_docx"
            ) as mock_polish,
        ):
            mock_pdf.side_effect = (
                lambda *args, **kwargs: output_dir / "report.pdf"
            )
            mock_draft.side_effect = (
                lambda *args, **kwargs: output_dir / "report_draft.docx"
            )
            mock_polish.side_effect = (
                lambda *args, **kwargs: output_dir / "report.docx"
            )

            results = builder.build()

        assert results["typ"] == output_dir / "report.typ"
        assert results["pdf"] == output_dir / "report.pdf"
        assert results["docx"] == output_dir / "report.docx"
        mock_pdf.assert_called_once()
        mock_draft.assert_called_once()
        mock_polish.assert_called_once()

    def test_build_pdf_failure_raises_error(self, tmp_path: Path):
        """Test that PDF compilation failure raises RuntimeError."""
        output_dir = tmp_path / "output"

        builder = AssessmentReportBuilder("Test Report", output_dir)

        with (
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.compile_typst_to_pdf"
            ) as mock_pdf,
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.draft_docx"
            ),
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.polish_docx"
            ),
        ):
            mock_pdf.side_effect = RuntimeError("Typst CLI failed")

            with pytest.raises(RuntimeError, match="PDF generation failed"):
                builder.build()

    def test_build_docx_draft_failure_raises_error(self, tmp_path: Path):
        """Test that DOCX draft generation failure raises RuntimeError."""
        output_dir = tmp_path / "output"

        builder = AssessmentReportBuilder("Test Report", output_dir)

        with (
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.compile_typst_to_pdf"
            ) as mock_pdf,
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.draft_docx"
            ) as mock_draft,
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.polish_docx"
            ),
        ):
            mock_pdf.side_effect = (
                lambda *args, **kwargs: output_dir / "report.pdf"
            )
            mock_draft.side_effect = RuntimeError("DOCX draft failed")

            with pytest.raises(RuntimeError, match="DOCX draft generation failed"):
                builder.build()

    def test_build_docx_polish_failure_raises_error(self, tmp_path: Path):
        """Test that DOCX polish failure raises RuntimeError."""
        output_dir = tmp_path / "output"

        builder = AssessmentReportBuilder("Test Report", output_dir)

        with (
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.compile_typst_to_pdf"
            ) as mock_pdf,
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.draft_docx"
            ) as mock_draft,
            patch(
                "cleanmast.subdomains.assessment.infrastructure.report_builder.polish_docx"
            ) as mock_polish,
        ):
            mock_pdf.side_effect = (
                lambda *args, **kwargs: output_dir / "report.pdf"
            )
            mock_draft.side_effect = (
                lambda *args, **kwargs: output_dir / "report_draft.docx"
            )
            mock_polish.side_effect = RuntimeError("DOCX polish failed")

            with pytest.raises(RuntimeError, match="DOCX polish failed"):
                builder.build()
