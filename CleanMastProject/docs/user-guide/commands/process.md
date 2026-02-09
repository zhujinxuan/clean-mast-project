# process clean

## Syntax
```bash
julia bin/CleanMast.jl process clean <config_path>
```

## Arguments
- `config_path`: Path to the config.yaml configuration file.

## Description
Clean data using configured rules.

---

# process tower-shading

## Syntax
```bash
julia bin/CleanMast.jl process tower-shading <config_path>
```

## Arguments
- `config_path`: Path to the config.yaml configuration file.

## Description
Apply tower shading detection and correction.

---

# process reconstruct-single

## Syntax
```bash
julia bin/CleanMast.jl process reconstruct-single <config_path>
```

## Arguments
- `config_path`: Path to the reconstruct-single.toml configuration file.

## Description
Reconstruct missing data using single mast data.

---

# process train-meso

## Syntax
```bash
julia bin/CleanMast.jl process train-meso <config_path>
```

## Arguments
- `config_path`: Path to the train-meso.toml configuration file.

## Description
Train mast and meso linear correlation models.

---

# process reconstruct-meso

## Syntax
```bash
julia bin/CleanMast.jl process reconstruct-meso <config_path>
```

## Arguments
- `config_path`: Path to the reconstruct-meso.toml configuration file.

## Description
Reconstruct missing data using trained mesoscale models.

---

# process representative-year

## Syntax
```bash
julia bin/CleanMast.jl process representative-year <config_path>
```

## Arguments
- `config_path`: Path to the representative-year.toml configuration file.

## Description
Calibrate data to a representative year.

---

# process wt-timeseries

## Syntax
```bash
julia bin/CleanMast.jl process wt-timeseries <config_path>
```

## Arguments
- `config_path`: Path to the wt-timeseries.toml configuration file.

## Description
Process wind turbine time series data. Extracts wind speed and direction data at target heights from representative year data. Saves timestamp, wind speed, and wind direction to CSV files.

---

# process reconstruct-cross

## Syntax
```bash
julia bin/CleanMast.jl process reconstruct-cross <config_path>
```

## Arguments
- `config_path`: Path to the reconstruct-cross.toml configuration file.

## Description
Execute cross-mast reconstruction using trained models.

The TOML configuration file should specify:
- Masts with input data sources and output paths
- Reconstruction jobs with trained model paths
- Priority levels for reconstruction order
- Settings for reconstruction execution

For each reconstruction job:
- Loads trained cross-mast models from JLD2 files
- Applies reconstruction to fill missing data points only
- Preserves existing measurements (configurable)
- Generates quality metrics and validation reports
- Saves reconstructed time series files

Reconstruction is executed in priority order:
- Priority 1: Excellent correlations (≥0.9)
- Priority 2: Good correlations (≥0.8)
- Priority 3: Acceptable correlations (≥0.7)

## Example
```bash
julia bin/CleanMast.jl process reconstruct-cross reconstruct-cross.toml
```

---

# process guess-mast-from-meso

## Syntax
```bash
julia bin/CleanMast.jl process guess-mast-from-meso <config_path>
```

## Arguments
- `config_path`: Path to the guess-mast-from-meso.toml configuration file.

## Description
Generate synthetic mast data from mesoscale data using mean speed matching. Generates synthetic mast data by scaling meso wind speeds to match target mean values.

## Example
```bash
julia bin/CleanMast.jl process guess-mast-from-meso guess-mast-from-meso.toml
```

---

# process steps

## Syntax
```bash
julia bin/CleanMast.jl process steps <dir> [--all] [--from <from>] [--to <to>] [--list]
```

## Arguments
- `dir`: Project directory containing configurations

## Options
- `--all`: Execute all processing steps (1-18)
- `--from <from>`: Starting step number (1-18, default: 1 when --all is used)
- `--to <to>`: Ending step number (1-18, default: 18 when --all is used)
- `--list`: List all available steps without executing

## Description
Execute processing steps with flexible control options. Execute processing pipeline in flexible steps for better control and debugging.

## Examples
```bash
julia bin/CleanMast.jl process steps --all ./projects/my-project
julia bin/CleanMast.jl process steps --from 5 --to 12 ./projects/my-project
julia bin/CleanMast.jl process steps --from 10 ./projects/my-project
julia bin/CleanMast.jl process steps --list
```
