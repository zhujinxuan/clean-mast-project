"""Structural harness for the reporting domain.

DDD structure defined in ``subdomains/spec.md``.
"""

from pathlib import Path

REPORTING_ROOT = Path(__file__).resolve().parents[2] / "src" / "cleanmast" / "subdomains" / "reporting"

FORBIDDEN_DIRS = [
    REPORTING_ROOT / "domain",
    REPORTING_ROOT / "shared",
    REPORTING_ROOT / "application",
    REPORTING_ROOT / "infrastructure",
]

PIPELINE_STAGE_PATHS = [
    REPORTING_ROOT / "model",
    REPORTING_ROOT / "protocols",
    REPORTING_ROOT / "compute",
    REPORTING_ROOT / "assemble",
    REPORTING_ROOT / "render",
    REPORTING_ROOT / "api.py",
    REPORTING_ROOT / "subdomains",
]


def _iter_reporting_py_files(exclude_subdomains: bool = True) -> list[Path]:
    """Return all .py files under the reporting root, optionally excluding subdomains/."""
    files: list[Path] = []
    for py_file in REPORTING_ROOT.rglob("*.py"):
        if exclude_subdomains and "subdomains" in py_file.parts:
            continue
        files.append(py_file)
    return sorted(files)


def test_no_forbidden_directories() -> None:
    """Flat contexts must not contain domain/, shared/, application/, or infrastructure/."""
    existing = [str(d.relative_to(REPORTING_ROOT)) for d in FORBIDDEN_DIRS if d.exists()]
    assert not existing, f"Forbidden directories still exist: {existing}"


def test_pipeline_stage_dirs() -> None:
    """The flat pipeline-stage structure must be present."""
    missing = [str(p.relative_to(REPORTING_ROOT)) for p in PIPELINE_STAGE_PATHS if not p.exists()]
    assert not missing, f"Missing pipeline stage paths: {missing}"
