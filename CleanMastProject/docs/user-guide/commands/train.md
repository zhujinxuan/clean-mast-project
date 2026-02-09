# train reconstruct-cross

## Syntax
```bash
julia bin/CleanMast.jl train reconstruct-cross <config_path>
```

## Arguments
- `config_path`: Path to the train-reconstruct-cross.toml configuration file.

## Description
Train cross-mast relationships and reconstruction models.

The TOML configuration file should specify:
- Multiple masts with reconstructed time series data files and sensor configurations
- Training settings including model parameters
- Output directory for results (default: ./train-reconstruct-cross)

For each mast pair, trains:
- Data coverage and overlap duration analysis
- Wind speed correlations between high-elevation sensors (≥120m)
- Wind direction differences and standard deviations
- Cross-mast reconstruction models saved as .jld2 files
- Machine-readable results for the recommend command

Selection criteria for qualified pairs:
- Speed reconstruction: ≥120 days overlap, ≥0.7 correlation (high-elevation sensors)
- Direction reconstruction: ≥120 days overlap, ≤12.5° std deviation (high-elevation sensors)

## Example
```bash
julia bin/CleanMast.jl train reconstruct-cross path/to/train-reconstruct-cross.toml
```
