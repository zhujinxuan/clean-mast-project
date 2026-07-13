# Preprocessing Evidence — M1664

## Source File
- **File**: `../raw/M1664.txt`
- **Format**: Windographer 4.0.28 export
- **Encoding**: GBK (confirmed via byte analysis: `A1 E3` = `°` U+00B0, `A1 E6` = `℃` U+2103)
- **Delimiter**: Comma (`,`)
- **Header line**: 10 (0-based)
- **Data rows**: ~154,000
- **Site**: M1664
- **Coordinates**: 45.247416°N, 124.430532°E, 122.0m

## Channel Mapping

| Channel | Raw Column | Mapped Column | Height Source | Rationale |
|---|---|---|---|---|
| Ch1 | direction 150 [°] | Ch1_Vane_150.00m_N_Avg_Deg | Column name | Height 150m from column name |
| Ch1 | direction 150 [°] sd | Ch1_Vane_150.00m_N_SD_Deg | Column name | Height 150m from column name |
| Ch1 | direction 150 [°] max | Ch1_Vane_150.00m_N_Max_Deg | Column name | Height 150m from column name |
| Ch1 | direction 150 [°] min | Ch1_Vane_150.00m_N_Min_Deg | Column name | Height 150m from column name |
| Ch2 | direction 100 [°] | Ch2_Vane_100.00m_N_Avg_Deg | Column name | Height 100m from column name |
| Ch2 | direction 100 [°] sd | Ch2_Vane_100.00m_N_SD_Deg | Column name | Height 100m from column name |
| Ch2 | direction 100 [°] max | Ch2_Vane_100.00m_N_Max_Deg | Column name | Height 100m from column name |
| Ch2 | direction 100 [°] min | Ch2_Vane_100.00m_N_Min_Deg | Column name | Height 100m from column name |
| Ch3 | direction 70 [°] | Ch3_Vane_70.00m_N_Avg_Deg | Column name | Height 70m from column name |
| Ch3 | direction 70 [°] sd | Ch3_Vane_70.00m_N_SD_Deg | Column name | Height 70m from column name |
| Ch3 | direction 70 [°] max | Ch3_Vane_70.00m_N_Max_Deg | Column name | Height 70m from column name |
| Ch3 | direction 70 [°] min | Ch3_Vane_70.00m_N_Min_Deg | Column name | Height 70m from column name |
| Ch4 | direction 50 [°] | Ch4_Vane_50.00m_N_Avg_Deg | Column name | Height 50m from column name |
| Ch4 | direction 50 [°] sd | Ch4_Vane_50.00m_N_SD_Deg | Column name | Height 50m from column name |
| Ch4 | direction 50 [°] max | Ch4_Vane_50.00m_N_Max_Deg | Column name | Height 50m from column name |
| Ch4 | direction 50 [°] min | Ch4_Vane_50.00m_N_Min_Deg | Column name | Height 50m from column name |
| Ch5 | direction 30 [°] | Ch5_Vane_30.00m_N_Avg_Deg | Column name | Height 30m from column name |
| Ch5 | direction 30 [°] sd | Ch5_Vane_30.00m_N_SD_Deg | Column name | Height 30m from column name |
| Ch5 | direction 30 [°] max | Ch5_Vane_30.00m_N_Max_Deg | Column name | Height 30m from column name |
| Ch5 | direction 30 [°] min | Ch5_Vane_30.00m_N_Min_Deg | Column name | Height 30m from column name |
| Ch6 | direction 10 [°] | Ch6_Vane_10.00m_N_Avg_Deg | Column name | Height 10m from column name |
| Ch6 | direction 10 [°] sd | Ch6_Vane_10.00m_N_SD_Deg | Column name | Height 10m from column name |
| Ch6 | direction 10 [°] max | Ch6_Vane_10.00m_N_Max_Deg | Column name | Height 10m from column name |
| Ch6 | direction 10 [°] min | Ch6_Vane_10.00m_N_Min_Deg | Column name | Height 10m from column name |
| Ch7 | temperature 10 [℃] | Ch7_Analog_10.00m_N_Avg_C | Column name | Temperature at 10m |
| Ch7 | temperature 10 [℃] sd | Ch7_Analog_10.00m_N_SD_C | Column name | Temperature at 10m |
| Ch7 | temperature 10 [℃] max | Ch7_Analog_10.00m_N_Max_C | Column name | Temperature at 10m |
| Ch7 | temperature 10 [℃] min | Ch7_Analog_10.00m_N_Min_C | Column name | Temperature at 10m |
| Ch8 | pressure 8 [kPa] | Ch8_Analog_8.00m_N_Avg_kPa | Column name | Pressure at 8m; kPa unit preserved |
| Ch8 | pressure 8 [kPa] sd | Ch8_Analog_8.00m_N_SD_kPa | Column name | Pressure at 8m; kPa unit preserved |
| Ch8 | pressure 8 [kPa] max | Ch8_Analog_8.00m_N_Max_kPa | Column name | Pressure at 8m; kPa unit preserved |
| Ch8 | pressure 8 [kPa] min | Ch8_Analog_8.00m_N_Min_kPa | Column name | Pressure at 8m; kPa unit preserved |
| Ch9 | speed 150 [m/s] | Ch9_Anem_150.00m_ESE_Avg_m/s | Column name | Height 150m from column name |
| Ch9 | speed 150 [m/s] sd | Ch9_Anem_150.00m_ESE_SD_m/s | Column name | Height 150m from column name |
| Ch9 | speed 150 [m/s] max | Ch9_Anem_150.00m_ESE_Max_m/s | Column name | Height 150m from column name |
| Ch9 | speed 150 [m/s] min | Ch9_Anem_150.00m_ESE_Min_m/s | Column name | Height 150m from column name |
| Ch10 | speed 100 [m/s] | Ch10_Anem_100.00m_ESE_Avg_m/s | Column name | Height 100m from column name |
| Ch10 | speed 100 [m/s] sd | Ch10_Anem_100.00m_ESE_SD_m/s | Column name | Height 100m from column name |
| Ch10 | speed 100 [m/s] max | Ch10_Anem_100.00m_ESE_Max_m/s | Column name | Height 100m from column name |
| Ch10 | speed 100 [m/s] min | Ch10_Anem_100.00m_ESE_Min_m/s | Column name | Height 100m from column name |
| Ch11 | speed 70 [m/s] | Ch11_Anem_70.00m_ESE_Avg_m/s | Column name | Height 70m from column name |
| Ch11 | speed 70 [m/s] sd | Ch11_Anem_70.00m_ESE_SD_m/s | Column name | Height 70m from column name |
| Ch11 | speed 70 [m/s] max | Ch11_Anem_70.00m_ESE_Max_m/s | Column name | Height 70m from column name |
| Ch11 | speed 70 [m/s] min | Ch11_Anem_70.00m_ESE_Min_m/s | Column name | Height 70m from column name |
| Ch12 | speed 50 [m/s] | Ch12_Anem_50.00m_ESE_Avg_m/s | Column name | Height 50m from column name |
| Ch12 | speed 50 [m/s] sd | Ch12_Anem_50.00m_ESE_SD_m/s | Column name | Height 50m from column name |
| Ch12 | speed 50 [m/s] max | Ch12_Anem_50.00m_ESE_Max_m/s | Column name | Height 50m from column name |
| Ch12 | speed 50 [m/s] min | Ch12_Anem_50.00m_ESE_Min_m/s | Column name | Height 50m from column name |
| Ch13 | speed 30 [m/s] | Ch13_Anem_30.00m_ESE_Avg_m/s | Column name | Height 30m from column name |
| Ch13 | speed 30 [m/s] sd | Ch13_Anem_30.00m_ESE_SD_m/s | Column name | Height 30m from column name |
| Ch13 | speed 30 [m/s] max | Ch13_Anem_30.00m_ESE_Max_m/s | Column name | Height 30m from column name |
| Ch13 | speed 30 [m/s] min | Ch13_Anem_30.00m_ESE_Min_m/s | Column name | Height 30m from column name |
| Ch14 | speed 10 [m/s] | Ch14_Anem_10.00m_ESE_Avg_m/s | Column name | Height 10m from column name |
| Ch14 | speed 10 [m/s] sd | Ch14_Anem_10.00m_ESE_SD_m/s | Column name | Height 10m from column name |
| Ch14 | speed 10 [m/s] max | Ch14_Anem_10.00m_ESE_Max_m/s | Column name | Height 10m from column name |
| Ch14 | speed 10 [m/s] min | Ch14_Anem_10.00m_ESE_Min_m/s | Column name | Height 10m from column name |

## Column Summary
- **Total raw columns**: 57 (Date/Time + 56 sensor columns)
- **Kept columns**: 56 sensor columns + Timestamp
- **Dropped columns**: None (all columns mapped)

## Sensor Height Assignment
- **Direction vanes (Ch1-Ch6)**: 150m, 100m, 70m, 50m, 30m, 10m
- **Temperature (Ch7)**: 10m
- **Pressure (Ch8)**: 8m
- **Anemometers (Ch9-Ch14)**: 150m, 100m, 70m, 50m, 30m, 10m

## Preprocessing Findings

### Encoding
| Column | Issue | User Decision | Rationale |
|---|---|---|---|
| All direction cols | Original unit `°` encoded in GBK (A1 E3) | Keep; col-normalizer renames to Deg | Unicode degree symbol preserved through GBK decode |
| All temperature cols | Original unit `℃` encoded in GBK (A1 E6) | Keep; col-normalizer renames to C | Unicode celsius symbol preserved through GBK decode |
| Pressure columns | Unit = kPa | Keep; nrg.toml mapping converts to Pa | Pressure kPa→Pa conversion handled by sensor format TOML |
| Timestamp format | Includes `.0` fractional seconds | Keep as-is | Format `%Y-%m-%d %H:%M:%S.0` accepted by downstream |
| GBK encoding | csv-merge auto-detected cp874 (wrong); manually converted to UTF-8 | Pre-converted to UTF-8 before csv-merge | cp874 detection caused garbled column names |

### Data Quality Issues
| Column | Issue | Severity | User Decision | Rationale |
|---|---|---|---|---|
| Ch9_Anem_150.00m_ESE_Avg_m/s | 1,229 rows with values >100 (max=1014.6); values cluster at 722.9, 1012.3-1012.7 — consistent with atmospheric pressure in hPa, NOT wind speed | **WARNING** | Keep column but flag as unreliable; investigate sensor config | Windographer likely mislabeled a pressure sensor as "speed 150" |
| Ch8_Analog_8.00m_N_Avg_kPa | 1,049 rows below 80 kPa (min=43.2 kPa); implausible for 122m elevation (expected ~100 kPa) | **INFO** | Keep; document for downstream review | Possibly corrupted pressure data or sensor malfunction periods |
## Pipeline
1. `uv run preprocess csv-merge 01_csv_merge.toml` → merged.csv
2. `uv run preprocess col-normalizer 02_col_normalize.toml` → normalized.csv
3. `uv run preprocess type-normalizer 03_type_normalize.toml` → final.csv
