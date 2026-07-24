"""Shared comparator for step-wise test datasets (test-data/cleanmast/song-yuan-*).

Two comparisons per pipeline step:
  config   — semantic TOML equality between a recommend-generated config and
             the stored truth config (key order / comments / whitespace ignored).
  parquets — row-level equality between generated parquet outputs and the
             stored truth parquets (NaN == NaN; floats compared exactly after
             read; mismatches reported with max abs diff).

Usage:
  uv run python test-data/cleanmast/lib/compare_step.py config EXPECTED.toml ACTUAL.toml
  uv run python test-data/cleanmast/lib/compare_step.py parquets EXPECTED_DIR ACTUAL_DIR

Exit code 0 on match, 1 on mismatch/error. Human-readable report on stdout.
"""

from __future__ import annotations

import math
import sys
import tomllib
from pathlib import Path

import polars as pl


def _fail(msg: str) -> int:
    print(f"MISMATCH: {msg}")
    return 1


def compare_config(expected_path: Path, actual_path: Path, skip_keys: set[str] | None = None) -> int:
    skip = skip_keys or set()
    if not actual_path.exists():
        return _fail(f"generated config missing: {actual_path}")
    if not expected_path.exists():
        return _fail(f"truth config missing: {expected_path}")
    expected = tomllib.loads(expected_path.read_text(encoding="utf-8"))
    actual = tomllib.loads(actual_path.read_text(encoding="utf-8"))
    if expected == actual:
        print(f"OK config: {actual_path.name} matches truth")
        return 0
    exp_keys = set(_flatten(expected)) - skip
    act_keys = set(_flatten(actual)) - skip
    only_exp = sorted(exp_keys - act_keys)
    only_act = sorted(act_keys - exp_keys)
    common = sorted(exp_keys & act_keys)
    flat_exp, flat_act = _flatten(expected), _flatten(actual)
    diffs = [k for k in common if k not in skip and flat_exp[k] != flat_act[k]]
    for k in only_exp[:10]:
        print(f"  only in truth:     {k} = {flat_exp[k]!r}")
    for k in only_act[:10]:
        print(f"  only in generated: {k} = {flat_act[k]!r}")
    for k in diffs[:10]:
        print(f"  differs: {k}: truth={flat_exp[k]!r} generated={flat_act[k]!r}")
    if not only_exp and not only_act and not diffs:
        print(f"OK config: {actual_path.name} matches truth (skipped keys: {sorted(skip)})")
        return 0
    return _fail(
        f"{actual_path.name}: {len(only_exp)} missing, {len(only_act)} extra, {len(diffs)} differing keys"
    )


def _flatten(d: object, prefix: str = "") -> dict[str, object]:
    out: dict[str, object] = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(_flatten(v, f"{prefix}{k}."))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            out.update(_flatten(v, f"{prefix}{i}."))
    else:
        out[prefix.rstrip(".")] = d
    return out


def _series_equal(a: pl.Series, b: pl.Series) -> tuple[bool, float | None]:
    """Null/NaN-aware equality. Returns (equal, max_abs_diff for floats)."""
    if a.dtype != b.dtype:
        return False, None
    if a.dtype.is_float():
        fa, fb = a.to_numpy(), b.to_numpy()
        both_nan = (fa != fa) & (fb != fb)  # NaN != NaN
        same = (fa == fb) | both_nan
        if bool(same.all()):
            return True, 0.0
        diff = abs(fa - fb)
        finite = diff[diff == diff]  # drop NaN diffs
        max_diff = float(finite.max()) if finite.size else math.nan
        return False, max_diff
    return bool(((a == b) | (a.is_null() & b.is_null())).all()), None


def compare_parquets(expected_dir: Path, actual_dir: Path) -> int:
    if not actual_dir.is_dir():
        return _fail(f"generated output dir missing: {actual_dir}")
    expected_files = sorted(expected_dir.glob("*.parquet"))
    if not expected_files:
        return _fail(f"no truth parquets in {expected_dir}")
    failures = 0
    for exp_file in expected_files:
        act_file = actual_dir / exp_file.name
        if not act_file.exists():
            failures += _fail(f"missing output: {act_file.name}")
            continue
        exp = pl.read_parquet(exp_file)
        act = pl.read_parquet(act_file)
        if exp.shape != act.shape:
            failures += _fail(f"{exp_file.name}: shape truth={exp.shape} generated={act.shape}")
            continue
        if sorted(exp.columns) != sorted(act.columns):
            failures += _fail(f"{exp_file.name}: column sets differ")
            continue
        act = act.select(exp.columns)  # align column order
        bad_cols = []
        for col in exp.columns:
            equal, max_diff = _series_equal(exp[col], act[col])
            if not equal:
                bad_cols.append((col, max_diff))
        if bad_cols:
            for col, md in bad_cols[:5]:
                print(f"  {exp_file.name}.{col}: differs (max abs diff={md})")
            failures += _fail(f"{exp_file.name}: {len(bad_cols)} columns differ")
        else:
            print(f"OK parquet: {exp_file.name} ({exp.shape[0]} rows x {exp.shape[1]} cols)")
    extra = sorted(p.name for p in actual_dir.glob("*.parquet") if not (expected_dir / p.name).exists())
    if extra:
        print(f"  note: extra generated files not in truth: {extra}")
    return failures


def main(argv: list[str]) -> int:
    if len(argv) < 4 or len(argv) > 5:
        print(__doc__)
        return 2
    mode, expected, actual = argv[1], Path(argv[2]), Path(argv[3])
    skip_keys: set[str] = set()
    if len(argv) == 5:
        skip_keys = set(argv[4].split(","))
    if mode == "config":
        return compare_config(expected, actual, skip_keys)
    if mode == "parquets":
        return compare_parquets(expected, actual)
    print(f"unknown mode: {mode}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
