# Mast Column Header Rename Guide

This guide provides a systematic approach to convert various mast data column header formats to the standardized NRG format, making them compatible with the CleanMast project's sensor parsing system. This step should be performed **before** running `project parse-sensors`.

## Overview

Different mast data sources use different column naming conventions:
- **NRG format**: `Ch1_Anem_120.00m_NW_Avg_m/s` (already compatible)
- **Windographer format**: `Spd 130m [m/s]`, `Dir 130m [°]` (needs conversion)
- **Other formats**: Various custom naming schemes (needs conversion)

The goal is to convert all formats to the standardized NRG format so they can be processed by the existing `project parse-sensors` system.

## 1. Target NRG Column Header Format

All mast data should be converted to follow the NRG standardized patterns:

### 1.1 Standard Format Pattern
```
Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}
```

### 1.2 Alternative Format Pattern (without direction)
```
Ch{channel}_{sensorType}_{height}m_{statType}_{unit}
```

### 1.3 Component Definitions

| Component | Description | Examples |
|-----------|-------------|----------|
| `{channel}` | Sequential channel number (assign systematically) | `1`, `2`, `3`, `13`, `14` |
| `{sensorType}` | Sensor type identifier | `Anem`, `Vane`, `Analog` |
| `{height}` | Height in meters (with decimals) | `130.00`, `110.00`, `90.00`, `70.00`, `10.00` |
| `{sensorDirection}` | Sensor direction (optional, assign if known) | `A`, `B`, `N`, `NW`, `SE` |
| `{statType}` | Statistical type | `Avg`, `SD`, `Min`, `Max`, `Gust`, `GustDir` |
| `{unit}` | Unit of measurement | `m/s`, `Deg`, `C`, `kPa`, `%RH` |

### 1.4 Expected Sensor Type Mappings

The system will automatically map these sensor types during parsing:

| Raw Type | Mapped Type | Unit | Description |
|----------|-------------|------|-------------|
| `Anem` | `WindSpeed` | `m/s` | Anemometer wind speed |
| `Vane` | `WindDirection` | `deg` | Wind vane direction |
| `Analog` + `C` | `Temperature` | `C` | Temperature sensor |
| `Analog` + `kPa` | `Pressure` | `Pa` | Pressure sensor (converted) |
| `Analog` + `%RH` | `Humidity` | `%RH` | Humidity sensor |

## 2. Common Input Formats and Conversion Examples

### 2.1 Windographer Format (e.g., BY-2501)

**Original Format:**
```
Spd 130m [m/s], Spd 130m SD [m/s], Spd 130m Max [m/s]
Dir 130m [°], Dir 130m SD [°]
RH 10m [%], AT_1_10m_Avg
```

**Converted to NRG Format:**
```
Ch1_Anem_130.00m_Avg_m/s, Ch1_Anem_130.00m_SD_m/s, Ch1_Anem_130.00m_Max_m/s
Ch13_Vane_130.00m_Avg_Deg, Ch13_Vane_130.00m_SD_Deg
Ch15_Analog_10.00m_Avg_%RH, Ch16_Analog_10.00m_Avg_C
```

### 2.2 Generic Format Examples

**Speed/Direction Format:**
```
WS_80m_avg, WS_80m_std, WD_80m_avg
→ Ch1_Anem_80.00m_Avg_m/s, Ch1_Anem_80.00m_SD_m/s, Ch2_Vane_80.00m_Avg_Deg
```

**Height-First Format:**
```
80m_WindSpeed_Mean, 80m_WindDirection_Mean
→ Ch1_Anem_80.00m_Avg_m/s, Ch2_Vane_80.00m_Avg_Deg
```

## 3. Conversion Process Steps

### 3.1 Analyze the Input Format

1. **Examine the header line** in your raw mast file (`.txt`, `.csv`, etc.)
2. **Identify the naming pattern** used for columns
3. **Map the components** to NRG format elements

**Common patterns to look for:**
```bash
# Search for header lines with various patterns
grep -n "Timestamp" your-mast-file.csv
grep -n "Spd.*m" your-mast-file.csv  # Windographer style
grep -n "WS_.*m" your-mast-file.csv  # Generic wind speed
```

**Example input formats:**
```
# Windographer format
Timestamp (UTC),Spd 130m [m/s],Dir 130m [°],RH 10m [%]

# Generic format
Timestamp,WS_80m_avg,WD_80m_avg,Temp_10m

# Already NRG format (no conversion needed)
Timestamp,Ch1_Anem_120.00m_NW_Avg_m/s,Ch13_Vane_118.00m_N_Avg_Deg
```

### 3.2 Create Channel Assignment Strategy

Assign sequential channel numbers to different sensor types and heights:

**Channel Assignment Guidelines:**
- **Channels 1-12**: Wind speed sensors (Anemometers) by height (highest first)
- **Channels 13-20**: Wind direction sensors (Vanes) by height
- **Channels 21-30**: Environmental sensors (Temperature, Pressure, Humidity)

**Example Channel Assignment:**
```
Ch1_Anem_130.00m_Avg_m/s     # Highest wind speed sensor
Ch2_Anem_110.00m_Avg_m/s     # Next highest wind speed
Ch3_Anem_90.00m_Avg_m/s      # Continue by height
...
Ch13_Vane_130.00m_Avg_Deg    # Highest wind direction sensor
Ch14_Vane_70.00m_Avg_Deg     # Next wind direction sensor
...
Ch21_Analog_10.00m_Avg_C     # Temperature sensor
Ch22_Analog_10.00m_Avg_%RH   # Humidity sensor
```

### 3.3 Generate rename-mapping.{input-basename}.toml

**IMPORTANT**: Always create a `rename-mapping.{input-basename}.toml` file in the same directory as your raw mast data. This file documents the conversion and can be used for reference or automation.

**Naming Convention**: Use `rename-mapping.{input-basename}.toml` to avoid name conflicts when processing multiple files in the same directory.

Example: For `2501_windographer.csv`, create `rename-mapping.2501_windographer.toml`

**Template for Windographer Format:**
```toml
# Rename mapping configuration for mast data headers
# Generated for: 2501_windographer.csv
# Format: Windographer → NRG
# Created: 2025-08-18

[header_info]
source_file = "2501_windographer.csv"
header_line = 1
timestamp_column = "Timestamp (UTC)"
converted_file = "2501_windographer.csv"  # File was edited in-place

# Column name mappings from Windographer format to NRG format
[column_mappings]
"Timestamp (UTC)" = "Timestamp"

# Wind Speed Sensors (Anemometers)
"Spd 130m [m/s]" = "Ch1_Anem_130.00m_Avg_m/s"
"Spd 130m SD [m/s]" = "Ch1_Anem_130.00m_SD_m/s"
"Spd 130m Max [m/s]" = "Ch1_Anem_130.00m_Max_m/s"
"Spd 110m [m/s]" = "Ch2_Anem_110.00m_Avg_m/s"
"Spd 110m SD [m/s]" = "Ch2_Anem_110.00m_SD_m/s"
"Spd 110m Max [m/s]" = "Ch2_Anem_110.00m_Max_m/s"
"Spd 90m [m/s]" = "Ch3_Anem_90.00m_Avg_m/s"
"Spd 90m SD [m/s]" = "Ch3_Anem_90.00m_SD_m/s"
"Spd 90m Max [m/s]" = "Ch3_Anem_90.00m_Max_m/s"
"Spd 70m [m/s]" = "Ch4_Anem_70.00m_Avg_m/s"
"Spd 70m SD [m/s]" = "Ch4_Anem_70.00m_SD_m/s"
"Spd 70m Max [m/s]" = "Ch4_Anem_70.00m_Max_m/s"
"Spd 50m [m/s]" = "Ch5_Anem_50.00m_Avg_m/s"
"Spd 50m SD [m/s]" = "Ch5_Anem_50.00m_SD_m/s"
"Spd 50m Max [m/s]" = "Ch5_Anem_50.00m_Max_m/s"
"Spd 30m [m/s]" = "Ch6_Anem_30.00m_Avg_m/s"
"Spd 30m SD [m/s]" = "Ch6_Anem_30.00m_SD_m/s"
"Spd 30m Max [m/s]" = "Ch6_Anem_30.00m_Max_m/s"
"Spd 15m [m/s]" = "Ch7_Anem_15.00m_Avg_m/s"
"Spd 15m SD [m/s]" = "Ch7_Anem_15.00m_SD_m/s"
"Spd 15m Max [m/s]" = "Ch7_Anem_15.00m_Max_m/s"

# Wind Direction Sensors (Vanes)
"Dir 130m [°]" = "Ch13_Vane_130.00m_Avg_Deg"
"Dir 130m SD [°]" = "Ch13_Vane_130.00m_SD_Deg"
"Dir 70m [°]" = "Ch14_Vane_70.00m_Avg_Deg"
"Dir 70m SD [°]" = "Ch14_Vane_70.00m_SD_Deg"
"Dir 15m [°]" = "Ch15_Vane_15.00m_Avg_Deg"
"Dir 15m SD [°]" = "Ch15_Vane_15.00m_SD_Deg"
"Dir 10m A [°]" = "Ch16_Vane_10.00m_A_Avg_Deg"
"Dir 10m B [°]" = "Ch17_Vane_10.00m_B_Avg_Deg"

# Environmental Sensors
"RH 10m [%]" = "Ch21_Analog_10.00m_Avg_%RH"
"AT_1_10m_Avg" = "Ch22_Analog_10.00m_Avg_C"
"AT_1_10m_Std" = "Ch22_Analog_10.00m_SD_C"

# Other columns (keep as-is or skip if not needed for wind analysis)
"BattV [V]" = "Ch30_Batt_0.00m_Avg_V"
```

### 3.4 Create the rename-mapping file

**ALWAYS create the rename-mapping file** in the same directory as your input data:

```bash
# Create the mapping file with proper naming convention
touch rename-mapping.{input-basename}.toml
```

**Example for BY-2501 data:**
```bash
# For file: 2501_windographer.csv
# Create: rename-mapping.2501_windographer.toml
```

### 3.5 Apply rename-mapping.toml

Apply the column renaming using the mapping file to create a standardized version of your raw data.

**Implementation options:**

1. **Script-based renaming** (recommended for larger files)
2. **Manual editing** (for small files)
3. **Text editor find/replace** (for moderate files)

**Example Python script for applying mappings:**
```python
import pandas as pd
import toml

# Load the mapping configuration (use proper filename)
mapping_file = 'rename-mapping.2501_windographer.toml'
with open(mapping_file, 'r') as f:
    config = toml.load(f)

# Read the original data
df = pd.read_csv(config['header_info']['source_file'])

# Apply column renaming
df = df.rename(columns=config['column_mappings'])

# Save the converted file
output_file = config['header_info']['source_file'].replace('.csv', '_nrg.csv')
df.to_csv(output_file, index=False)
print(f"Converted file saved as: {output_file}")
```

## 4. Integration with parse-sensors

After completing the header conversion:

1. **Verify the converted headers** match the NRG format patterns
2. **Create or update parse-sensors.toml** to reference the converted file
3. **Run the parse-sensors command** as normal:
   ```bash
   julia bin/CleanMast.jl process parse-sensors your-project/parse-sensors.toml
   ```

**Example parse-sensors.toml for converted data:**
```toml
[[masts]]
input = "2501_windographer_nrg.csv"  # The converted file
name = "by-2501"
sensor = "formats/sensor/nrg.toml"   # Use standard NRG sensor format
```

The system will then:
- Parse the standardized NRG column headers
- Apply sensor type mappings (Anem → WindSpeed, Vane → WindDirection, etc.)
- Generate normalized CSV output with clean column names like `WindSpeed_130m_avg [m/s]`
- Create sensor metadata files for downstream processing

## 5. Format-Specific Conversion Guidelines

### 5.1 Windographer Format Conversion

**Pattern Recognition:**
- Speed: `Spd {height}m [m/s]` → `Ch{N}_Anem_{height}.00m_Avg_m/s`
- Direction: `Dir {height}m [°]` → `Ch{N}_Vane_{height}.00m_Avg_Deg`
- Statistics: `SD` → `SD`, `Max` → `Max`

### 5.2 Generic Format Conversion

**Common Patterns:**
- `WS_{height}m` → `Ch{N}_Anem_{height}.00m_Avg_m/s`
- `WD_{height}m` → `Ch{N}_Vane_{height}.00m_Avg_Deg`
- `Temp_{height}m` → `Ch{N}_Analog_{height}.00m_Avg_C`

### 5.3 Custom Format Guidelines

For other formats:
1. **Identify sensor types**: Wind speed, direction, temperature, pressure, humidity
2. **Extract heights**: Convert to decimal format (e.g., `80` → `80.00`)
3. **Map statistics**: avg/mean → Avg, std/sd → SD, max → Max, min → Min
4. **Assign channels**: Follow the channel assignment strategy
5. **Standardize units**: Ensure units match NRG format exactly

## 6. Quality Assurance

### 6.1 Header Validation Checklist

- [ ] All channel numbers are assigned systematically
- [ ] Height values include decimal places (e.g., `130.00m` not `130m`)
- [ ] Sensor directions are consistent (A, B, N, NW, SE, etc.)
- [ ] Statistical types use proper case (Avg, SD, Min, Max, Gust)
- [ ] Units are correctly formatted (m/s, Deg, C, kPa, %RH)
- [ ] Timestamp column is standardized as "Timestamp"
- [ ] Channel assignments follow logical grouping (speeds 1-12, directions 13-20, etc.)

### 6.2 Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| Missing decimal in height | Change `130m` to `130.00m` |
| Inconsistent direction naming | Use A, B for dual sensors; N, NW, SE for compass directions |
| Wrong case in stat types | Use: Avg, SD, Min, Max, Gust, GustDir |
| Unit formatting | Use: m/s, Deg, C, kPa, %RH (exact format) |
| Missing channel prefix | Add `Ch` prefix to all channel numbers |
| Irregular channel numbering | Follow systematic assignment: 1-12 speeds, 13-20 directions, 21+ environmental |

### 6.3 Verification Steps

1. **Check converted file** has proper NRG format headers
2. **Verify rename-mapping.{input-basename}.toml** was created and contains complete mappings
3. **Test with parse-sensors** to ensure compatibility
4. **Verify output** produces expected normalized column names
5. **Compare data integrity** between original and converted files

### 6.4 Required Deliverables

For each conversion, ensure you have created:
- [ ] **Converted data file** with NRG format headers
- [ ] **rename-mapping.{input-basename}.toml** documenting the conversion
- [ ] **Verification** that the file works with parse-sensors

This conversion process enables any mast data format to be processed through the standardized CleanMast sensor parsing pipeline, ensuring consistent data processing for wind analysis workflows.
