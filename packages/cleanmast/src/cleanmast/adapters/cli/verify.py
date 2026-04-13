"""CLI adapter for verify command - runs test datasets."""

import json
import subprocess
import sys
import time
import tomllib
from datetime import datetime
from pathlib import Path

import click


def _find_test_data_root() -> Path:
    """Find test-data directory relative to workspace root.
    
    Search order:
    1. CWD / test-data
    2. This package's parent / ../../../../ test-data (dev layout)
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


def _discover_datasets(test_data_root: Path, package_filter: str | None = None) -> list[dict]:
    """Discover all datasets with verify.toml manifests.
    
    Returns list of dicts: {package, name, dir, manifest}
    """
    datasets = []
    if not test_data_root.exists():
        return datasets
    
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
            manifest = ds_dir / "verify.toml"
            if manifest.exists():
                with open(manifest, "rb") as f:
                    cfg = tomllib.load(f)
                datasets.append({
                    "package": pkg_dir.name,
                    "name": ds_dir.name,
                    "dir": ds_dir,
                    "manifest": manifest,
                    "config": cfg,
                })
    return datasets


def _run_dvc_pull(dataset_dir: Path) -> tuple[bool, str, float]:
    """Run dvc pull in dataset directory. Returns (success, output, elapsed)."""
    start = time.perf_counter()
    try:
        result = subprocess.run(
            ["dvc", "pull"],
            cwd=dataset_dir,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=300,
        )
        elapsed = time.perf_counter() - start
        success = result.returncode == 0
        output = result.stdout.strip() or result.stderr.strip()
        return success, output, elapsed
    except FileNotFoundError:
        elapsed = time.perf_counter() - start
        return False, "dvc not found (skip)", elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start
        return False, "dvc pull timed out", elapsed


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


def _run_just_verify(justfile_dir: Path, timeout: float = 600.0) -> tuple[bool, dict, float]:
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


def _run_cleanmast_command(dataset_dir: Path, command: str, config: str, args: list[str]) -> tuple[bool, str, float]:
    """Run cleanmast {command} {config} {args}. Returns (success, output, elapsed)."""
    start = time.perf_counter()
    cmd_parts = ["cleanmast"] + command.split() + [config] + args
    
    try:
        result = subprocess.run(
            cmd_parts,
            cwd=dataset_dir,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=600,
        )
        elapsed = time.perf_counter() - start
        success = result.returncode == 0
        output = result.stdout.strip()
        if not output:
            output = result.stderr.strip()
        return success, output, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start
        return False, "Command timed out", elapsed


def _check_outputs(dataset_dir: Path, expected_outputs: list[str]) -> tuple[bool, list[str]]:
    """Check expected output files exist. Returns (all_exist, missing_files)."""
    missing = []
    for out_path in expected_outputs:
        full_path = dataset_dir / out_path
        if not full_path.exists():
            missing.append(out_path)
    return len(missing) == 0, missing


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
    "--json", "-j",
    "json_output",
    is_flag=True,
    help="Output results as JSON instead of Rich table",
)
@click.argument(
    "dataset",
    required=False,
)
def verify(package: str | None, dry_run: bool, json_output: bool, dataset: str | None):
    """Discover and run test datasets under test-data/.
    
    Scans test-data/{package}/{dataset}/ for verify.toml manifests,
    runs dvc pull, executes the declared cleanmast command,
    and verifies expected outputs exist.
    
    Examples:
        
        cleanmast verify                  # Run all datasets
        cleanmast verify --dry-run        # List datasets only
        cleanmast verify -p cleanmast     # Filter by package
        cleanmast verify kp-202603-report # Run specific dataset
    """
    test_data_root = _find_test_data_root()
    
    datasets = _discover_datasets(test_data_root, package_filter=package)
    
    if dataset:
        datasets = [d for d in datasets if d["name"] == dataset]
        if not datasets:
            available = [d["name"] for d in _discover_datasets(test_data_root, package_filter=package)]
            raise click.ClickException(f"Dataset '{dataset}' not found. Available: {available}")
    
    if not datasets:
        if package:
            click.echo(f"No datasets found for package '{package}'.")
        else:
            click.echo("No datasets found in test-data/.")
        return

    use_just_mode = False
    justfiles = []
    if json_output and _can_use_just():
        justfiles = _discover_justfiles(test_data_root, package_filter=package)
        if dataset:
            justfiles = [j for j in justfiles if j["name"] == dataset]
        if justfiles:
            use_just_mode = True

    if not json_output:
        click.echo(click.style("✓ CleanMast Verify Runner", bold=True))
        click.echo("=" * 40)
        click.echo()
    
    results = []
    
    if use_just_mode:
        for jf in justfiles:
            label = f"{jf['package']}/{jf['name']}"
            
            if dry_run:
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
                continue
            
            _, result_dict, _ = _run_just_verify(jf["dir"])
            results.append({
                "name": result_dict["name"],
                "label": label,
                "status": result_dict["status"],
                "pull_status": result_dict.get("pull_status", "success"),
                "pull_duration_sec": result_dict.get("pull_duration_sec", 0.0),
                "duration_sec": result_dict.get("duration_sec", 0.0),
                "outputs": result_dict.get("outputs", []),
                "error": result_dict.get("error"),
            })
    else:
        for ds in datasets:
            label = f"{ds['package']}/{ds['name']}"
            cfg = ds["config"]
            
            run_cfg = cfg.get("run", {})
            expect_cfg = cfg.get("expect", {})
            command = run_cfg.get("command", "")
            config_file = run_cfg.get("config", "")
            extra_args = run_cfg.get("args", [])
            expected_outputs = expect_cfg.get("outputs", [])
            
            if dry_run:
                if not json_output:
                    click.echo(f"  [DRY-RUN] {label}")
                    click.echo(f"    Command: cleanmast {command} {config_file} {' '.join(extra_args)}")
                    click.echo(f"    Expect:  {expected_outputs}")
                results.append({
                    "name": ds["name"],
                    "label": label,
                    "status": "dry-run",
                    "pull_status": "skipped",
                    "pull_duration_sec": 0.0,
                    "duration_sec": 0.0,
                    "outputs": expected_outputs,
                    "error": None,
                })
                continue
            
            if not json_output:
                click.echo(f"  [PULL]   {label}", nl=False)
            pull_ok, pull_msg, pull_time = _run_dvc_pull(ds["dir"])
            if not json_output:
                click.echo(f"  {'✓' if pull_ok else '✗'} ({pull_time:.1f}s)")
                if not pull_ok and "not found" not in pull_msg:
                    click.echo(f"          {pull_msg}")

            if not json_output:
                click.echo(f"  [RUN]    {label}", nl=False)
            cmd_ok, cmd_msg, cmd_time = _run_cleanmast_command(
                ds["dir"], command, config_file, extra_args
            )
            if not json_output:
                click.echo(f"  {'✓' if cmd_ok else '✗'} ({cmd_time:.1f}s)")
                if not cmd_ok:
                    click.echo(f"          {cmd_msg[:200]}")

            if not json_output:
                click.echo(f"  [CHECK]  {label}", nl=False)
            outputs_ok, missing = _check_outputs(ds["dir"], expected_outputs)
            if outputs_ok:
                first_out = ds["dir"] / expected_outputs[0]
                size_mb = first_out.stat().st_size / (1024 * 1024)
                if not json_output:
                    click.echo(f"  ✓ {expected_outputs[0]} ({size_mb:.1f} MB)")
            else:
                if not json_output:
                    click.echo(f"  ✗ Missing: {missing}")

            overall_ok = cmd_ok and outputs_ok
            error_msg = None
            if not overall_ok:
                if not cmd_ok:
                    error_msg = cmd_msg[:500]
                elif not outputs_ok:
                    error_msg = f"Missing outputs: {missing}"

            results.append({
                "name": ds["name"],
                "label": label,
                "status": "pass" if overall_ok else "fail",
                "pull_status": "success" if pull_ok else "failed",
                "pull_duration_sec": round(pull_time, 1),
                "duration_sec": round(cmd_time, 1),
                "outputs": expected_outputs if outputs_ok else [],
                "error": error_msg,
            })
            if not json_output:
                click.echo()
    
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
            click.echo(f"Results: {len(datasets)} dataset(s) listed (dry-run)")
        elif failed == 0:
            click.echo(click.style(f"Results: {passed} passed, {failed} failed", fg="green"))
        else:
            click.echo(click.style(f"Results: {passed} passed, {failed} failed", fg="red"))

    if failed > 0 and not dry and not json_output:
        sys.exit(1)
