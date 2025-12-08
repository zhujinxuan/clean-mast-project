# Lidar Data Format Reference

This document describes the standardized format for WindCube lidar measurement data.

## Overview

The Lidar format provides a standardized way to organize WindCube lidar data, making it compatible with downstream wind resource analysis systems. This format handles the unique characteristics of lidar measurements including multiple height levels, vertical wind components, signal quality metrics, and data availability tracking.

## Input Format: WindCube .sta Files

WindCube lidar systems produce `.sta` files with the following structure:

### File Structure
1. **Metadata Header (40 lines)**: System configuration, GPS location, measurement parameters
2. **Column Headers (1 line)**: Tab-delimited, very long header with repeating patterns per height
3. **Data Rows**: Tab-delimited time series with 10-minute averages

### Key Characteristics
- **Delimiter**: Tab (`\t`)
- **Timestamp Format**: `YYYY/MM/DD HH:MM` (e.g., `2023/04/28 00:10`)
- **Interval**: 10-minute averages
- **Missing Values**: `NaN`
- **Heights**: Variable, defined in metadata (e.g., 40, 50, 70, 80, 90, 100, 110, 120, 130, 140, 150, 180m)

### Measurements Per Height Level
- Wind Speed (average, dispersion, min, max)
- Wind Direction (average)
- Z-wind / Vertical Wind (average, dispersion)
- CNR - Carrier-to-Noise Ratio (average, min)
- Doppler Spectral Broadening (average)
- Data Availability (percentage)

## Standardized Output Format

### Primary Pattern
```
Lidar_{height}.00m_{measurement}_{statType}_{unit}
```

### System-Level Pattern
```
{measurementName}_{unit}
```

## Component Definitions

| Component | Description | Examples |
|-----------|-------------|----------|
| `{height}` | Height in meters (with 2 decimals) | `40.00`, `50.00`, `70.00`, `140.00`, `180.00` |
| `{measurement}` | Measurement type | `WindSpeed`, `WindDirection`, `ZWind`, `CNR`, `DoppSpectBroad`, `DataAvailability` |
| `{statType}` | Statistical type | `Avg`, `SD`, `Min`, `Max` |
| `{unit}` | Unit of measurement | `m/s`, `Deg`, `dB`, `%`, `C`, `hPa`, `V` |

## Measurement Type Definitions

| Measurement | Description | Available Stats | Unit |
|-------------|-------------|-----------------|------|
| `WindSpeed` | Horizontal wind speed | Avg, SD, Min, Max | `m/s` |
| `WindDirection` | Wind direction | Avg | `Deg` |
| `ZWind` | Vertical wind component | Avg, SD | `m/s` |
| `CNR` | Carrier-to-Noise Ratio (signal quality) | Avg, Min | `dB` |
| `DoppSpectBroad` | Doppler Spectral Broadening | Avg | `m/s` |
| `DataAvailability` | Data availability percentage | Value | `%` |

## System Measurements

System-level measurements (one value per timestamp):

| Original Name | Standardized Name | Unit | Notes |
|---------------|-------------------|------|-------|
| `Timestamp (end of interval)` | `Timestamp` | `YYYY-MM-DD HH:MM:SS` | |
| `Int Temp (°C)` | `IntTemp_C` | `C` | Internal temperature, keep as-is |
| `Ext Temp (°C)` | `Lidar_1m_Temperature_C` | `C` | **Rename to Lidar format** (external temp ≈ 1m height) |
| `Pressure (hPa)` | `Lidar_1m_Pressure_hPa` | `hPa` | **Rename to Lidar format** (ground level ≈ 1m height) |
| `Rel Humidity (%)` | `RelHumidity_%` | `%` | |
| `Wiper count` | `WiperCount` | (count) | No unit, skip during parsing |
| `Vbatt (V)` | `Vbatt_V` | `V` | |

**Important**: External temperature and pressure are measured at or near ground level (effectively ~1m height). To ensure compatibility with the Lidar column pattern `Lidar_{height}m_{measurement}_{unit}`, these should be renamed to follow the standardized format.

## Example Conversions

### Wind Speed Measurements
```
Original: 40m WindSpeed (m/s)
Output:   Lidar_40.00m_WindSpeed_Avg_m/s

Original: 40m WindSpeed Dispersion (m/s)
Output:   Lidar_40.00m_WindSpeed_SD_m/s

Original: 40m WindSpeed min (m/s)
Output:   Lidar_40.00m_WindSpeed_Min_m/s

Original: 40m WindSpeed max (m/s)
Output:   Lidar_40.00m_WindSpeed_Max_m/s
```

### Wind Direction
```
Original: 40m WindDirection (°)
Output:   Lidar_40.00m_WindDirection_Avg_Deg
```

### Vertical Wind (Z-wind)
```
Original: 40m ZWind (m/s)
Output:   Lidar_40.00m_ZWind_Avg_m/s

Original: 40m ZWind Dispersion (m/s)
Output:   Lidar_40.00m_ZWind_SD_m/s
```

### Signal Quality (CNR)
```
Original: 40m CNR (dB)
Output:   Lidar_40.00m_CNR_Avg_dB

Original: 40m CNR min (dB)
Output:   Lidar_40.00m_CNR_Min_dB
```

### Other Measurements
```
Original: 40m DoppSpectBroad (m/s)
Output:   Lidar_40.00m_DoppSpectBroad_Avg_m/s

Original: 40m DataAvailability (%)
Output:   Lidar_40.00m_DataAvailability_%
```

### System Measurements
```
Original: Timestamp (end of interval)
Output:   Timestamp

Original: Int Temp (°C)
Output:   IntTemp_C

Original: Ext Temp (°C)
Output:   Lidar_1m_Temperature_C

Original: Pressure (hPa)
Output:   Lidar_1m_Pressure_hPa

Original: Rel Humidity (%)
Output:   RelHumidity_%

Original: Wiper count
Output:   WiperCount

Original: Vbatt (V)
Output:   Vbatt_V
```

## Column Organization

Recommended column order in standardized output:

1. **Timestamp** (first column)
2. **System measurements** (IntTemp, Lidar_1m_Temperature, Lidar_1m_Pressure, RelHumidity, WiperCount, Vbatt)
3. **Height-based measurements** (grouped by height, lowest to highest):
   - For each height: WindSpeed (Avg, SD, Min, Max), WindDir, ZWind (Avg, SD), CNR (Avg, Min), DoppSpectBroad, DataAvail

## Statistical Type Conventions

- `Avg` - Average/Mean value
- `SD` - Standard deviation (maps from "Dispersion" in original format)
- `Min` - Minimum value
- `Max` - Maximum value

**Note**: Lidar "Dispersion" is equivalent to standard deviation and should be converted to `SD`.

## Unit Conventions

- Wind speed (horizontal and vertical): `m/s`
- Wind direction: `Deg`
- Temperature: `C`
- Pressure: `hPa`
- Humidity: `%`
- Voltage: `V`
- CNR: `dB` (can be negative)
- Data Availability: `%`

## Data Quality Indicators

### CNR (Carrier-to-Noise Ratio)
- **Range**: Typically -25 to +10 dB
- **Good signal**: > -10 dB
- **Marginal signal**: -20 to -10 dB
- **Poor signal**: < -20 dB
- Used to assess measurement reliability

### Data Availability
- **Range**: 0-100%
- **Good**: 100% or close to it
- **Degraded**: < 80%
- Indicates how much of the 10-minute period had valid measurements

## Quality Assurance Checklist

- [ ] Height values include 2 decimal places (e.g., `40.00m`)
- [ ] Statistical types use proper case (`Avg`, `SD`, `Min`, `Max`)
- [ ] Units are correctly formatted (`m/s`, `Deg`, `dB`, `%`, `C`, `hPa`)
- [ ] Timestamp is standardized to `YYYY-MM-DD HH:MM:SS` format
- [ ] "Dispersion" converted to `SD` (standard deviation)
- [ ] System measurements use standardized names
- [ ] All height levels present in data are included
- [ ] Column order follows recommended structure

## Differences from NRG Format

| Aspect | NRG Format | Lidar Format |
|--------|------------|--------------|
| **Prefix** | `Ch{N}_` (channel-based) | `Lidar_` (instrument-based) |
| **Structure** | Single sensor per channel | Multiple measurements per height |
| **Unique Measurements** | None | Z-wind, CNR, DoppSpectBroad, DataAvail |
| **Delimiter** | Comma | Tab (input), Comma (output) |
| **Vertical Wind** | Not included | Included as ZWind |
| **Signal Quality** | Not included | Included as CNR |

## Notes

- Lidar data is fundamentally different from traditional mast data
- Multiple measurement types exist at each height level
- Signal quality (CNR) is critical for data validation
- Vertical wind component provides additional atmospheric information
- Data availability tracking is built into the format
