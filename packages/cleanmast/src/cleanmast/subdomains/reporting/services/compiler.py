"""Report compilation utilities.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service Layer ✓ | Compiler Pattern ✓
"""

import subprocess
from pathlib import Path


def compile_typst_to_pdf(typ_path: Path, output_dir: Path) -> Path:
    """Compile Typst file to PDF using typst CLI.

    Args:
        typ_path: Path to the .typ file to compile
        output_dir: Directory where the PDF will be saved

    Returns:
        Path to the generated PDF file

    Raises:
        RuntimeError: If typst CLI is not installed or compilation fails
    """
    # Check if typst CLI is installed
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

    # Determine output path
    pdf_path = output_dir / "report.pdf"

    # Compile the typst file
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


def compile_typst_to_docx(typ_path: Path, output_dir: Path) -> Path:
    """Compile Typst file to DOCX using typ2docx.

    Args:
        typ_path: Path to the .typ file to compile
        output_dir: Directory where the DOCX will be saved

    Returns:
        Path to the generated DOCX file

    Raises:
        ImportError: If typ2docx is not installed
        RuntimeError: If conversion fails
    """
    # Try to import typ2docx
    try:
        import typ2docx  # type: ignore
    except ImportError:
        raise ImportError(
            "typ2docx not installed. Install with: pip install typ2docx"
        )

    # Determine output path
    docx_path = output_dir / "report.docx"

    # Convert the typst file
    try:
        typ2docx.convert(
            input_path=str(typ_path),
            output_path=str(docx_path)
        )
    except Exception as e:
        raise RuntimeError(f"DOCX conversion failed: {e}")

    return docx_path
