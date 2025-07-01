# `project parse-sensors` Command

This document details how to configure and run the `project parse-sensors` command, which is the first crucial step in the CleanMastProject pipeline. This command takes your raw, heterogeneous data files and converts them into a standardized format that the rest of the toolkit can understand.

## 1. Data Preparation

Before running the command, you need to have your raw data files ready. This typically includes:

-   **Mast Data**: Time-series data from your meteorological mast(s), usually in a CSV-like format.
-   **Meso-scale Data**: Long-term reference data, such as from ERA5, often in a different CSV-like format.
-   **Sensor Format Files**: For each distinct data format, you need to provide a `.toml` configuration file that describes how to parse it. This includes details about the timestamp, delimiters, and how to interpret each data column.

Place your raw data files directly inside your project directory. It's also a good practice to store your sensor format definitions in a `formats/sensor/` subdirectory within your project.

**Example Directory Structure:**

```
projects/windfarm-170/
├── nrg-17005.txt
├── era5.txt
├── merra2.txt
└── formats/
    └── sensor/
        ├── nrg.toml
        └── freemeso-meso.toml
```

## 2. Configuration (`parse-sensors.toml`)

The behavior of the `parse-sensors` command is controlled by a single file in your project's root directory: `parse-sensors.toml`.

This file explicitly distinguishes between mast data (in a `[[masts]]` array) and meso-scale data (in an optional `[[mesos]]` array).

### Configuration Fields

-   **`input`**: (String, required) The path to the raw data file, relative to the project directory.
-   **`name`**: (String, required) A unique logical name for this dataset (e.g., "MetMast1", "ERA5"). This name will be used in subsequent processing steps.
-   **`sensor`**: (String, required) The path to the sensor format `.toml` file that describes how to parse this `input` file.
-   **`output`**: (Table, optional) A table defining the output paths. If not given, defaults to `./raw/{name}.csv` and `./raw/{name}.sensors.toml`.
    -   **`data`**: (String, required) The relative path where the standardized CSV data will be saved.
    -   **`sensors`**: (String, required) The relative path where the generated sensor metadata file (in TOML format) will be saved.

### Example `parse-sensors.toml`

```toml
# Entry for the meteorological mast data
[[masts]]
input = "nrg-17005.txt"
name = "nrg-17005"
sensor = "formats/sensor/nrg.toml"

# Entries for the meso-scale data
[[mesos]]
input = "era5.txt"
name = "era5"
sensor = "formats/sensor/freemeso-meso.toml"

[[mesos]]
input = "merra2.txt"
name = "merra2"
sensor = "formats/sensor/freemeso-meso.toml"
```

## 3. Command Execution

To run the command, execute the following from outside your project directory, using `nushell`:

```nushell
> julia bin/CleanMast.jl project parse-sensors projects/windfarm-170
```

The command will:
1.  Read the `parse-sensors.toml` in your project directory.
2.  Iterate through each `[[masts]]` and `[[mesos]]` entry.
3.  Read the specified `input` file.
4.  Apply the parsing and normalization rules defined in the corresponding `sensor` format file.
5.  Write the processed data and sensor metadata to the specified `output` paths.

## 4. Expected Result

After the command successfully completes, your project directory will contain a new `raw/` directory. Inside, you will find the standardized data and sensor files, named according to your configuration.

**Example Resulting Directory Structure:**

```
projects/windfarm-170/
├── nrg-17005.txt
├── era5.txt
├── merra2.txt
├── parse-sensors.toml
├── formats/
│   └── sensor/
│       ├── nrg.toml
│       └── freemeso-meso.toml
└── raw/
    ├── nrg-17005.csv
    ├── nrg-17005.sensors.toml
    ├── era5.csv
    ├── era5.sensors.toml
    ├── merra2.csv
    └── merra2.sensors.toml
``` 