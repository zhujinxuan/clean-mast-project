# kp-202603-report

Report generation experiment using lidar and mast measurement data from 康平 (Kangping) wind farm.

- **Mast data**: L32261, M245228 (120m–200m sensor heights)
- **Meso/Lidar data**: ERA5Lidar (100m)
- **Purpose**: Generate representative timeseries report analysis (PDF)

## Usage

```bash
just verify    # dvc pull → recommend config → generate report → check output
```
