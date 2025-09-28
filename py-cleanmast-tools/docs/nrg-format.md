# NRG Column Header Format Reference

This document describes the standardized NRG format used for mast data column headers.

## Overview

The NRG format provides a standardized way to name columns in mast data files, making them compatible with downstream processing systems. This format ensures consistent interpretation of sensor data across different data sources.

## Standard Format Patterns

### Primary Pattern (with direction)
```
Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}
```

### Alternative Pattern (without direction)
```
Ch{channel}_{sensorType}_{height}m_{statType}_{unit}
```

## Component Definitions

| Component | Description | Examples |
|-----------|-------------|----------|
| `{channel}` | Sequential channel number | `1`, `2`, `3`, `13`, `14` |
| `{sensorType}` | Sensor type identifier | `Anem`, `Vane`, `Analog` |
| `{height}` | Height in meters (with decimals) | `130.00`, `110.00`, `90.00`, `70.00`, `10.00` |
| `{sensorDirection}` | Sensor direction (optional) | `A`, `B`, `N`, `NW`, `SE` |
| `{statType}` | Statistical type | `Avg`, `SD`, `Min`, `Max`, `Gust`, `GustDir` |
| `{unit}` | Unit of measurement | `m/s`, `Deg`, `C`, `kPa`, `%RH` |

## Channel Assignment Strategy

Channels should be assigned systematically by sensor type and height:

- **Channels 1-12**: Wind speed sensors (Anemometers) by height (highest first)
- **Channels 13-20**: Wind direction sensors (Vanes) by height
- **Channels 21-30**: Environmental sensors (Temperature, Pressure, Humidity)
- **Channel 30+**: System/utility sensors (Battery voltage, etc.)

## Sensor Type Mappings

| Raw Type | Mapped Type | Unit | Description |
|----------|-------------|------|-------------|
| `Anem` | `WindSpeed` | `m/s` | Anemometer wind speed |
| `Vane` | `WindDirection` | `deg` | Wind vane direction |
| `Analog` + `C` | `Temperature` | `C` | Temperature sensor |
| `Analog` + `kPa` | `Pressure` | `kPa` | Pressure sensor |
| `Analog` + `%RH` | `Humidity` | `%RH` | Humidity sensor |

## Example Conversions

### Wind Speed Sensors
```
Original: WS_130m_Avg, WS_130m_Std, WS_130m_Max
NRG:      Ch1_Anem_130.00m_Avg_m/s, Ch1_Anem_130.00m_SD_m/s, Ch1_Anem_130.00m_Max_m/s
```

### Wind Direction Sensors
```
Original: WD_130m_Avg, WD_130m_Std
NRG:      Ch13_Vane_130.00m_Avg_Deg, Ch13_Vane_130.00m_SD_Deg
```

### Environmental Sensors
```
Original: AT_1_10m_Avg, RH_1_10m_Avg
NRG:      Ch21_Analog_10.00m_Avg_C, Ch22_Analog_10.00m_Avg_%RH
```

### System Sensors
```
Original: Batt_Volt
NRG:      Ch30_Analog_0.00m_Avg_V
```

## Statistical Type Conventions

- `Avg` - Average/Mean value
- `SD` - Standard deviation (not `Std`)
- `Min` - Minimum value
- `Max` - Maximum value
- `Gust` - Gust speed (for wind)
- `GustDir` - Gust direction (for wind)

## Unit Conventions

- Wind speed: `m/s`
- Wind direction: `Deg`
- Temperature: `C`
- Pressure: `kPa`
- Humidity: `%RH`
- Voltage: `V`

## Quality Assurance Checklist

- [ ] Channel numbers are assigned systematically
- [ ] Height values include decimal places (e.g., `130.00m`)
- [ ] Statistical types use proper case (`Avg`, `SD`, `Min`, `Max`)
- [ ] Units are correctly formatted (`m/s`, `Deg`, `C`, `kPa`, `%RH`)
- [ ] Timestamp column is standardized as "Timestamp"
- [ ] Channel assignments follow logical grouping
