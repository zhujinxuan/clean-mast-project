"""Report compilation utilities."""

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


