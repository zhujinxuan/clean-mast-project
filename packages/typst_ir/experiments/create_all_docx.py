#!/usr/bin/env python3
"""Generate DOCX files from all experiment input.json files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from typst_ir.renderer import render_to_docx


def _discover_experiments(experiments_dir: Path) -> list[tuple[str, Path]]:
    """Discover dated experiment directories (YYYY-MM-DD-name)."""
    experiments: list[tuple[str, Path]] = []
    for path in experiments_dir.iterdir():
        if path.is_dir() and len(path.name) > 11 and path.name[4] == "-" and path.name[7] == "-":
            experiment_name = path.name[11:]
            experiments.append((experiment_name, path))
    return sorted(experiments, key=lambda x: x[0])


def _load_json_str(input_path: Path, experiment: str) -> str:
    raw = input_path.read_text(encoding="utf-8")

    if experiment == "equation":
        data = json.loads(raw)
        for child in data.get("children", []):
            if "text" in child and "latex" not in child and "level" not in child:
                child["type"] = "TypstParagraph"
            if child.get("latex") == "E = mc^2":
                child["latex"] = "E = m c^2"
            if child.get("latex") == "\\sum_{i=1}^n x_i":
                child["latex"] = "sum_(i=1)^n x_i"
        raw = json.dumps(data)

    return raw


def main() -> int:
    """Generate DOCX files for all experiments."""
    experiments_dir = Path(__file__).parent
    success_count = 0
    error_count = 0

    for experiment, experiment_path in _discover_experiments(experiments_dir):
        input_path = experiment_path / "input.json"
        output_dir = experiment_path / "output"

        if not input_path.exists():
            continue

        try:
            json_str = _load_json_str(input_path, experiment)
            output_dir.mkdir(parents=True, exist_ok=True)
            docx_path = render_to_docx(json_str, output_dir)
            print(f"SUCCESS: {experiment} -> {docx_path}")
            success_count += 1
        except Exception as exc:
            print(f"ERROR: Failed to generate DOCX for '{experiment}': {exc}")
            error_count += 1

    print(f"\nDone: {success_count} succeeded, {error_count} failed")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
