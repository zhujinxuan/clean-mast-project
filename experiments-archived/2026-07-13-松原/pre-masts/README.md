# Pre-Masts: 松原 4-Mast Preprocessing

Raw meteorological mast data and preprocessing pipeline for the 松原 (Songyuan) wind energy assessment project.

## Masts

| Mast | Source Format | Encoding | Rows | Sensors |
|------|--------------|----------|------|---------|
| M3142 | NRG SymphoniePRO export | UTF-8 | 60,062 | 7 anemometers, 3 vanes, 1 temp, 1 pressure |
| M5972 | NRG SymphoniePRO export | UTF-8 | 62,139 | 7 anemometers, 3 vanes, 1 temp, 1 pressure |
| M1664 | Windographer 4.0.28 export | GBK | 153,992 | 6 anemometers, 6 vanes, 1 temp, 1 pressure |
| M5057 | Windographer 4.0.28 export | GBK | 136,300 | 6 anemometers, 6 vanes, 1 temp, 1 pressure |

## Directory Structure

```
pre-masts/
├── raw/                    # Source files (untouched)
│   ├── M3142.txt
│   ├── M5972.txt
│   ├── M1664.txt
│   └── M5057.txt
├── preprocessed/           # Pipeline outputs
│   ├── M3142/
│   ├── M5972/
│   ├── M1664/
│   ├── M5057/
│   ├── postprocess_clean.py
│   └── VALIDATION.md
├── mesos/                  # ERA5 mesoscale data
└── README.md
```

## Pipeline Steps

### 1. Encoding Conversion (Windographer masts only)

Windographer exports use GBK encoding (`°` = `A1 E3`, `℃` = `A1 E6`). The `csv-merge` tool auto-detects `cp874` (Thai) instead of GBK, which produces garbled column names (`°` → `กใ`). Pre-convert to UTF-8 before processing:

```python
raw = Path("raw/M1664.txt").read_bytes()
text = raw.decode("gbk")
Path("preprocessed/M1664/M1664_utf8.txt").write_text(text, encoding="utf-8")
```

### 2. CSV Merge (`csv-merge`)

Merges raw files, normalizes timestamps, handles column mismatches.

| Mast | Config | Delim | Header Line | Notes |
|------|--------|-------|-------------|-------|
| M3142 | `01_csv_merge.toml` | `\t` | 236 | NRG format, "Data" marker at line 235 |
| M5972 | `01_csv_merge.toml` | `\t` | 226 | NRG format, "Data" marker at line 225 |
| M1664 | `01_csv_merge.toml` | `,` | 10 | Uses `M1664_utf8.txt` (converted) |
| M5057 | `01_csv_merge.toml` | `,` | 10 | Uses `M5057_utf8.txt` (converted) |

### 3. Column Normalization (`col-normalizer`)

Renames raw column names to standard NRG format:
```
Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}
```

- **NRG masts (M3142, M5972)**: Identity mapping (`keep_unmapped = false` drops Gust columns)
- **Windographer masts (M1664, M5057)**: Full mapping from `direction 150 [°]` → `Ch1_Vane_150.00m_N_Avg_Deg`, etc.

**Known issue**: The col-normalizer scrambles column order (alphabetical instead of preserving input order). Data values remain correctly matched to their column names.

### 4. Type Normalization (`type-normalizer`)

Converts all sensor columns to Float64.

### 5. Post-Process Cleaning (`postprocess_clean.py`)

Nulls anomalous values per-cell (rows preserved):

| Rule | Columns | Rationale |
|------|---------|-----------|
| Wind > 30 m/s | Anem Avg/SD/Min | Sustained wind physical limit |
| Gust > 50 m/s | Anem Max | Sensor error threshold |
| Pressure < 80 kPa | Analog_8 Avg/Min/Max | Implausible at surface elevation |
| Temp > 50°C | Analog_10 Max | Sensor spike |
| Temp < -40°C | Analog_10 Min | Sensor spike |

Run: `uv run python pre-masts/preprocessed/postprocess_clean.py`

## Data Quality Findings

### M1664 — Ch9 Sensor Mislabeling

**Ch9 (`speed 150 [m/s]`)** is mostly wind speed (99.2%) but 1,228 rows (0.8%) contain atmospheric pressure in hPa (values 950–1014), not wind speed. Windographer mislabeled a pressure sensor as "speed 150".

**Ch8 (`pressure 8 [kPa]`)** is mostly pressure (99.3%) but 1,049 rows (0.7%) have anomalous low readings (43–80 kPa).

These rows are correlated (Ch9 shows hPa when Ch8 shows low kPa) — likely the same sensor malfunction period.

### M3142 / M5972 — Pressure Min Dips

`Ch17_Analog_8.00m_N_Min_kPa` has occasional dips below 80 kPa (4.8–5.2% of rows). These are sensor artifacts in the minimum statistics; average and max values remain normal.

## Output Files

Each mast directory contains:

| File | Description |
|------|-------------|
| `merged.csv` | csv-merge output |
| `normalized.csv` | col-normalizer output |
| `final.csv` | type-normalizer output |
| `cleaned.csv` | post-process cleaned output (anomalies nulled) |
| `evidence.md` | Channel mapping documentation |
| `01_csv_merge.toml` | csv-merge config |
| `02_col_normalize.toml` | col-normalizer config |
| `03_type_normalize.toml` | type-normalizer config |

The `cleaned.csv` files are ready for downstream processing ( Julia CleanMast pipeline).
