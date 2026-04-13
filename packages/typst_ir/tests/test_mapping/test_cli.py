"""Tests for CLI commands in typst_ir.mapping.cli.

Tests the export-mapping command that orchestrates loading IR,
building mapping, and exporting to JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from click.testing import CliRunner
from docx import Document as DocxDocument
from typst_ir import TypstDocument, TypstHeading, TypstParagraph, TypstSection
from typst_ir.mapping.cli import main

if TYPE_CHECKING:
    pass


class TestMainCommand:
    """Test the main CLI group."""

    def test_main_help(self) -> None:
        """Main command should show help with available commands."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Typst IR" in result.output
        assert "export-mapping" in result.output

    def test_main_version(self) -> None:
        """Main command should show version."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestExportMappingCommand:
    """Test the export-mapping subcommand."""

    def test_export_mapping_help(self) -> None:
        """export-mapping should show help with all options."""
        runner = CliRunner()
        result = runner.invoke(main, ["export-mapping", "--help"])

        assert result.exit_code == 0
        assert "--ir-json" in result.output
        assert "--docx" in result.output
        assert "--output" in result.output
        assert "--log-level" in result.output

    def test_export_mapping_missing_ir_json(self, tmp_path: Path) -> None:
        """export-mapping should fail without --ir-json."""
        runner = CliRunner()

        # Create dummy files for other required options
        docx_path = tmp_path / "test.docx"
        DocxDocument().save(str(docx_path))
        ir_json = tmp_path / "ir.json"
        doc = TypstDocument(children=[TypstSection(heading=TypstHeading(text=""), body=[TypstParagraph(text="Test")], subsections=[])])
        ir_json.write_text(doc.model_dump_json(), encoding="utf-8")

        result = runner.invoke(
            main,
            [
                "export-mapping",
                "--docx", str(docx_path),
                "--output", str(tmp_path / "out.json"),
            ],
        )

        assert result.exit_code != 0
        assert "--ir-json" in result.output or "Missing option" in result.output or "required" in result.output.lower()

    def test_export_mapping_missing_docx(self, tmp_path: Path) -> None:
        """export-mapping should fail without --docx."""
        runner = CliRunner()

        # Create dummy IR file
        ir_json = tmp_path / "ir.json"
        doc = TypstDocument(children=[TypstSection(heading=TypstHeading(text=""), body=[TypstParagraph(text="Test")], subsections=[])])
        ir_json.write_text(doc.model_dump_json(), encoding="utf-8")

        result = runner.invoke(
            main,
            [
                "export-mapping",
                "--ir-json", str(ir_json),
                "--output", str(tmp_path / "out.json"),
            ],
        )

        assert result.exit_code != 0
        assert "--docx" in result.output or "Missing option" in result.output or "required" in result.output.lower()

    def test_export_mapping_missing_output(self, tmp_path: Path) -> None:
        """export-mapping should fail without --output."""
        runner = CliRunner()

        # Create dummy files
        ir_json = tmp_path / "ir.json"
        doc = TypstDocument(children=[TypstSection(heading=TypstHeading(text=""), body=[TypstParagraph(text="Test")], subsections=[])])
        ir_json.write_text(doc.model_dump_json(), encoding="utf-8")
        docx_path = tmp_path / "test.docx"
        DocxDocument().save(str(docx_path))

        result = runner.invoke(
            main,
            [
                "export-mapping",
                "--ir-json", str(ir_json),
                "--docx", str(docx_path),
            ],
        )

        assert result.exit_code != 0
        assert "--output" in result.output or "Missing option" in result.output or "required" in result.output.lower()

    def test_export_mapping_nonexistent_ir_json(self) -> None:
        """export-mapping should fail if IR JSON doesn't exist."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "export-mapping",
                    "--ir-json", "nonexistent.json",
                    "--docx", "test.docx",
                    "--output", "out.json",
                ],
            )

            assert result.exit_code != 0
            assert "does not exist" in result.output or "Invalid value" in result.output

    def test_export_mapping_nonexistent_docx(self) -> None:
        """export-mapping should fail if DOCX doesn't exist."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create IR JSON file
            doc = TypstDocument(children=[TypstSection(heading=TypstHeading(text=""), body=[TypstParagraph(text="Test")], subsections=[])])
            Path("ir.json").write_text(doc.model_dump_json(), encoding="utf-8")

            result = runner.invoke(
                main,
                [
                    "export-mapping",
                    "--ir-json", "ir.json",
                    "--docx", "nonexistent.docx",
                    "--output", "out.json",
                ],
            )

            assert result.exit_code != 0
            assert "does not exist" in result.output or "Invalid value" in result.output

    def test_export_mapping_success(self, tmp_path: Path) -> None:
        """export-mapping should succeed with valid inputs."""
        runner = CliRunner()

        # Create IR JSON file
        ir_json = tmp_path / "ir.json"
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[TypstParagraph(text="Content")],
                    subsections=[],
                ),
            ]
        )
        ir_json.write_text(doc.model_dump_json(), encoding="utf-8")

        # Create minimal DOCX file (just PK header)
        docx_path = tmp_path / "test.docx"
        DocxDocument().save(str(docx_path))

        # Output path
        output_path = tmp_path / "mapping.json"

        result = runner.invoke(
            main,
            [
                "export-mapping",
                "--ir-json", str(ir_json),
                "--docx", str(docx_path),
                "--output", str(output_path),
                "--no-inject",
            ],
        )

        assert result.exit_code == 0, f"Output: {result.output}"
        assert "Loading IR" in result.output
        assert "Building mapping" in result.output
        assert "Exporting mapping" in result.output
        assert "✓ Mapping exported successfully" in result.output
        assert output_path.exists()

    def test_export_mapping_with_log_level(self, tmp_path: Path) -> None:
        runner = CliRunner()

        ir_json = tmp_path / "ir.json"
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[TypstParagraph(text="Content")],
                    subsections=[],
                ),
            ]
        )
        ir_json.write_text(doc.model_dump_json(), encoding="utf-8")

        docx_path = tmp_path / "test.docx"
        DocxDocument().save(str(docx_path))

        output_path = tmp_path / "mapping.json"

        result = runner.invoke(
            main,
            [
                "export-mapping",
                "--ir-json", str(ir_json),
                "--docx", str(docx_path),
                "--output", str(output_path),
                "--log-level", "ERROR",
                "--no-inject",
            ],
        )

        assert result.exit_code == 0, f"Output: {result.output}"
        assert output_path.exists()

    def test_export_mapping_output_content(self, tmp_path: Path) -> None:
        """export-mapping should produce valid JSON with correct structure."""
        runner = CliRunner()

        # Create IR JSON file
        ir_json = tmp_path / "ir.json"
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[TypstParagraph(text="Content")],
                    subsections=[],
                ),
            ]
        )
        ir_json.write_text(doc.model_dump_json(), encoding="utf-8")

        # Create minimal DOCX file
        docx_path = tmp_path / "test.docx"
        DocxDocument().save(str(docx_path))

        # Output path
        output_path = tmp_path / "mapping.json"

        result = runner.invoke(
            main,
            [
                "export-mapping",
                "--ir-json", str(ir_json),
                "--docx", str(docx_path),
                "--output", str(output_path),
                "--no-inject",
            ],
        )

        assert result.exit_code == 0

        # Verify JSON structure
        mapping_data = json.loads(output_path.read_text(encoding="utf-8"))
        assert "version" in mapping_data
        assert "full_hash" in mapping_data
        assert "entries" in mapping_data
        assert "path_index" in mapping_data
        assert mapping_data["version"] == "1.0.0"
        assert isinstance(mapping_data["full_hash"], str)
        assert isinstance(mapping_data["entries"], dict)
        assert isinstance(mapping_data["path_index"], dict)

    def test_export_mapping_creates_parent_directories(self, tmp_path: Path) -> None:
        """export-mapping should create parent directories for output."""
        runner = CliRunner()

        # Create IR JSON file
        ir_json = tmp_path / "ir.json"
        doc = TypstDocument(children=[TypstSection(heading=TypstHeading(text=""), body=[TypstParagraph(text="Test")], subsections=[])])
        ir_json.write_text(doc.model_dump_json(), encoding="utf-8")

        # Create minimal DOCX file
        docx_path = tmp_path / "test.docx"
        DocxDocument().save(str(docx_path))

        # Output path in nested directory
        output_path = tmp_path / "nested" / "deep" / "mapping.json"

        result = runner.invoke(
            main,
            [
                "export-mapping",
                "--ir-json", str(ir_json),
                "--docx", str(docx_path),
                "--output", str(output_path),
                "--no-inject",
            ],
        )

        assert result.exit_code == 0
        assert output_path.exists()

    def test_export_mapping_complex_document(self, tmp_path: Path) -> None:
        """export-mapping should handle complex documents with sections and lists."""
        runner = CliRunner()

        # Create complex IR JSON file
        ir_json = tmp_path / "ir.json"
        from typst_ir import TypstBulletList, TypstEquation, TypstSection, TypstTable

        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Document Title"),
                    body=[],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Equation"),
                    body=[TypstEquation(latex="E = mc^2")],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Section 1"),
                    body=[
                        TypstEquation(latex="F = ma"),
                        TypstBulletList(
                            items=[
                                [TypstEquation(latex="x = 1")],
                                [TypstEquation(latex="y = 2")],
                            ]
                        ),
                    ],
                    subsections=[],
                ),
                TypstSection(
                    heading=TypstHeading(text="Table"),
                    body=[TypstTable(
                        headers=["A", "B"],
                        data=[["1", "2"]],
                    )],
                    subsections=[],
                ),
            ]
        )
        ir_json.write_text(doc.model_dump_json(), encoding="utf-8")

        # Create minimal DOCX file
        docx_path = tmp_path / "test.docx"
        DocxDocument().save(str(docx_path))

        # Output path
        output_path = tmp_path / "mapping.json"

        result = runner.invoke(
            main,
            [
                "export-mapping",
                "--ir-json", str(ir_json),
                "--docx", str(docx_path),
                "--output", str(output_path),
                "--no-inject",
            ],
        )

        assert result.exit_code == 0

        # Verify mapping has entries for all node types
        mapping_data = json.loads(output_path.read_text(encoding="utf-8"))
        paths = list(mapping_data["entries"].keys())

        # Should have entries for all node types
        assert any("Heading" in p for p in paths), f"No Heading in paths: {paths}"
        assert any("Equation" in p for p in paths), f"No Equation in paths: {paths}"
        assert any("Section" in p for p in paths), f"No Section in paths: {paths}"
        assert any("BulletList" in p for p in paths), f"No BulletList in paths: {paths}"
        assert any("Table" in p for p in paths), f"No Table in paths: {paths}"

    def test_export_mapping_count_output(self, tmp_path: Path) -> None:
        """export-mapping should output correct entry count."""
        runner = CliRunner()

        # Create IR JSON file with known structure
        ir_json = tmp_path / "ir.json"
        doc = TypstDocument(
            children=[
                TypstSection(
                    heading=TypstHeading(text="Title"),
                    body=[
                        TypstParagraph(text="Para 1"),
                        TypstParagraph(text="Para 2"),
                    ],
                    subsections=[],
                ),
            ]
        )
        ir_json.write_text(doc.model_dump_json(), encoding="utf-8")

        # Create minimal DOCX file
        docx_path = tmp_path / "test.docx"
        DocxDocument().save(str(docx_path))

        # Output path
        output_path = tmp_path / "mapping.json"

        result = runner.invoke(
            main,
            [
                "export-mapping",
                "--ir-json", str(ir_json),
                "--docx", str(docx_path),
                "--output", str(output_path),
                "--no-inject",
            ],
        )

        assert result.exit_code == 0

        # Verify entry count in output message
        mapping_data = json.loads(output_path.read_text(encoding="utf-8"))
        entry_count = len(mapping_data["entries"])
        assert f"{entry_count} entries" in result.output
