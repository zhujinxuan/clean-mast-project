#!/usr/bin/env python3
"""Thin wrapper delegating to `cleanmast-dev baseline` (cleanmast_dev_tools.baseline).

The implementation moved to packages/cleanmast-dev-tools (dev-driven commands
never ship in the cleanmast package). This wrapper preserves the command string
referenced by tickets, hooks, skills, and docs:

    uv run python scripts/verify_baseline.py --package cleanmast
"""

import sys

from cleanmast_dev_tools.baseline import main

if __name__ == "__main__":
    sys.exit(main())
