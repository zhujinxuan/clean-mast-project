# NRG Column Header Format Reference

## Primary Pattern

```
Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}
```

## Component Definitions

| Component | Description | Examples |
|-----------|-------------|----------|
| channel | Sequential channel number | 1, 2, 13 |
| sensorType | Sensor type identifier | Anem, Vane, Analog |
| height | Height in meters with decimals | 80.00, 130.00 |
| sensorDirection | Direction (optional) | A, B, N |
| statType | Statistical type | Avg, SD, Min, Max |
| unit | Unit of measurement | m/s, Deg, C, hPa |

## Direction (sensorDirection)

The direction field is **positioned between height and statType**:
`Ch{channel}_{sensorType}_{height}m_{sensorDirection}_{statType}_{unit}`

### How to Determine Direction

1. **If the original column name has a direction suffix** → use it directly.
   - `@140mT` → direction `T`
   - `@140mB` → direction `B`
2. **If the original column name has no direction suffix** → use default scheme:
   - Single sensor at height → `A` (main/primary)
   - Duplicate sensor type at same height → `A` for the one without suffix, `T` for the one with suffix

| Direction | Source | Meaning |
|-----------|--------|---------|
| `A` | No suffix in original name | Main / primary (default) |
| `T` | Original name has `T` suffix | Secondary / top |
| `B` | Original name has `B` suffix | Secondary / bottom |

## Example Conversions

```
# No direction suffix → default "A"
CH1_NRG_40C_Anem_80m_Avg          -> Ch1_Anem_80.00m_A_Avg_m/s
CH7_NRG_200P_Vane_80m_Avg         -> Ch7_Vane_80.00m_A_Avg_Deg
CH9_NRG_110S_Temp_C_Avg           -> Ch9_Analog_10.00m_A_Avg_C

# Direction "T" from original suffix
Anemomete@140mT;wind_speed;Avg    -> Ch2_Anem_140.00m_T_Avg_m/s

# Same height, different directions
Anemomete@140m;wind_speed;Avg     -> Ch1_Anem_140.00m_A_Avg_m/s
Anemomete@140mT;wind_speed;Avg    -> Ch2_Anem_140.00m_T_Avg_m/s

# All other sensors default to "A"
Wind Vane@140m;wind_direction;Avg -> Ch13_Vane_140.00m_A_Avg_Deg
Wind Vane@100m;wind_direction;Avg -> Ch14_Vane_100.00m_A_Avg_Deg
Temperature@10m;temperature;Avg   -> Ch21_Analog_10.00m_A_Avg_C
```
