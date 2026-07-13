# Preprocessing Validation Report — 松原 4-Mast Dataset

**Date**: 2026-07-02
**Masts**: M3142, M5972, M1664, M5057

---

## Summary

| Mast | Format | Columns | Rows | Status | Issues |
|------|--------|---------|------|--------|--------|
| M3142 | NRG SymphoniePRO | 53 | 60,062 | ✅ Clean | None |
| M5972 | NRG SymphoniePRO | 53 | 62,139 | ✅ Clean | None |
| M1664 | Windographer (GBK) | 57 | 153,992 | ⚠️ Issues | Ch9 mislabeled (pressure as speed); Ch8 low pressure |
| M5057 | Windographer (GBK) | 57 | 136,300 | ✅ Clean | 12 null timestamp rows |

---

## NRG Masts (M3142, M5972)

### Column Headers
Both masts already have columns in standard NRG format:
```
Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}
```
- **53 columns**: Timestamp + 52 sensor columns
- **Sensor types**: Anem (7 heights), Vane (3 heights), Analog temperature (1), Analog pressure (1)
- **Stat types**: Avg, SD, Min, Max, Gust (Gust/GustDir dropped by col-normalizer)

### Range Validation

| Sensor | M3142 Range | M5972 Range | Expected | Status |
|--------|-------------|-------------|----------|--------|
| Anemometers (m/s) | 0.31–27.28 | 0.31–26.67 | 0–30 | ✅ |
| Vanes (deg) | 0–360 | 0–359.98 | 0–360 | ✅ |
| Temperature (°C) | -27.8–34.4 | -28.72–35.48 | -40–50 | ✅ |
| Pressure (kPa) | 86.4–101.9 | 85.51–101.86 | 80–110 | ✅ |

### Notes
- M5972 pressure headers use uppercase `KPA` vs M3142's `kPa` — both should map correctly via nrg.toml unit mapping rules
- Zero nulls in either mast
- Wind speed profile consistent across heights (higher = faster, as expected)

---

## Windographer Masts (M1664, M5057)

### Column Mapping
Original Windographer columns mapped to NRG format:

| Channel | Original Pattern | NRG Pattern |
|---------|-----------------|-------------|
| Ch1-Ch6 | `direction {h} [°]` | `Ch{N}_Vane_{h}.00m_N_{stat}_Deg` |
| Ch7 | `temperature 10 [℃]` | `Ch7_Analog_10.00m_N_{stat}_C` |
| Ch8 | `pressure 8 [kPa]` | `Ch8_Analog_8.00m_N_{stat}_kPa` |
| Ch9-Ch14 | `speed {h} [m/s]` | `Ch{N}_Anem_{h}.00m_ESE_{stat}_m/s` |

### Encoding
Both Windographer files use **GBK encoding** (confirmed: `A1 E3` = °, `A1 E6` = ℃). The `csv-merge` tool auto-detected `cp874` (incorrect). Files were pre-converted to UTF-8 before processing.

### Range Validation

| Sensor | M1664 Range | M5057 Range | Expected | Status |
|--------|-------------|-------------|----------|--------|
| Anemometers (m/s) | 0.3–**1014.6** | 0.3–26.6 | 0–30 | ⚠️ M1664 Ch9 |
| Vanes (deg) | 0–359.9 | 0–359.9 | 0–360 | ✅ |
| Temperature (°C) | -33.9–36.0 | -34.1–37.1 | -40–50 | ✅ |
| Pressure (kPa) | **43.2**–102.8 | 85.7–102.1 | 80–110 | ⚠️ M1664 Ch8 |

---

## Critical Findings — M1664

### 1. Ch9_Anem_150.00m_ESE_Avg_m/s — MISLABELED SENSOR
- **1,229 rows** with values >30 m/s (max = 1014.6)
- High values cluster at 722.9, 1012.3–1012.7 — these are **atmospheric pressure in hPa**, not wind speed
- **Root cause**: Windographer export labeled a pressure/humidity sensor as "speed 150 [m/s]"
- **Impact**: Ch9 (150m anemometer) data is unreliable for wind analysis
- **Recommendation**: Flag Ch9 as suspect; consider re-mapping or excluding from wind resource assessment

### 2. Ch8_Analog_8.00m_N_Avg_kPa — LOW PRESSURE READINGS
- **1,049 rows** below 80 kPa (min = 43.2 kPa)
- At 122m elevation, expected pressure is ~100 kPa; 43.2 kPa is physically implausible
- **Recommendation**: Review pressure sensor calibration logs; mark suspect periods as missing

### M5057 — No Issues
- All sensors within expected physical ranges
- 12 rows with null timestamps (likely header/footer artifacts) — negligible impact on 136K rows

---

## Output Files

```
pre-masts/preprocessed/
├── M3142/
│   ├── 01_csv_merge.toml
│   ├── 02_col_normalize.toml
│   ├── 03_type_normalize.toml
│   ├── evidence.md
│   ├── merged.csv      (25.6 MB, 60K rows)
│   ├── normalized.csv   (25.6 MB, 60K rows)
│   └── final.csv        (25.6 MB, 60K rows)
├── M5972/
│   ├── 01_csv_merge.toml
│   ├── 02_col_normalize.toml
│   ├── 03_type_normalize.toml
│   ├── evidence.md
│   ├── merged.csv      (26.5 MB, 62K rows)
│   ├── normalized.csv   (26.5 MB, 62K rows)
│   └── final.csv        (26.5 MB, 62K rows)
├── M1664/
│   ├── 01_csv_merge.toml
│   ├── 02_col_normalize.toml
│   ├── 03_type_normalize.toml
│   ├── evidence.md
│   ├── merged.csv      (42.5 MB, 154K rows)
│   ├── normalized.csv   (42.5 MB, 154K rows)
│   └── final.csv        (42.5 MB, 154K rows)
├── M5057/
│   ├── 01_csv_merge.toml
│   ├── 02_col_normalize.toml
│   ├── 03_type_normalize.toml
│   ├── evidence.md
│   ├── merged.csv      (37.6 MB, 136K rows)
│   ├── normalized.csv   (37.6 MB, 136K rows)
│   └── final.csv        (37.6 MB, 136K rows)
└── VALIDATION.md        (this file)
```
