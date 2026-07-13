"""
Post-process: clean anomalous values in preprocessed mast CSVs.

1. Mast-specific row drops (drop entire rows):
   - M1664: Drop Jan 3–11, 2023 (9 days of Ch9 sensor mislabeling)

2. Per-cell null rules (set cell to null, keep the row):
   - Anemometer Avg/SD/Min > 30 m/s  → null  (sustained wind physical limit)
   - Anemometer Max > 50 m/s          → null  (gusts can exceed 30 but 50+ is sensor error)
   - Pressure Avg/Min/Max < 80 kPa   → null  (implausible at surface elevation)
   - Temperature Max > 50°C           → null  (sensor spike)
   - Temperature Min < -40°C          → null  (sensor spike)

Note: Pressure SD is excluded — its values are naturally ~0.0-0.5 kPa.
"""

import polars as pl
from pathlib import Path
import sys

BASE = Path(__file__).parent

# Mast-specific date ranges to DROP entirely (bad sensor periods)
ROW_DROPS = {
    "M1664": ("2023-01-03", "2023-01-11"),  # Ch9 mislabeling: pressure recorded as wind
}

# Per-cell null rules: (column_substring, allowed_stat_types, condition_fn, description)
RULES = [
    ("Anem",      ("Avg", "SD", "Min"),           lambda s: s > 30,  "wind >30 m/s (sustained)"),
    ("Anem",      ("Max",),                       lambda s: s > 50,  "gust >50 m/s (sensor error)"),
    ("Analog_8",  ("Avg", "Min", "Max"),          lambda s: s < 80,  "pressure <80 kPa"),
    ("Analog_10", ("Max",),                       lambda s: s > 50,  "temp >50°C (spike)"),
    ("Analog_10", ("Min",),                       lambda s: s < -40, "temp <-40°C (spike)"),
]


def clean_mast(mast: str, csv_path: Path) -> dict:
    """Apply row drops then per-cell null rules. Write cleaned.csv, return stats."""
    df = pl.read_csv(str(csv_path), infer_schema_length=0)
    original_rows = len(df)
    details = []

    # --- Step 1: Drop bad date ranges ---
    if mast in ROW_DROPS:
        start, end = ROW_DROPS[mast]
        before = len(df)
        # Extract date part from Timestamp (first 10 chars: "YYYY-MM-DD")
        df = df.filter(
            ~(
                (pl.col("Timestamp").str.slice(0, 10) >= start)
                & (pl.col("Timestamp").str.slice(0, 10) <= end)
            )
        )
        dropped = before - len(df)
        if dropped > 0:
            details.append(("ROW DROP", dropped, f"Date range {start} to {end}"))

    # --- Step 2: Per-cell null rules ---
    total_cells_nulled = 0
    for col_name in df.columns:
        for col_sub, stat_types, cond_fn, desc in RULES:
            if col_sub not in col_name:
                continue
            if not any(st in col_name for st in stat_types):
                continue

            s = df[col_name].cast(pl.Float64, strict=False)
            bad_mask = cond_fn(s)
            n_bad = bad_mask.sum()

            if n_bad > 0:
                df = df.with_columns(
                    pl.when(bad_mask).then(None).otherwise(pl.col(col_name)).alias(col_name)
                )
                total_cells_nulled += n_bad
                details.append((col_name, n_bad, desc))

    out_path = csv_path.parent / "cleaned.csv"
    df.write_csv(str(out_path))

    return {
        "original_rows": original_rows,
        "rows": len(df),
        "cols": len(df.columns),
        "rows_dropped": original_rows - len(df),
        "cells_nulled": total_cells_nulled,
        "details": details,
        "output": str(out_path),
    }


def main():
    masts = sys.argv[1:] if len(sys.argv) > 1 else ["M3142", "M5972", "M1664", "M5057"]

    for mast in masts:
        csv = BASE / mast / "final.csv"
        if not csv.exists():
            print(f"SKIP {mast}: {csv} not found")
            continue

        print(f"\n{'='*60}")
        print(f"  {mast}")
        print(f"{'='*60}")

        result = clean_mast(mast, csv)

        if result["rows_dropped"] > 0:
            print(f"  Dropped {result['rows_dropped']} rows ({result['original_rows']:,} → {result['rows']:,})")
        if result["cells_nulled"] == 0 and result["rows_dropped"] == 0:
            print(f"  ✅ No anomalies found ({result['rows']} rows, {result['cols']} cols)")
        elif result["cells_nulled"] > 0:
            print(f"  Nulled {result['cells_nulled']} cells:")
            for col, n, desc in result["details"]:
                if col == "ROW DROP":
                    print(f"    {'[row drop]':50s}  {n:6d} rows  ({desc})")
                else:
                    print(f"    {col:50s}  {n:6d} cells  ({desc})")
        print(f"  Output: {result['output']}")


if __name__ == "__main__":
    main()
