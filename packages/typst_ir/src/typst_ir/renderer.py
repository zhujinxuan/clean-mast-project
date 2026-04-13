"""Typst IR renderer - convert JSON IR to Typst markup and compile to PDF/DOCX.

Provides high-level functions to render Typst IR documents from JSON input
to various output formats including Typst markup, PDF, and DOCX.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from typst_ir.nodes import TypstDocument
from typst_ir.serializer import serialize


def render_to_typst(json_str: str) -> str:
    """Render JSON IR input to Typst markup string.

    Parses the JSON string into a TypstDocument IR tree and serializes
    it to valid Typst markup that can be compiled with the typst CLI.

    Args:
        json_str: JSON string representing a TypstDocument IR tree

    Returns:
        Valid Typst markup string

    Raises:
        ValueError: If JSON parsing fails or produces invalid IR

    Example:
        >>> json_str = '{"children": [{"heading": {"text": "Hello"}, "body": [], "subsections": []}]}'
        >>> markup = render_to_typst(json_str)
        >>> assert '= Hello' in markup
    """
    doc = TypstDocument.model_validate_json(json_str)
    return serialize(doc)


def render_to_pdf(json_str: str, output_dir: Path) -> Path:
    """Render JSON IR input to PDF file.

    Convenience wrapper that writes the serialized Typst markup to
    ``output_dir / "report.typ"`` and compiles it to PDF.

    Args:
        json_str: JSON string representing a TypstDocument IR tree
        output_dir: Directory where the PDF will be saved

    Returns:
        Path to the generated PDF file

    Raises:
        RuntimeError: If typst CLI is not installed or compilation fails
        ValueError: If JSON parsing fails

    Example:
        >>> json_str = '{"children": [{"heading": {"text": "Report"}, "body": [], "subsections": []}]}'
        >>> pdf_path = render_to_pdf(json_str, Path("./output"))
        >>> assert pdf_path.suffix == ".pdf"
    """
    doc = TypstDocument.model_validate_json(json_str)
    typst_markup = serialize(doc)

    output_dir.mkdir(parents=True, exist_ok=True)
    typ_path = output_dir / "report.typ"
    typ_path.write_text(typst_markup, encoding="utf-8")

    json_path = typ_path.with_suffix(".typ.json")
    json_path.write_text(json_str, encoding="utf-8")

    return compile_typst_to_pdf(typ_path, output_dir)


def render_to_docx(json_str: str, output_dir: Path) -> Path:
    """Render JSON IR input to DOCX file.

    Convenience wrapper that writes the serialized Typst markup to
    ``output_dir / "report.typ"`` and converts it to DOCX via pandoc.

    Args:
        json_str: JSON string representing a TypstDocument IR tree
        output_dir: Directory where the DOCX will be saved

    Returns:
        Path to the generated DOCX file

    Raises:
        RuntimeError: If pandoc is not installed or conversion fails
        ValueError: If JSON parsing fails

    Example:
        >>> json_str = '{"children": [{"heading": {"text": "Report"}, "body": [], "subsections": []}]}'
        >>> docx_path = render_to_docx(json_str, Path("./output"))
        >>> assert docx_path.suffix == ".docx"
    """
    doc = TypstDocument.model_validate_json(json_str)
    typst_markup = serialize(doc)

    output_dir.mkdir(parents=True, exist_ok=True)
    typ_path = output_dir / "report.typ"
    typ_path.write_text(typst_markup, encoding="utf-8")

    json_path = typ_path.with_suffix(".typ.json")
    json_path.write_text(json_str, encoding="utf-8")

    return compile_typst_to_docx(typ_path, output_dir)


def compile_typst_to_pdf(typ_path: Path, output_dir: Path, json_content: str | None = None) -> Path:
    """Compile an existing Typst file to PDF.

    Assumes ``typ_path`` already contains the desired Typst markup.
    The caller is responsible for writing the ``.typ`` source before
    invoking this function.

    Args:
        typ_path: Path to the existing .typ file to compile
        output_dir: Directory where the PDF will be saved
        json_content: Optional JSON content to write alongside the .typ file

    Returns:
        Path to the generated PDF file

    Raises:
        RuntimeError: If typst CLI is not installed or compilation fails
    """
    if json_content is not None:
        json_path = typ_path.with_suffix(".typ.json")
        json_path.write_text(json_content, encoding="utf-8")

    _check_typst_cli()

    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / "report.pdf"

    try:
        subprocess.run(
            ["typst", "compile", str(typ_path), str(pdf_path)],
            capture_output=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else "Unknown error"
        raise RuntimeError(f"Typst compilation failed: {error_msg}")

    return pdf_path


def compile_typst_to_docx(typ_path: Path, output_dir: Path, json_content: str | None = None) -> Path:
    """Convert an existing Typst file to DOCX using pandoc.

    Assumes ``typ_path`` already contains the desired Typst markup.
    The caller is responsible for writing the ``.typ`` source before
    invoking this function.

    Args:
        typ_path: Path to the existing .typ file to convert
        output_dir: Directory where the DOCX will be saved
        json_content: Optional JSON content to write alongside the .typ file

    Returns:
        Path to the generated DOCX file

    Raises:
        RuntimeError: If pandoc is not installed or conversion fails
    """
    if json_content is not None:
        json_path = typ_path.with_suffix(".typ.json")
        json_path.write_text(json_content, encoding="utf-8")

    _check_pandoc()

    output_dir.mkdir(parents=True, exist_ok=True)
    docx_path = output_dir / "report.docx"

    try:
        result = subprocess.run(
            [
                "pandoc",
                typ_path.name,
                "-o", docx_path.name,
                "-f", "typst",
                "-t", "docx"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=300,
            cwd=typ_path.parent
        )

        if result.returncode != 0:
            error_msg = result.stderr.decode("utf-8", errors="replace") if result.stderr else "Unknown error"
            raise RuntimeError(f"DOCX conversion failed: {error_msg}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("DOCX conversion timed out after 300 seconds")

    return docx_path


def _check_typst_cli() -> None:
    """Check if typst CLI is installed.

    Raises:
        RuntimeError: If typst CLI is not found
    """
    try:
        subprocess.run(
            ["typst", "--version"],
            capture_output=True,
            check=True
        )
    except FileNotFoundError:
        raise RuntimeError(
            "Typst CLI not found. PDF generation requires typst.\n"
            "Install from: https://github.com/typst/typst/releases\n"
            "  macOS: brew install typst\n"
            "  Linux: Download binary from GitHub\n"
            "  Windows: winget install Typst.Typst"
        )


def _check_pandoc() -> None:
    """Check if pandoc is installed.

    Raises:
        RuntimeError: If pandoc is not found
    """
    if not shutil.which("pandoc"):
        raise RuntimeError(
            "pandoc not found in PATH. DOCX generation requires pandoc.\n"
            "Install from: https://pandoc.org/installing.html\n"
            "  Ubuntu/Debian: sudo apt-get install pandoc\n"
            "  macOS: brew install pandoc\n"
            "  Windows: choco install pandoc or winget install JohnMacFarlane.Pandoc"
        )
