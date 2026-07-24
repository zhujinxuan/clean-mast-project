#!/usr/bin/env python3
"""Baseline verification runner - executes verification checks and generates per-package timestamped baseline files.

Usage:
    uv run python scripts/verify_baseline.py                    # Run all checks, all packages
    uv run python scripts/verify_baseline.py --package cleanmast # Single package
    uv run python scripts/verify_baseline.py --skip dvc --skip pytest  # Skip checks
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Configuration
ERROR_THRESHOLD = 500  # Characters
PACKAGES_DIR = Path("packages")
BASELINE_REFS_DIR = "baseline-refs"


@dataclass
class CheckResult:
    """Result of a single verification check."""
    name: str
    status: str  # "PASS" or "FAIL"
    duration: float
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    summary_text: str = ""


@dataclass
class BaselineData:
    """Complete baseline data for a package."""
    package: str
    timestamp: str
    git_sha: str
    results: list[CheckResult]


def get_timestamp() -> str:
    """Generate ISO 8601 timestamp without colons for filename safety."""
    return datetime.now().strftime("%Y-%m-%dT%H%M%S")


def get_git_sha() -> str:
    """Get short git SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "unknown"


def discover_packages(package_filter: str | None = None) -> list[str]:
    """Discover all packages in the packages/ directory."""
    if not PACKAGES_DIR.exists():
        return []
    
    packages = []
    for item in sorted(PACKAGES_DIR.iterdir()):
        if item.is_dir() and (item / "pyproject.toml").exists():
            if package_filter is None or item.name == package_filter:
                packages.append(item.name)
    return packages


def run_check(
    name: str,
    cmd: list[str],
    cwd: Path | None = None,
    timeout: int = 300,
) -> CheckResult:
    """Run a subprocess check and capture results."""
    start = time.perf_counter()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
            errors="replace",
        )
        elapsed = time.perf_counter() - start
        
        return CheckResult(
            name=name,
            status="PASS" if result.returncode == 0 else "FAIL",
            duration=elapsed,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start
        return CheckResult(
            name=name,
            status="FAIL",
            duration=elapsed,
            exit_code=-1,
            stderr=f"Command timed out after {timeout}s",
        )
    except FileNotFoundError as e:
        elapsed = time.perf_counter() - start
        return CheckResult(
            name=name,
            status="FAIL",
            duration=elapsed,
            exit_code=-1,
            stderr=f"Command not found: {e}",
        )


def parse_pyright_output(result: CheckResult) -> CheckResult:
    """Parse pyright JSON output."""
    try:
        data = json.loads(result.stdout)
        diagnostics = data.get("generalDiagnostics", [])
        summary = data.get("summary", {})
        
        result.error_count = summary.get("errorCount", 0)
        result.warning_count = summary.get("warningCount", 0)
        
        for diag in diagnostics:
            entry = {
                "file": diag.get("file", "unknown"),
                "line": diag.get("range", {}).get("start", {}).get("line", 0),
                "message": diag.get("message", ""),
                "severity": diag.get("severity", "error"),
            }
            if entry["severity"] == "error":
                result.errors.append(entry)
            else:
                result.warnings.append(entry)
                
    except json.JSONDecodeError:
        result.stderr = result.stdout or "Failed to parse pyright output"
    
    return result


def parse_ast_grep_output(result: CheckResult) -> CheckResult:
    """Parse ast-grep JSON output."""
    try:
        data = json.loads(result.stdout)
        result.error_count = len(data)
        result.warning_count = 0

        for violation in data:
            entry = {
                "file": violation.get("file", "unknown"),
                "line": violation.get("range", {}).get("start", {}).get("line", 0) + 1,
                "message": violation.get("message", ""),
                "severity": violation.get("severity", "error"),
            }
            result.errors.append(entry)

    except json.JSONDecodeError:
        result.stderr = result.stdout or "Failed to parse ast-grep output"

    return result


def parse_lint_imports_output(result: CheckResult) -> CheckResult:
    """Parse lint-imports text output."""
    output = result.stdout + result.stderr
    
    match = re.search(r"Contracts:\s*(\d+)\s+kept,\s*(\d+)\s+broken", output)
    if match:
        kept = int(match.group(1))
        broken = int(match.group(2))
        result.error_count = broken
        result.warning_count = 0
        result.summary_text = f"Contracts: {kept} kept, {broken} broken"
    else:
        result.error_count = 1 if result.exit_code != 0 else 0
        result.warning_count = 0
        result.summary_text = (
            "Import lint violations detected"
            if result.exit_code != 0
            else "No import lint violations"
        )
    
    return result


def parse_ruff_output(result: CheckResult) -> CheckResult:
    """Parse ruff JSON output."""
    try:
        data = json.loads(result.stdout)
        result.error_count = len(data)
        result.warning_count = 0
        
        for violation in data:
            entry = {
                "file": violation.get("filename", "unknown"),
                "line": violation.get("location", {}).get("row", 0),
                "code": violation.get("code", ""),
                "message": violation.get("message", ""),
            }
            result.errors.append(entry)
            
    except json.JSONDecodeError:
        result.stderr = result.stdout or "Failed to parse ruff output"
    
    return result


def parse_pytest_output(result: CheckResult) -> CheckResult:
    """Parse pytest text output."""
    output = result.stdout + result.stderr
    
    passed = 0
    failed = 0
    errors = 0
    skipped = 0
    
    # Look for patterns like "X passed", "Y failed", "Z skipped"
    passed_match = re.search(r'(\d+)\s+passed', output)
    failed_match = re.search(r'(\d+)\s+failed', output)
    error_match = re.search(r'(\d+)\s+error', output)
    skipped_match = re.search(r'(\d+)\s+skipped', output)

    if passed_match:
        passed = int(passed_match.group(1))
    if failed_match:
        failed = int(failed_match.group(1))
    if error_match:
        errors = int(error_match.group(1))
    if skipped_match:
        skipped = int(skipped_match.group(1))

    result.error_count = failed + errors
    result.warning_count = 0
    result.summary_text = (
        f"Passed: {passed} | Failed: {failed} | Errors: {errors} | Skipped: {skipped}"
    )

    return result


def parse_dvc_verify_output(result: CheckResult) -> CheckResult:
    """Parse cleanmast verify --json output."""
    try:
        data = json.loads(result.stdout)
        summary = data.get("summary", {})
        datasets = data.get("datasets", [])
        
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        
        result.error_count = failed
        result.warning_count = 0
        result.summary_text = f"Datasets: {len(datasets)} | Passed: {passed} | Failed: {failed}"
        
        # Store dataset info for detailed output
        result.errors = [
            {
                "name": ds.get("name", ""),
                "status": ds.get("status", ""),
                "error": ds.get("error"),
                "duration_sec": ds.get("duration_sec", 0),
            }
            for ds in datasets
            if ds.get("status") == "fail"
        ]
        
        result.warnings = [
            {
                "name": ds.get("name", ""),
                "status": ds.get("status", ""),
                "duration_sec": ds.get("duration_sec", 0),
            }
            for ds in datasets
            if ds.get("status") == "pass"
        ]
        
    except json.JSONDecodeError:
        result.stderr = result.stdout or "Failed to parse dvc-verify output"
    
    return result


def run_ty_check(package: str) -> CheckResult:
    """Run ty type check for a package."""
    cmd = ["uv", "run", "ty", "check", f"packages/{package}", "--output-format", "full"]
    result = run_check("ty", cmd, timeout=180)
    # ty outputs text, so we count errors based on exit code
    result.error_count = 1 if result.exit_code != 0 else 0
    result.summary_text = "Type errors detected" if result.exit_code != 0 else "No type errors"
    return result


def run_ruff_check() -> CheckResult:
    """Run ruff lint check for all packages."""
    cmd = ["uv", "run", "ruff", "check", "packages/", "--output-format", "json"]
    result = run_check("ruff", cmd, timeout=60)
    return parse_ruff_output(result)


def run_pytest_check(package: str) -> CheckResult:
    """Run pytest for a package (parallel by default)."""
    workers = os.environ.get("PYTEST_XDIST_WORKERS", "4")
    cmd = [
        "uv", "run", "pytest", f"packages/{package}/tests",
        "-q", "--tb=short", "-n", workers,
    ]
    result = run_check("pytest", cmd, timeout=300)
    return parse_pytest_output(result)


def run_dvc_verify_check(package: str) -> CheckResult:
    """Run cleanmast verify --json for a package."""
    cmd = ["uv", "run", "cleanmast", "verify", "--json", "-p", package, "--jobs", "4"]
    result = run_check("dvc-verify", cmd, timeout=3600)
    return parse_dvc_verify_output(result)


def run_ast_grep_check(package: str) -> CheckResult:
    """Run ast-grep scan for a package.

    For cleanmast, scan the whole package source using shared .ast-grep/rules/.
    For other packages, fall back to package-specific sgconfig.yml.
    """
    if package == "cleanmast":
        target = "packages/cleanmast/src/cleanmast/"
        cmd = [
            "uv",
            "run",
            "ast-grep",
            "scan",
            "--json",
            "--config",
            ".ast-grep/sgconfig.yml",
            target,
        ]
        result = run_check("ast-grep", cmd, timeout=120)
        return parse_ast_grep_output(result)

    config_path = f"packages/{package}/sgconfig.yml"
    cmd = ["uv", "run", "ast-grep", "scan", "--json", "--config", config_path]
    result = run_check("ast-grep", cmd, timeout=120)
    return parse_ast_grep_output(result)


def run_lint_imports_check() -> CheckResult:
    """Run import-linter checks."""
    cmd = ["uv", "run", "lint-imports"]
    result = run_check("lint-imports", cmd, timeout=120)
    return parse_lint_imports_output(result)


def format_error_content(result: CheckResult) -> str:
    """Format error content for size checking."""
    if result.name == "ty":
        return result.stdout + result.stderr
    elif result.name == "ruff":
        return json.dumps(result.errors, indent=2)
    elif result.name == "pytest":
        return result.stdout + result.stderr
    elif result.name == "dvc-verify":
        return json.dumps(result.errors, indent=2)
    elif result.name == "ast-grep":
        return json.dumps(result.errors, indent=2)
    elif result.name == "lint-imports":
        return result.stdout + result.stderr
    return ""


def write_large_errors(
    package_dir: Path,
    timestamp: str,
    result: CheckResult,
) -> str | None:
    """Write large error output to separate file. Returns reference path if written."""
    error_content = format_error_content(result)
    
    if len(error_content) >= ERROR_THRESHOLD:
        refs_dir = package_dir / BASELINE_REFS_DIR
        refs_dir.mkdir(parents=True, exist_ok=True)
        
        # Use appropriate extension based on content type
        if result.name in ("pytest", "ty"):
            ref_filename = f"{timestamp}-{result.name}.txt"
            temp_suffix = ".txt"
        else:
            ref_filename = f"{timestamp}-{result.name}.json"
            temp_suffix = ".json"
        ref_path = refs_dir / ref_filename
        
        # Atomic write
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=temp_suffix,
            dir=refs_dir,
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(error_content)
            temp_path = f.name
        
        os.replace(temp_path, ref_path)
        
        return f"{BASELINE_REFS_DIR}/{ref_filename}"
    
    return None


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    return f"{seconds:.1f}s"


def generate_baseline_markdown(
    data: BaselineData,
    package_dir: Path,
) -> str:
    """Generate the baseline markdown content."""
    lines = [
        f"# Baseline: {data.package}",
        f"> Generated: {data.timestamp}",
        f"> Commit: {data.git_sha}",
        "",
        "## Summary",
        "| Check | Status | Duration | Errors | Warnings |",
        "|-------|--------|----------|--------|----------|",
    ]
    
    for result in data.results:
        status_emoji = "🟢" if result.status == "PASS" else "🔴"
        duration_str = format_duration(result.duration)
        error_count = result.error_count if result.error_count > 0 else 0
        warning_count = result.warning_count if result.warning_count > 0 else "-"
        lines.append(
            f"| {result.name} | {status_emoji} {result.status} | {duration_str} | {error_count} | {warning_count} |"
        )
    
    lines.extend(["", "## Details", ""])
    
    for result in data.results:
        lines.append(f"### {result.name}")
        lines.append(f"Status: {result.status}")
        
        # Check for large errors
        error_ref = write_large_errors(package_dir, data.timestamp, result)
        
        if error_ref:
            error_size = len(format_error_content(result))
            lines.append(f"Errors: See {error_ref} ({error_size:,} bytes)")
        elif result.errors:
            lines.append(f"Errors ({len(result.errors)}):")
            for error in result.errors[:10]:  # Limit to first 10
                if result.name == "ruff":
                    lines.append(f"- {error.get('file', '')}:{error.get('line', 0)} — {error.get('code', '')}: {error.get('message', '')}")
                elif result.name == "dvc-verify":
                    lines.append(f"- ❌ {error.get('name', '')}: {error.get('error', 'Unknown error')}")
            if len(result.errors) > 10:
                lines.append(f"- ... and {len(result.errors) - 10} more errors")
        
        if result.warnings and not error_ref:
            if result.name == "dvc-verify":
                lines.append(f"Datasets ({len(result.warnings)} found):")
                for ds in result.warnings[:10]:
                    lines.append(f"- ✅ {ds.get('name', '')} ({ds.get('duration_sec', 0):.1f}s)")
                if len(result.warnings) > 10:
                    lines.append(f"- ... and {len(result.warnings) - 10} more datasets")
        
        if result.summary_text:
            lines.append(result.summary_text)
        
        if result.stderr and not error_ref and not result.errors:
            lines.append(f"Output: {result.stderr[:200]}")
        
        lines.append("")
    
    return "\n".join(lines)


def run_verification(
    package: str,
    skip_checks: set[str],
) -> tuple[BaselineData, bool]:
    """Run all verification checks for a package. Returns (data, all_passed)."""
    timestamp = get_timestamp()
    git_sha = get_git_sha()
    
    results: list[CheckResult] = []
    all_passed = True
    
    print(f"\n📦 Running checks for package: {package}")
    print("=" * 50)
    
    # 1. Type check (ty)
    if "ty" not in skip_checks:
        print("  [ty] Running type check...", end=" ")
        result = run_ty_check(package)
        results.append(result)
        status = "✓" if result.status == "PASS" else "✗"
        print(f"{status} ({format_duration(result.duration)})")
        if result.status != "PASS":
            all_passed = False
    
    # 2. Lint (ruff) - runs once for all packages
    if "ruff" not in skip_checks and package == "cleanmast":  # Only run ruff once
        print("  [ruff] Running lint check...", end=" ")
        result = run_ruff_check()
        results.append(result)
        status = "✓" if result.status == "PASS" else "✗"
        print(f"{status} ({format_duration(result.duration)})")
        if result.status != "PASS":
            all_passed = False
    
    # 3. Tests (pytest)
    if "pytest" not in skip_checks:
        print("  [pytest] Running tests...", end=" ")
        result = run_pytest_check(package)
        results.append(result)
        status = "✓" if result.status == "PASS" else "✗"
        print(f"{status} ({format_duration(result.duration)})")
        if result.status != "PASS":
            all_passed = False
    
    # 4. DVC verify
    if "dvc" not in skip_checks:
        print("  [dvc-verify] Running dataset verification...", end=" ")
        result = run_dvc_verify_check(package)
        results.append(result)
        status = "✓" if result.status == "PASS" else "✗"
        print(f"{status} ({format_duration(result.duration)})")
        if result.status != "PASS":
            all_passed = False
    
    # 5. lint-imports (advisory / non-blocking)
    if "lint-imports" not in skip_checks and package == "cleanmast":
        print("  [lint-imports] Running import contract checks...", end=" ")
        result = run_lint_imports_check()
        results.append(result)
        status = "✓" if result.status == "PASS" else "✗"
        print(f"{status} ({format_duration(result.duration)})")
    
    # 6. ast-grep custom rules (advisory / non-blocking)
    if "ast-grep" not in skip_checks:
        print("  [ast-grep] Running custom rule checks...", end=" ")
        result = run_ast_grep_check(package)
        results.append(result)
        status = "✓" if result.status == "PASS" else "✗"
        print(f"{status} ({format_duration(result.duration)})")
    
    data = BaselineData(
        package=package,
        timestamp=timestamp,
        git_sha=git_sha,
        results=results,
    )
    
    return data, all_passed


def write_baseline_file(
    data: BaselineData,
    package_dir: Path,
) -> Path:
    """Write baseline file atomically."""
    content = generate_baseline_markdown(data, package_dir)
    
    filename = f"baseline-{data.timestamp}.md"
    output_path = package_dir / filename
    
    # Atomic write
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        dir=package_dir,
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(content)
        temp_path = f.name
    
    os.replace(temp_path, output_path)
    
    return output_path


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run verification checks and generate per-package baseline files.",
    )
    parser.add_argument(
        "--package",
        help="Filter by package name (default: all packages)",
    )
    parser.add_argument(
        "--skip",
        action="append",
        choices=["ty", "ruff", "pytest", "dvc", "ast-grep", "lint-imports"],
        help="Skip a specific check (can be used multiple times)",
    )
    
    args = parser.parse_args()
    
    skip_checks = set(args.skip) if args.skip else set()
    
    # Discover packages
    packages = discover_packages(args.package)
    if not packages:
        print(f"Error: No packages found in {PACKAGES_DIR}")
        return 1
    
    print(f"📋 Discovered packages: {', '.join(packages)}")
    if skip_checks:
        print(f"⏭️  Skipping checks: {', '.join(skip_checks)}")
    
    overall_success = True
    
    for package in packages:
        package_dir = PACKAGES_DIR / package
        
        if not package_dir.exists():
            print(f"Warning: Package directory not found: {package_dir}")
            continue
        
        # Run verification
        data, passed = run_verification(package, skip_checks)
        
        if not passed:
            overall_success = False
        
        # Write baseline file
        output_path = write_baseline_file(data, package_dir)
        print(f"  📝 Baseline written: {output_path}")
    
    print("\n" + "=" * 50)
    if overall_success:
        print("✓ All checks passed")
        return 0
    else:
        print("✗ Some checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
