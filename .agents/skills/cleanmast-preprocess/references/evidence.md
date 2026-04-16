# Column Mapping Evidence — M4941 Reference Dataset

This document records the rationale for every channel decision in the M4941 NRG logger preprocessing.

## Kept Meteorological Columns

| Channel | Raw Column | Mapped Column | Height Source | Rationale |
|---|---|---|---|---|
| CH1 | CH1_NRG_40C_Anem_80m_Avg | Ch1_Anem_80.00m_Avg_m/s | Column name | Height 80m parsed directly from header |
| CH1 | CH1_NRG_40C_Anem_80m_SD | Ch1_Anem_80.00m_SD_m/s | Column name | Height 80m parsed directly from header |
| CH1 | CH1_NRG_40C_Anem_80m_Max | Ch1_Anem_80.00m_Max_m/s | Column name | Height 80m parsed directly from header |
| CH1 | CH1_NRG_40C_Anem_80m_Min | Ch1_Anem_80.00m_Min_m/s | Column name | Height 80m parsed directly from header |
| CH2 | CH2_NRG_40C_Anem_70m_Avg | Ch2_Anem_70.00m_Avg_m/s | Column name | Height 70m parsed directly from header |
| CH2 | CH2_NRG_40C_Anem_70m_SD | Ch2_Anem_70.00m_SD_m/s | Column name | Height 70m parsed directly from header |
| CH2 | CH2_NRG_40C_Anem_70m_Max | Ch2_Anem_70.00m_Max_m/s | Column name | Height 70m parsed directly from header |
| CH2 | CH2_NRG_40C_Anem_70m_Min | Ch2_Anem_70.00m_Min_m/s | Column name | Height 70m parsed directly from header |
| CH3 | CH3_NRG_40C_Anem_50m_Avg | Ch3_Anem_50.00m_Avg_m/s | Column name | Height 50m parsed directly from header |
| CH3 | CH3_NRG_40C_Anem_50m_SD | Ch3_Anem_50.00m_SD_m/s | Column name | Height 50m parsed directly from header |
| CH3 | CH3_NRG_40C_Anem_50m_Max | Ch3_Anem_50.00m_Max_m/s | Column name | Height 50m parsed directly from header |
| CH3 | CH3_NRG_40C_Anem_50m_Min | Ch3_Anem_50.00m_Min_m/s | Column name | Height 50m parsed directly from header |
| CH4 | CH4_NRG_40C_Anem_30m_Avg | Ch4_Anem_30.00m_Avg_m/s | Column name | Height 30m parsed directly from header |
| CH4 | CH4_NRG_40C_Anem_30m_SD | Ch4_Anem_30.00m_SD_m/s | Column name | Height 30m parsed directly from header |
| CH4 | CH4_NRG_40C_Anem_30m_Max | Ch4_Anem_30.00m_Max_m/s | Column name | Height 30m parsed directly from header |
| CH4 | CH4_NRG_40C_Anem_30m_Min | Ch4_Anem_30.00m_Min_m/s | Column name | Height 30m parsed directly from header |
| CH5 | CH5_NRG_40C_Anem_10m_Avg | Ch5_Anem_10.00m_Avg_m/s | Column name | Height 10m parsed directly from header |
| CH5 | CH5_NRG_40C_Anem_10m_SD | Ch5_Anem_10.00m_SD_m/s | Column name | Height 10m parsed directly from header |
| CH5 | CH5_NRG_40C_Anem_10m_Max | Ch5_Anem_10.00m_Max_m/s | Column name | Height 10m parsed directly from header |
| CH5 | CH5_NRG_40C_Anem_10m_Min | Ch5_Anem_10.00m_Min_m/s | Column name | Height 10m parsed directly from header |
| CH7 | CH7_NRG_200P_Vane_80m_Avg | Ch7_Vane_80.00m_Avg_Deg | Column name | Height 80m parsed directly from header |
| CH7 | CH7_NRG_200P_Vane_80m_SD | Ch7_Vane_80.00m_SD_Deg | Column name | Height 80m parsed directly from header |
| CH7 | CH7_NRG_200P_Vane_80m_Max | Ch7_Vane_80.00m_Max_Deg | Column name | Height 80m parsed directly from header |
| CH7 | CH7_NRG_200P_Vane_80m_Min | Ch7_Vane_80.00m_Min_Deg | Column name | Height 80m parsed directly from header |
| CH8 | CH8_NRG_200P_Vane_10m_Avg | Ch8_Vane_10.00m_Avg_Deg | Column name | Height 10m parsed directly from header |
| CH8 | CH8_NRG_200P_Vane_10m_SD | Ch8_Vane_10.00m_SD_Deg | Column name | Height 10m parsed directly from header |
| CH8 | CH8_NRG_200P_Vane_10m_Max | Ch8_Vane_10.00m_Max_Deg | Column name | Height 10m parsed directly from header |
| CH8 | CH8_NRG_200P_Vane_10m_Min | Ch8_Vane_10.00m_Min_Deg | Column name | Height 10m parsed directly from header |
| CH9 | CH9_NRG_110S_Temp_C_Avg | Ch9_Analog_10.00m_Avg_C | Metaheader | Column omits height; metaheader confirms 10m |
| CH9 | CH9_NRG_110S_Temp_C_SD | Ch9_Analog_10.00m_SD_C | Metaheader | Column omits height; metaheader confirms 10m |
| CH9 | CH9_NRG_110S_Temp_C_Max | Ch9_Analog_10.00m_Max_C | Metaheader | Column omits height; metaheader confirms 10m |
| CH9 | CH9_NRG_110S_Temp_C_Min | Ch9_Analog_10.00m_Min_C | Metaheader | Column omits height; metaheader confirms 10m |
| CH10 | CH10_NRG_BP20_Baro_kPa_Avg | Ch10_Analog_7.00m_Avg_kPa | Metaheader | Column omits height; metaheader confirms 7m |
| CH10 | CH10_NRG_BP20_Baro_kPa_SD | Ch10_Analog_7.00m_SD_kPa | Metaheader | Column omits height; metaheader confirms 7m |
| CH10 | CH10_NRG_BP20_Baro_kPa_Max | Ch10_Analog_7.00m_Max_kPa | Metaheader | Column omits height; metaheader confirms 7m |
| CH10 | CH10_NRG_BP20_Baro_kPa_Min | Ch10_Analog_7.00m_Min_kPa | Metaheader | Column omits height; metaheader confirms 7m |
| CH13 | CH13_NRG_40C_Anem_ms_Avg | Ch13_Anem_0.00m_Avg_m/s | Fallback 0.00m | No height in column; metaheader is 0/empty → info missing |
| CH13 | CH13_NRG_40C_Anem_ms_SD | Ch13_Anem_0.00m_SD_m/s | Fallback 0.00m | No height in column; metaheader is 0/empty → info missing |
| CH13 | CH13_NRG_40C_Anem_ms_Max | Ch13_Anem_0.00m_Max_m/s | Fallback 0.00m | No height in column; metaheader is 0/empty → info missing |
| CH13 | CH13_NRG_40C_Anem_ms_Min | Ch13_Anem_0.00m_Min_m/s | Fallback 0.00m | No height in column; metaheader is 0/empty → info missing |
| CH14 | CH14_NRG_40C_Anem_ms_Avg | Ch14_Anem_0.00m_Avg_m/s | Fallback 0.00m | No height in column; metaheader is 0/empty → info missing |
| CH14 | CH14_NRG_40C_Anem_ms_SD | Ch14_Anem_0.00m_SD_m/s | Fallback 0.00m | No height in column; metaheader is 0/empty → info missing |
| CH14 | CH14_NRG_40C_Anem_ms_Max | Ch14_Anem_0.00m_Max_m/s | Fallback 0.00m | No height in column; metaheader is 0/empty → info missing |
| CH14 | CH14_NRG_40C_Anem_ms_Min | Ch14_Anem_0.00m_Min_m/s | Fallback 0.00m | No height in column; metaheader is 0/empty → info missing |
| CH15 | CH15_NRG_40C_Anem_ms_Avg | Ch15_Anem_0.00m_Avg_m/s | Fallback 0.00m | No height in column; metaheader is 0/empty → info missing |
| CH15 | CH15_NRG_40C_Anem_ms_SD | Ch15_Anem_0.00m_SD_m/s | Fallback 0.00m | No height in column; metaheader is 0/empty → info missing |
| CH15 | CH15_NRG_40C_Anem_ms_Max | Ch15_Anem_0.00m_Max_m/s | Fallback 0.00m | No height in column; metaheader is 0/empty → info missing |
| CH15 | CH15_NRG_40C_Anem_ms_Min | Ch15_Anem_0.00m_Min_m/s | Fallback 0.00m | No height in column; metaheader is 0/empty → info missing |

## Dropped Non-Meteorological Columns

| Channel | Raw Column | Mapped Column | Height Source | Rationale |
|---|---|---|---|---|
| CH6 | CH6_No_SCM_Installed_Avg | DROPPED | N/A | Non-meteo diagnostic: no SIM card installed status |
| CH6 | CH6_No_SCM_Installed_SD | DROPPED | N/A | Non-meteo diagnostic: no SIM card installed status |
| CH6 | CH6_No_SCM_Installed_Max | DROPPED | N/A | Non-meteo diagnostic: no SIM card installed status |
| CH6 | CH6_No_SCM_Installed_Min | DROPPED | N/A | Non-meteo diagnostic: no SIM card installed status |
| CH11 | CH11_No_SCM_Installed_Avg | DROPPED | N/A | Non-meteo diagnostic: no SIM card installed status |
| CH11 | CH11_No_SCM_Installed_SD | DROPPED | N/A | Non-meteo diagnostic: no SIM card installed status |
| CH11 | CH11_No_SCM_Installed_Max | DROPPED | N/A | Non-meteo diagnostic: no SIM card installed status |
| CH11 | CH11_No_SCM_Installed_Min | DROPPED | N/A | Non-meteo diagnostic: no SIM card installed status |
| CH12 | CH12_iPack_Voltmtr_volts_Avg | DROPPED | N/A | Non-meteo diagnostic: iPack battery voltage |
| CH12 | CH12_iPack_Voltmtr_volts_SD | DROPPED | N/A | Non-meteo diagnostic: iPack battery voltage |
| CH12 | CH12_iPack_Voltmtr_volts_Max | DROPPED | N/A | Non-meteo diagnostic: iPack battery voltage |
| CH12 | CH12_iPack_Voltmtr_volts_Min | DROPPED | N/A | Non-meteo diagnostic: iPack battery voltage |
| CH13 | CH13_Custom_Avg | DROPPED | N/A | Non-meteo diagnostic: custom/logger placeholder (kept only NRG_40C_Anem_ms variant) |
| CH13 | CH13_Custom_SD | DROPPED | N/A | Non-meteo diagnostic: custom/logger placeholder (kept only NRG_40C_Anem_ms variant) |
| CH13 | CH13_Custom_Max | DROPPED | N/A | Non-meteo diagnostic: custom/logger placeholder (kept only NRG_40C_Anem_ms variant) |
| CH13 | CH13_Custom_Min | DROPPED | N/A | Non-meteo diagnostic: custom/logger placeholder (kept only NRG_40C_Anem_ms variant) |
| CH14 | CH14_Custom_Avg | DROPPED | N/A | Non-meteo diagnostic: custom/logger placeholder (kept only NRG_40C_Anem_ms variant) |
| CH14 | CH14_Custom_SD | DROPPED | N/A | Non-meteo diagnostic: custom/logger placeholder (kept only NRG_40C_Anem_ms variant) |
| CH14 | CH14_Custom_Max | DROPPED | N/A | Non-meteo diagnostic: custom/logger placeholder (kept only NRG_40C_Anem_ms variant) |
| CH14 | CH14_Custom_Min | DROPPED | N/A | Non-meteo diagnostic: custom/logger placeholder (kept only NRG_40C_Anem_ms variant) |
| CH15 | CH15_Custom_Avg | DROPPED | N/A | Non-meteo diagnostic: custom/logger placeholder (kept only NRG_40C_Anem_ms variant) |
| CH15 | CH15_Custom_SD | DROPPED | N/A | Non-meteo diagnostic: custom/logger placeholder (kept only NRG_40C_Anem_ms variant) |
| CH15 | CH15_Custom_Max | DROPPED | N/A | Non-meteo diagnostic: custom/logger placeholder (kept only NRG_40C_Anem_ms variant) |
| CH15 | CH15_Custom_Min | DROPPED | N/A | Non-meteo diagnostic: custom/logger placeholder (kept only NRG_40C_Anem_ms variant) |
