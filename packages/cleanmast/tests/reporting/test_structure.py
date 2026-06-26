"""Structural harness for the reporting domain.

These tests verify that the reporting context follows the flat pipeline-stage
DDD structure defined in ``subdomains/spec.md``. They are intentionally written
to FAIL on the current codebase while assessment shims still exist; once the
shims are removed in later waves, the tests will pass.
"""

import ast
from pathlib import Path

import pytest

REPORTING_ROOT = (
    Path(__file__).parent.parent.parent
    / "src"
    / "cleanmast"
    / "subdomains"
    / "reporting"
)


ASSESSMENT_IMPORT_PREFIX = "cleanmast.subdomains.assessment"
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
]


def _iter_reporting_py_files(exclude_subdomains: bool = True) -> list[Path]:
    """Return all .py files under the reporting root, optionally excluding subdomains/."""
    files = sorted(REPORTING_ROOT.rglob("*.py"))
    if not exclude_subdomains:
        return files
    return [
        f
        for f in files
        if "subdomains" not in f.relative_to(REPORTING_ROOT).parts
    ]


def _is_assessment_import(node: ast.AST) -> bool:
    """True if the node is ``from cleanmast.subdomains.assessment... import ...``."""
    return (
        isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith(ASSESSMENT_IMPORT_PREFIX)
    )


def _is_all_export(node: ast.AST) -> bool:
    """True if the node is an ``__all__ = [...]`` assignment."""
    if not isinstance(node, ast.Assign):
        return False
    targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
    return targets == ["__all__"]


def _is_docstring(node: ast.AST) -> bool:
    """True if the node is a module-level string literal (docstring)."""
    if not isinstance(node, ast.Expr):
        return False
    value = node.value
    return isinstance(value, ast.Constant) and isinstance(value.value, str)


def _file_is_shim(path: Path) -> bool:
    """A shim re-exports assessment symbols and has no other meaningful code."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        pytest.fail(f"Syntax error in {path}: {exc}")

    has_assessment_import = False
    for node in tree.body:
        if _is_assessment_import(node):
            has_assessment_import = True
        elif _is_all_export(node) or _is_docstring(node):
            continue
        else:
            return False
    return has_assessment_import


def test_no_forbidden_directories() -> None:
    """Flat contexts must not contain domain/, shared/, application/, or infrastructure/."""
    existing = [str(d.relative_to(REPORTING_ROOT)) for d in FORBIDDEN_DIRS if d.exists()]
    assert not existing, f"Forbidden directories still exist: {existing}"


def test_no_shim_files() -> None:
    """No file outside subdomains/ should be a one-line assessment re-export shim."""
    shims = [str(f.relative_to(REPORTING_ROOT)) for f in _iter_reporting_py_files() if _file_is_shim(f)]
    assert not shims, f"Assessment shim files still exist: {shims}"


def test_pipeline_stage_dirs() -> None:
    """The flat pipeline-stage structure must be present."""
    missing = [str(p.relative_to(REPORTING_ROOT)) for p in PIPELINE_STAGE_PATHS if not p.exists()]
    assert not missing, f"Missing pipeline stage paths: {missing}"


def test_no_assessment_imports_in_reporting() -> None:
    """Reporting must never import from its sibling assessment context."""
    violations: list[str] = []
    for path in _iter_reporting_py_files(exclude_subdomains=False):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if _is_assessment_import(node):
                violations.append(str(path.relative_to(REPORTING_ROOT)))
                break
    assert not violations, f"Files importing from assessment: {violations}"
