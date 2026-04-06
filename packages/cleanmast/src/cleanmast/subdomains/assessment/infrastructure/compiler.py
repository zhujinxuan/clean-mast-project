"""Report compilation utilities.

ADR-GUARDRAILS: structure-001-subdomain-layout, ddd-s-001-services
Compliance: Subdomain layout ✓ | Service Layer ✓ | Compiler Pattern ✓
"""

import shutil
import subprocess
from pathlib import Path

from cleanmast.infrastructure.path_utils import to_posix_path


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
            ["typst", "compile", to_posix_path(typ_path), to_posix_path(pdf_path)],
            capture_output=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else "Unknown error"
        raise RuntimeError(f"Typst compilation failed: {error_msg}")

    return pdf_path


def compile_typst_to_docx(typ_path: Path, output_dir: Path) -> Path:
    """Compile Typst file to DOCX using pandoc.

    Args:
        typ_path: Path to the .typ file to compile
        output_dir: Directory where the DOCX will be saved

    Returns:
        Path to the generated DOCX file

    Raises:
        RuntimeError: If pandoc is not installed or conversion fails
    """
    # Check if pandoc is installed
    if not shutil.which("pandoc"):
        raise RuntimeError(
            "pandoc not found in PATH. DOCX generation requires pandoc.\n"
            "Install from: https://pandoc.org/installing.html\n"
            "  Ubuntu/Debian: sudo apt-get install pandoc\n"
            "  macOS: brew install pandoc\n"
            "  Windows: choco install pandoc or winget install JohnMacFarlane.Pandoc"
        )

    # Determine output path
    docx_path = output_dir / "report.docx"

    # Convert the typst file using pandoc
    try:
        result = subprocess.run(
            [
                "pandoc",
                str(typ_path),
                "-o", str(docx_path),
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
            error_msg = result.stderr.decode('utf-8', errors='replace') if result.stderr else "Unknown error"
            raise RuntimeError(f"DOCX conversion failed: {error_msg}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("DOCX conversion timed out after 300 seconds")

    return docx_path
