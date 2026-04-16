# Post-Merge Self-Check Checklist

Use this checklist after running `csv-merge` and before proceeding to column normalization.

## 1. Verify merged file integrity
- [ ] The merged CSV exists and is not empty
- [ ] A `Timestamp` column is present and sorted chronologically
- [ ] Row count is roughly the sum of all input files (minus duplicates/headers)

## 2. Inspect the full column list
- [ ] Run `head -n 1 merged.csv | tr ',' '\n' | sort` to see every column
- [ ] Identify any unexpected columns (e.g. `Custom_*`, `No_SCM_Installed_*`, `iPack_Voltmtr_*`)

## 3. Detect column mismatches across raw files
- [ ] Check for channels that appear with two different names (e.g. `CH13_Custom_Avg` vs `CH13_NRG_40C_Anem_ms_Avg`)
- [ ] Confirm `column_mismatch = "union"` was used if mismatches exist
- [ ] Decide which variant represents the real sensor and map only that one

## 4. Identify non-meteorological columns to drop
Drop these categories from the final dataset:
- [ ] `CH*_No_SCM_Installed_*` — SIM / logger status
- [ ] `CH*_iPack_Voltmtr_volts_*` — battery voltage
- [ ] `CH*_Custom_*` — custom/logger diagnostic placeholders

## 5. Validate sensor configuration
- [ ] Cross-check each `CH{ N }_` channel against the site sensor configuration
- [ ] Verify sensor types (Anem, Vane, Analog) match the physical instruments
- [ ] Verify heights independently — do not assume anemometer height for temperature or other analog sensors
- [ ] **Resolve height using the precedence rule:**
  1. **Tabular column header** — if the column name contains a height (e.g. `80m`), use it
  2. **NRG metaheader** — if the column name omits height, inspect `head -n 170 raw_file.txt | grep -A 6 "Channel #\tN"` and look for `Height\tX`
  3. **Fallback `0.00m`** — if both sources lack a real height, use `0.00m` (meaning "height information missing")
- [ ] Treat metaheader `Height\t0` as "not configured" unless an independent source confirms the sensor is truly at ground level
- [ ] If metaheaders are unavailable, look up the height from the site logger configuration sheet

## 6. Write `evidence.md`
After deciding mappings, produce `evidence.md` with a markdown table covering every channel:
- [ ] Columns kept as meteorological data: `Raw Column`, `Mapped Column`, `Height Source`, `Rationale`
- [ ] Columns dropped as non-meteo: `Raw Column`, `DROPPED`, `N/A`, one-sentence rationale
- [ ] `Height Source` values are correct: `Column name`, `Metaheader`, `Fallback 0.00m`, or `N/A`

## 7. Prepare column mappings
- [ ] Every kept column has a target name in standard NRG format: `Ch{channel}_{sensorType}_{height}m_{statType}_{unit}`
- [ ] Height uses two decimal places (e.g. `80.00m`, `10.00m`, `0.00m`)
- [ ] No unmapped columns will remain if `keep_unmapped = false` is used

## 8. Final verification after normalization
- [ ] Output columns match mapping targets exactly (plus `Timestamp`)
- [ ] Dropped non-meteo columns are absent
- [ ] All numeric columns are Float64 after `type-normalizer`
- [ ] `evidence.md` is present and consistent with the actual mapping
