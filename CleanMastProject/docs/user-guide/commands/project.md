# project parse-sensors

## Syntax
```bash
julia bin/CleanMast.jl project parse-sensors <config_path>
```

## Arguments
- `config_path`: Path to the parse-sensors.toml configuration file.

## Description
Process sensor data based on a TOML configuration file. Creates raw data files and sensor metadata files.

## Example
```bash
julia bin/CleanMast.jl project parse-sensors path/to/project/parse-sensors.toml
```
