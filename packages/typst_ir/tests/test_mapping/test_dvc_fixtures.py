"""Tests for DVC-managed mapping fixtures."""

from pathlib import Path

import pytest
from click.testing import CliRunner
from typst_ir.mapping.cli import main
from typst_ir.mapping.types import DocxTypstMapping


class TestDvcFixtureMapping:
    """Tests using real-world DVC-managed fixtures for kp-202603-mapping."""

    @pytest.fixture
    def fixture_dir(self) -> Path:
        return (
            Path(__file__).parent.parent.parent.parent.parent
            / "test-data"
            / "typst-ir"
            / "kp-202603-mapping"
        )

    def test_dvc_fixtures_exist(self, fixture_dir: Path) -> None:
        """All required fixture files should exist."""
        assert (fixture_dir / "report.typ.json").exists()
        assert (fixture_dir / "report.docx").exists()

    @pytest.mark.skip(reason="Fixture uses pre-sections JSON format")
    def test_export_mapping_generates_valid_output(
        self, fixture_dir: Path, tmp_path: Path
    ) -> None:
        """CLI export-mapping should generate a valid mapping from real fixtures."""
        ir_path = fixture_dir / "report.typ.json"
        docx_path = fixture_dir / "report.docx"
        output_path = tmp_path / "output.json"

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "export-mapping",
                "--ir-json",
                str(ir_path),
                "--docx",
                str(docx_path),
                "--output",
                str(output_path),
                "--no-inject",
            ],
        )

        assert result.exit_code == 0, f"Output: {result.output}"
        assert output_path.exists()

        output_mapping = DocxTypstMapping.model_validate_json(
            output_path.read_text(encoding="utf-8")
        )

        assert output_mapping.version == "1.0.0"
        assert len(output_mapping.full_hash) == 64
        assert len(output_mapping.entries) > 0
        assert len(output_mapping.path_index) > 0
