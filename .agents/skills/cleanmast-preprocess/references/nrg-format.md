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

## Example Conversions

```
CH1_NRG_40C_Anem_80m_Avg -> Ch1_Anem_80.00m_Avg_m/s
CH7_NRG_200P_Vane_80m_Avg -> Ch7_Vane_80.00m_Avg_Deg
CH9_NRG_110S_Temp_C_Avg -> Ch9_Analog_10.00m_Avg_C
```
