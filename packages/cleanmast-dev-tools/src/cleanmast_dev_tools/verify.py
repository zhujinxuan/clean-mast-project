"""Verify command - runs test datasets via their Justfiles."""

import concurrent.futures
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import click


def _find_test_data_root() -> Path:
    """Find test-data directory relative to workspace root.

    Search order:
    1. CWD / test-data
    2. Any parent of CWD / test-data
    """
    cwd = Path.cwd()
    for p in [cwd] + list(cwd.parents):
        candidate = p / "test-data"
        if candidate.is_dir():
            return candidate
    raise click.ClickException(
        "Cannot find test-data directory. "
        "Run from workspace root or a subdirectory."
    )


_can_use_just_cache: bool | None = None


def _discover_justfiles(test_data_root: Path, package_filter: str | None = None) -> list[dict]:
    """Discover all Justfiles in test-data directories.

    Returns list of dicts: {package, name, dir, justfile_path}
    """
    justfiles = []
    if not test_data_root.exists():
        return justfiles

    for pkg_dir in sorted(test_data_root.iterdir()):
        if not pkg_dir.is_dir():
            continue
        if pkg_dir.name.startswith(".") or pkg_dir.name.startswith("_"):
            continue
        if package_filter and pkg_dir.name != package_filter:
            continue

        for ds_dir in sorted(pkg_dir.iterdir()):
            if not ds_dir.is_dir():
                continue
            justfile_path = ds_dir / "Justfile"
            if justfile_path.exists():
                justfiles.append({
                    "package": pkg_dir.name,
                    "name": ds_dir.name,
                    "dir": ds_dir,
                    "justfile_path": justfile_path,
                })
    return justfiles


def _can_use_just() -> bool:
    """Check if `just` command is available. Cached result."""
    global _can_use_just_cache
    if _can_use_just_cache is not None:
        return _can_use_just_cache

    try:
        result = subprocess.run(
            ["just", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        _can_use_just_cache = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        _can_use_just_cache = False

    return _can_use_just_cache


def _run_just_verify(justfile_dir: Path, timeout: float = 1800.0) -> tuple[bool, dict, float]:
    """Run `just verify-json` in the justfile directory.

    Returns: (success, result_dict, elapsed_time)
    """
    start = time.perf_counter()

    try:
        result = subprocess.run(
            ["just", "verify-json"],
            cwd=justfile_dir,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
        elapsed = time.perf_counter() - start

        if result.returncode != 0:
            error_result = {
                "name": justfile_dir.name,
                "status": "fail",
                "duration_sec": round(elapsed, 1),
                "pull_status": "failed",
                "pull_duration_sec": 0.0,
                "outputs": [],
                "error": f"just verify-json failed: {result.stderr[:500]}",
            }
            return False, error_result, elapsed

        output = result.stdout.strip()
        json_start = output.find('{')
        if json_start == -1:
            raise ValueError("No JSON object found in output")

        json_str = output[json_start:]
        parsed = json.loads(json_str)

        if "name" not in parsed:
            parsed["name"] = justfile_dir.name
        if "status" not in parsed:
            parsed["status"] = "pass"
        if "duration_sec" not in parsed:
            parsed["duration_sec"] = round(elapsed, 1)
        if "pull_status" not in parsed:
            parsed["pull_status"] = "success"
        if "pull_duration_sec" not in parsed:
            parsed["pull_duration_sec"] = 0.0
        if "outputs" not in parsed:
            parsed["outputs"] = []
        if "error" not in parsed:
            parsed["error"] = None

        return True, parsed, elapsed

    except (json.JSONDecodeError, ValueError) as e:
        elapsed = time.perf_counter() - start
        error_result = {
            "name": justfile_dir.name,
            "status": "fail",
            "duration_sec": round(elapsed, 1),
            "pull_status": "failed",
            "pull_duration_sec": 0.0,
            "outputs": [],
            "error": f"Failed to parse JSON output: {e}",
        }
        return False, error_result, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start
        error_result = {
            "name": justfile_dir.name,
            "status": "fail",
            "duration_sec": round(elapsed, 1),
            "pull_status": "failed",
            "pull_duration_sec": 0.0,
            "outputs": [],
            "error": f"just verify-json timed out after {timeout}s",
        }
        return False, error_result, elapsed
    except FileNotFoundError:
        elapsed = time.perf_counter() - start
        error_result = {
            "name": justfile_dir.name,
            "status": "fail",
            "duration_sec": round(elapsed, 1),
            "pull_status": "failed",
            "pull_duration_sec": 0.0,
            "outputs": [],
            "error": "just command not found",
        }
        return False, error_result, elapsed


def _echo_dataset_result(entry: dict) -> None:
    """Echo one dataset result line (non-json mode)."""
    mark = "✓" if entry["status"] == "pass" else "✗"
    click.echo(f"  {mark} {entry['label']} ({entry['duration_sec']:.1f}s)")
    if entry["error"]:
        click.echo(f"          {entry['error'][:200]}")


@click.command("verify")
@click.option(
    "--package", "-p",
    help="Filter by package name (e.g., cleanmast)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show discovered datasets without running them",
)
@click.option(
    "--json", "-J",
    "json_output",
    is_flag=True,
    help="Output results as JSON instead of table",
)
@click.option(
    "--jobs", "-j",
    type=int,
    default=1,
    help="Number of parallel workers",
)
@click.argument(
    "dataset",
    required=False,
)
def verify(package: str | None, dry_run: bool, json_output: bool, dataset: str | None, jobs: int):
    """Discover and run test datasets via their Justfiles.

    Datasets live under test-data/{package}/{dataset}/ and are discovered
    by the presence of a Justfile with a `verify-json` recipe, which runs
    the dataset's verification and prints a JSON result object on stdout.

    When --jobs > 1, verification runs concurrently via ThreadPoolExecutor.

    Examples:

        cleanmast-dev verify                     # Run all datasets
        cleanmast-dev verify --dry-run           # List datasets only
        cleanmast-dev verify -p cleanmast        # Filter by package
        cleanmast-dev verify kp-202603-report    # Run specific dataset
        cleanmast-dev verify -p cleanmast -j 4   # Run with 4 parallel workers
    """
    test_data_root = _find_test_data_root()

    justfiles = _discover_justfiles(test_data_root, package_filter=package)

    if dataset:
        filtered = [j for j in justfiles if j["name"] == dataset]
        if not filtered:
            available = [j["name"] for j in justfiles]
            raise click.ClickException(f"Dataset '{dataset}' not found. Available: {available}")
        justfiles = filtered

    if not justfiles:
        if package:
            click.echo(f"No datasets found for package '{package}'.")
        else:
            click.echo("No datasets found in test-data/.")
        return

    if not dry_run and not _can_use_just():
        raise click.ClickException("`just` command not found; verify requires just-mode.")

    if not json_output:
        click.echo(click.style("✓ CleanMast Verify Runner", bold=True))
        click.echo("=" * 40)
        click.echo()

    results: list[dict] = []

    if dry_run:
        for jf in justfiles:
            label = f"{jf['package']}/{jf['name']}"
            if not json_output:
                click.echo(f"  [DRY-RUN] {label}")
            results.append({
                "name": jf["name"],
                "label": label,
                "status": "dry-run",
                "pull_status": "skipped",
                "pull_duration_sec": 0.0,
                "duration_sec": 0.0,
                "outputs": [],
                "error": None,
            })
    elif jobs > 1:
        _results: list[dict | None] = [None] * len(justfiles)
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
            future_to_idx: dict[concurrent.futures.Future, int] = {
                executor.submit(_run_just_verify, jf["dir"]): idx
                for idx, jf in enumerate(justfiles)
            }
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                jf = justfiles[idx]
                label = f"{jf['package']}/{jf['name']}"
                try:
                    _, result_dict, _ = future.result()
                except Exception as exc:
                    result_dict = {
                        "name": jf["name"],
                        "status": "fail",
                        "duration_sec": 0.0,
                        "pull_status": "failed",
                        "pull_duration_sec": 0.0,
                        "outputs": [],
                        "error": f"Worker exception: {exc}",
                    }
                _results[idx] = {
                    "name": result_dict["name"],
                    "label": label,
                    "status": result_dict["status"],
                    "pull_status": result_dict.get("pull_status", "success"),
                    "pull_duration_sec": result_dict.get("pull_duration_sec", 0.0),
                    "duration_sec": result_dict.get("duration_sec", 0.0),
                    "outputs": result_dict.get("outputs", []),
                    "error": result_dict.get("error"),
                }
        results = [r for r in _results if r is not None]
        if not json_output:
            for entry in results:
                _echo_dataset_result(entry)
    else:
        for jf in justfiles:
            label = f"{jf['package']}/{jf['name']}"
            _, result_dict, _ = _run_just_verify(jf["dir"])
            entry = {
                "name": result_dict["name"],
                "label": label,
                "status": result_dict["status"],
                "pull_status": result_dict.get("pull_status", "success"),
                "pull_duration_sec": result_dict.get("pull_duration_sec", 0.0),
                "duration_sec": result_dict.get("duration_sec", 0.0),
                "outputs": result_dict.get("outputs", []),
                "error": result_dict.get("error"),
            }
            results.append(entry)
            if not json_output:
                _echo_dataset_result(entry)

    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    dry = sum(1 for r in results if r["status"] == "dry-run")

    if json_output:
        json_result = {
            "package": "cleanmast",
            "timestamp": datetime.now().isoformat(),
            "datasets": [
                {
                    "name": r["name"],
                    "status": r["status"],
                    "duration_sec": r["duration_sec"],
                    "pull_status": r["pull_status"],
                    "pull_duration_sec": r["pull_duration_sec"],
                    "outputs": r["outputs"],
                    "error": r["error"],
                }
                for r in results
            ],
            "summary": {"passed": passed, "failed": failed},
        }
        click.echo(json.dumps(json_result, indent=2))
    else:
        click.echo("=" * 40)
        if dry:
            click.echo(f"Results: {len(justfiles)} dataset(s) listed (dry-run)")
        elif failed == 0:
            click.echo(click.style(f"Results: {passed} passed, {failed} failed", fg="green"))
        else:
            click.echo(click.style(f"Results: {passed} passed, {failed} failed", fg="red"))

    if failed > 0 and not dry and not json_output:
        sys.exit(1)
