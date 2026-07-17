"""Deploy an archived CleanMast experiment to a target directory.

Usage (from the repository root):

    uv run python experiments-archived/<archive-dir>/deploy.py projects/<new-name>

What it does, in order:

1. `dvc pull -R <archive>` — restore DVC-tracked data (.tar.zst + .parquet).
2. Extract every `.tar.zst` from the directory that contains it
   (tar entries carry a prefix relative to that directory).
3. Copy the replay payload to the target, EXCLUDING DVC metadata
   (`*.dvc`, `*.tar.zst`, `.gitignore`, `ARCHIVE.md`, `deploy.py`).
4. Rename `justfile.archive` -> `Justfile` in the target. The file is a
   pristine copy of the original project's Justfile; `PROJECT_NAME` derives
   from the directory name at runtime, so it works unmodified under
   `projects/<new-name>/`.
5. Strip the read-only attribute recursively — DVC-pulled files carry it,
   and pipeline steps rewrite `raw/*.parquet` in place.
6. Sanity-check the target (masts/, mesos/, formats/, parse-sensors.toml).

The target directory is NEVER DVC-tracked: pipeline steps may rewrite,
regenerate, or delete anything inside it.
"""

from __future__ import annotations

import argparse
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ARCHIVE_DIR = Path(__file__).resolve().parent

# Files that belong to the archive itself, not to the replay payload.
# (justfile.archive is NOT skipped: it is copied as the target's Justfile.)
SKIP_NAMES = {".gitignore", "ARCHIVE.md", "deploy.py"}


def find_repo_root() -> Path:
    for candidate in (ARCHIVE_DIR, *ARCHIVE_DIR.parents):
        if (candidate / ".dvc").is_dir():
            return candidate
    sys.exit("Error: no .dvc directory found at or above the archive directory.")


def dvc_pull(root: Path) -> None:
    rel = ARCHIVE_DIR.relative_to(root).as_posix()
    print(f"+ dvc pull -R {rel}")
    subprocess.run(["dvc", "pull", "-R", rel], cwd=root, check=True)


def extract_tar_zst() -> None:
    archives = sorted(ARCHIVE_DIR.rglob("*.tar.zst"))
    for archive in archives:
        print(f"+ extract {archive.relative_to(ARCHIVE_DIR)}")
        with subprocess.Popen(
            ["zstd", "-d", archive.name, "-c"],
            cwd=archive.parent,
            stdout=subprocess.PIPE,
        ) as zstd, subprocess.Popen(
            ["tar", "xf", "-"], cwd=archive.parent, stdin=zstd.stdout
        ) as tar:
            if zstd.stdout is not None:
                zstd.stdout.close()
            tar_rc = tar.wait()
            zstd_rc = zstd.wait()
        if zstd_rc != 0 or tar_rc != 0:
            sys.exit(f"Error: failed to extract {archive}")


def copy_payload(target: Path) -> None:
    for item in sorted(ARCHIVE_DIR.iterdir()):
        if item.name in SKIP_NAMES or item.suffix == ".dvc" or item.name.endswith(".tar.zst"):
            continue
        if item.name == "justfile.archive":
            shutil.copy2(item, target / "Justfile")
        elif item.is_dir():
            shutil.copytree(
                item,
                target / item.name,
                ignore=shutil.ignore_patterns("*.dvc", "*.tar.zst"),
            )
        else:
            shutil.copy2(item, target / item.name)


def make_writable(target: Path) -> None:
    for path in target.rglob("*"):
        try:
            path.chmod(path.stat().st_mode | stat.S_IWRITE)
        except OSError:
            pass


def verify(target: Path) -> list[str]:
    problems = []
    if not (target / "Justfile").is_file():
        problems.append("Justfile missing (archive had no justfile.archive)")
    if not (target / "parse-sensors.toml").is_file():
        problems.append("parse-sensors.toml missing")
    for dirname in ("masts", "mesos", "formats", "raw"):
        if not (target / dirname).is_dir():
            problems.append(f"{dirname}/ missing")
    if (target / "masts").is_dir() and not list((target / "masts").glob("*.csv")):
        problems.append("masts/ contains no CSV files")
    if (target / "mesos").is_dir() and not list((target / "mesos").glob("*.txt")):
        problems.append("mesos/ contains no txt files")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy this archived experiment to a target directory.")
    parser.add_argument("target", type=Path, help="Target directory, e.g. projects/2026-07-13-songyuan")
    parser.add_argument("--force", action="store_true", help="Allow deploying into a non-empty directory")
    args = parser.parse_args()

    target: Path = args.target.resolve()
    if target == ARCHIVE_DIR or ARCHIVE_DIR in target.parents:
        sys.exit("Error: target must be OUTSIDE the archive directory.")
    if target.exists() and any(target.iterdir()) and not args.force:
        sys.exit(f"Error: {target} is not empty (use --force to deploy anyway).")
    if target.parent.name != "projects":
        print(f"Warning: target {target} is not under a projects/ directory;")
        print("the deployed Justfile assumes projects/<name> (PROJECT = projects/ + dir name).")

    target.mkdir(parents=True, exist_ok=True)
    root = find_repo_root()
    dvc_pull(root)
    extract_tar_zst()
    copy_payload(target)
    make_writable(target)

    problems = verify(target)
    for problem in problems:
        print(f"Warning: {problem}")

    print(f"\nDeployed to {target}")
    if not problems:
        print("Next: just -f " + target.name + "/Justfile run-all   (from the projects/ directory)")


if __name__ == "__main__":
    main()
