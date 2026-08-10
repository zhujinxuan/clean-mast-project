"""Lint .scratch ticket files against docs/agents/issue-tracker.md conventions.

Checks each ticket under `.scratch/<feature>/issues/`:
- Filename: `NN-<slug>.md` (to-tickets batch) or `YYYY-MM-DD-<slug>.md` (ad-hoc)
- A `Status:` line with a recognized status
- A `Blocked by:` line
- Acceptance criteria referencing the verify_baseline command

Usage:
    uv run python scripts/lint_tickets.py          # staged files only (pre-commit)
    uv run python scripts/lint_tickets.py --all    # every ticket in .scratch
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ISSUES_RE = re.compile(r"^\.scratch/[^/]+/issues/[^/]+\.md$")
NAME_RE = re.compile(r"^(\d{2}|\d{4}-\d{2}-\d{2})-[a-z0-9][a-z0-9-]*\.md$")
STATUS_RE = re.compile(r"^\*{0,2}Status:\*{0,2}\s*([a-z-]+)", re.MULTILINE)
BLOCKED_RE = re.compile(r"^\*{0,2}Blocked by:\*{0,2}", re.MULTILINE)

STATUSES = {
    # triage labels (docs/agents/triage-labels.md)
    "needs-triage",
    "needs-info",
    "ready-for-agent",
    "ready-for-human",
    "wontfix",
    # lifecycle / wayfinder
    "claimed",
    "resolved",
    "done",
}


def staged_ticket_files() -> list[Path]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        check=True,
    ).stdout
    return [ROOT / p for p in out.splitlines() if ISSUES_RE.match(p)]


def all_ticket_files() -> list[Path]:
    return sorted((ROOT / ".scratch").glob("*/issues/*.md"))


def lint_file(path: Path) -> list[str]:
    rel = path.relative_to(ROOT).as_posix()
    errors: list[str] = []
    if not NAME_RE.match(path.name):
        errors.append(
            f"{rel}: filename must be NN-<slug>.md (batch) or YYYY-MM-DD-<slug>.md (ad-hoc)"
        )
    text = path.read_text(encoding="utf-8")
    status = STATUS_RE.search(text)
    if status is None:
        errors.append(f"{rel}: missing 'Status:' line")
    elif status.group(1) not in STATUSES:
        errors.append(
            f"{rel}: unknown status '{status.group(1)}' (expected one of {sorted(STATUSES)})"
        )
    if not BLOCKED_RE.search(text):
        errors.append(f"{rel}: missing 'Blocked by:' line")
    if "verify_baseline" not in text:
        errors.append(
            f"{rel}: acceptance criteria must include the verify_baseline command"
        )
    return errors


def main() -> int:
    files = all_ticket_files() if "--all" in sys.argv else staged_ticket_files()
    errors = [error for path in files for error in lint_file(path)]
    if errors:
        print("Ticket lint failed:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1
    if files:
        print(f"Ticket lint: {len(files)} file(s) OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
