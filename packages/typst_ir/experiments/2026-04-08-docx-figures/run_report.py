#!/usr/bin/env python3
"""Run report generation with DOCX enabled to test figure embedding.

This script runs the cleanmast report timeseries command WITHOUT --no-docx
to generate a DOCX file with embedded figures (if pandoc supports it).
"""

import subprocess
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
TEST_DATA_DIR = PROJECT_ROOT / "test-data" / "cleanmast" / "kp-202603-report"
CONFIG_FILE = TEST_DATA_DIR / "rep-ts-report.toml"
OUTPUT_DIR = TEST_DATA_DIR / "rep-ts"


def main():
    print("=" * 60)
    print("Running report generation WITH DOCX enabled")
    print("=" * 60)
    
    # Clean previous output
    if OUTPUT_DIR.exists():
        import shutil
        shutil.rmtree(OUTPUT_DIR)
        print(f"Cleaned previous output: {OUTPUT_DIR}")
    
    # Run the report generation
    cmd = [
        "uv", "run", "cleanmast", "report", "timeseries",
        str(CONFIG_FILE),
        # Note: NOT using --no-docx, so DOCX will be generated
    ]
    
    print(f"\nCommand: {' '.join(cmd)}")
    print(f"Working directory: {TEST_DATA_DIR}")
    print()
    
    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    if result.returncode != 0:
        print(f"\n❌ Command failed with return code {result.returncode}")
        sys.exit(1)
    
    # Check outputs
    print("\n" + "=" * 60)
    print("Checking outputs")
    print("=" * 60)
    
    pdf_path = OUTPUT_DIR / "report.pdf"
    docx_path = OUTPUT_DIR / "report.docx"
    typ_path = OUTPUT_DIR / "report.typ"
    json_path = OUTPUT_DIR / "report.typ.json"
    
    for path in [pdf_path, docx_path, typ_path, json_path]:
        if path.exists():
            size = path.stat().st_size
            print(f"✓ {path.name}: {size:,} bytes")
        else:
            print(f"✗ {path.name}: NOT FOUND")
    
    if docx_path.exists():
        print(f"\n✓ DOCX generated successfully: {docx_path}")
        print(f"  Size: {docx_path.stat().st_size:,} bytes")
        return str(docx_path)
    else:
        print("\n❌ DOCX not generated")
        sys.exit(1)


if __name__ == "__main__":
    docx_path = main()
    print(f"\nDOCX_PATH={docx_path}")