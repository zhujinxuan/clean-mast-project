"""
Patch reconstruct-meso.toml to extend the time range for M3142/M5972.

Why:
  The cluster-optimal period (recommend reconstruct-meso) sets a shared
  2022-09-01 → 2025-08-31 grid for all masts. But the representative-year
  windows for M3142/M5972 are 2022-08-01 → 2023-07-31 (see
  override_representative_year.py), and representative-year.toml reads
  ./reconstruct-meso/*.parquet — so August 2022 was silently clipped,
  producing 11-month "representative years".

  reconstruct-cross (the reconstruct-meso input) covers 2022-06-11 →
  2025-12-14 for every mast with 0 nulls at 150m, and clean/ has real
  measurements for August 2022 on both masts — so extending min back to
  2022-08-01 restores a measured month, not a fabricated one.

Patched:
  M3142: min 2022-09-01 → 2022-08-01  (max unchanged 2025-08-31)
  M5972: min 2022-09-01 → 2022-08-01  (max unchanged 2025-08-31)
  M1664, M5057: untouched (their rep-year window 2024-09 → 2025-08 is
  already inside the shared grid).
"""

import re
import sys
from pathlib import Path

# Per-mast time_range overrides: mast -> (min, max) or None to leave unchanged
MAST_RANGE_OVERRIDES = {
    "M3142": ("2022-08-01T00:00:00.000Z", None),
    "M5972": ("2022-08-01T00:00:00.000Z", None),
}


def patch_reconstruct_meso(toml_path: Path) -> dict:
    """Patch per-mast time_range in reconstruct-meso.toml."""
    text = toml_path.read_text(encoding="utf-8")
    patched = {}

    for mast, (new_min, new_max) in MAST_RANGE_OVERRIDES.items():
        pattern = rf'(\[\[masts\]\]\nname = "{mast}".*?\[masts\.time_range\]\n    max = )(\S+)(.*?\n    min = )(\S+)'

        def replace_range(m):
            max_val = new_max if new_max is not None else m.group(2)
            min_val = new_min if new_min is not None else m.group(4)
            return f"{m.group(1)}{max_val}{m.group(3)}{min_val}"

        new_text, count = re.subn(pattern, replace_range, text, flags=re.DOTALL)
        if count > 0:
            text = new_text
            patched[mast] = f"min → {new_min}" if new_min else f"max → {new_max}"
        else:
            print(f"  Warning: Could not patch {mast} -- pattern not found")

    toml_path.write_text(text, encoding="utf-8")
    return patched


def main():
    base = Path(__file__).parent
    toml_path = base.parent / "reconstruct-meso.toml"

    if not toml_path.exists():
        print(f"Error: {toml_path} not found")
        sys.exit(1)

    print(f"Patching: {toml_path}")
    patched = patch_reconstruct_meso(toml_path)

    print(f"\nPatched {len(patched)}/{len(MAST_RANGE_OVERRIDES)} masts:")
    for mast, change in patched.items():
        print(f"  {mast}: {change}")

    for mast in MAST_RANGE_OVERRIDES:
        if mast not in patched:
            print(f"  {mast}: NOT patched")


if __name__ == "__main__":
    main()
