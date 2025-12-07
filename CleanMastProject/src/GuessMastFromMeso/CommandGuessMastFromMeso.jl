module CommandGuessMastFromMeso

using Comonicon
using ...Types.GuessMastFromMesoConfig: GuessMastFromMesoConfiguration
using ...Types.Utils: from_dict
using ...CleanMastUtils: load_dict
using ..Core: guess_mast_from_meso
using ..BootstrapGuessMastFromMeso: bootstrap_guess_mast_from_meso_config

"""
Generate synthetic mast data from mesoscale data using mean speed matching.

# Arguments
- `config_path`: Path to guess-mast-from-meso.toml configuration file

# Examples
```bash
julia bin/CleanMast.jl process guess-mast-from-meso guess-mast-from-meso.toml
```
"""
@cast function guess_mast_from_meso_command(config_path::String)
    if !isfile(config_path)
        error("Configuration file not found: $config_path")
    end

    println("📖 Loading configuration from: $config_path")
    config_dict = load_dict(config_path)
    config = from_dict(GuessMastFromMesoConfiguration, config_dict)

    base_dir = dirname(abspath(config_path))
    guess_mast_from_meso(config, base_dir)

    return nothing
end

"""
Bootstrap a guess-mast-from-meso.toml configuration file from meso data.

# Arguments
- `--meso`: Path to meso data CSV file (sensors file auto-detected as basename.sensors.toml)
- `--output`: Output path for configuration file (default: ../{meso-basename}.guess-mast-from-meso.toml relative to meso directory)

# Examples
```bash
julia bin/CleanMast.jl bootstrap guess-mast-from-meso --meso ./raw/era5.csv
```
"""
@cast function bootstrap_guess_mast_from_meso_command(;
    meso::String,
    output::Union{String, Nothing}=nothing
)
    if !isfile(meso)
        error("Meso data file not found: $meso")
    end

    bootstrap_guess_mast_from_meso_config(meso; output_path=output)

    return nothing
end

export guess_mast_from_meso_command, bootstrap_guess_mast_from_meso_command

end
