# Quick Tutorial

This tutorial provides a step-by-step guide to setting up a new project, parsing sensor data, and running the full data processing pipeline with CleanMastProject.

## 1. Installation

(This section is currently empty and will be filled in later.)
(Install Julia)
(Install nushell)
(git clone and Julia pkg.resolve())

## 2. Project Initialization

First, create a new directory for your project. Suppose you are already under `CleanMastProject/`, suppose your project name
is `windfarm-170`. Create a project with some necessary files as.

```nushell
> julia bin/CleanMast.jl project init projects/windfarm-170
```

## 3. Data Preparation

Next, you need to bring your raw data files into the project.

1.  **Mast Data**: Copy your raw mast data file(s) (e.g., `nrg-17005.txt`) into the project directory. Usually one txt file from nrg data
2.  **Meso Data**: If you have meso-scale model data, copy that into the project directory as well (e.g., `era5.txt`).
3.  **Sensor Format Files**: You will need a sensor format configuration file for each of your raw data files. 
It is a configuration file to associated the data files' heading columns to the wind measurement attributes, like height, sensor's direction, sensor meassure type, etc. Common formats are already in `project/windfarm-170/formats/sensor/` like `nrg.toml`. You can use them directly or
as a reference.

Your directory should look something like this:

```
projects/windfarm-170/
├── nrg-17005.txt
├── era5.txt
└── formats/
    └── sensor/
        └── nrg.toml
        └── freemeso-meso.toml
```

## 4. Configuration

### a. `config.yaml`

This file is currently required for some legacy commands. Create a `config.yaml` in your project root with the following minimal content. Replace `my-mast-name` and `my-meso-name` with the logical names you want to use.

```yaml
Mast:
  name: nrg-17005

Meso:
  name: era5

Analysis:
  time_range:
    min: "2020-01-01 00:00:00"
    max: "2021-01-01 00:00:00"
```

### b. `parse-sensors.toml`

This is the main configuration file for the first processing step. Create a `parse-sensors.toml` file in your project root. This file tells the system where to find your raw data and how to parse them. The command `project parse-sensors` will parse your input txt files as to csv and a toml describing each column of csv.

```toml
[[masts]]
input = "nrg-17005.txt"
name = "nrg-17005"
sensor = "formats/sensor/nrg.toml"
output = { data = "raw/nrg-17005.csv", sensors = "raw/nrg-17005.sensors.toml" }

[meso]
input = "era5.txt"
name = "era5"
sensor = "formats/sensor/freemeso-meso.toml"
output = { data = "raw/era5.csv", sensors = "raw/era5.sensors.toml" }
```

## 5. Run the Pipeline

Now you are ready to process your data.

### a. Parse Sensor Data

This first command reads your raw data based on `parse-sensors.toml`, normalizes it, and saves the output to the `raw/` directory.

From outside your project directory, run:

```nushell
> julia bin/CleanMast.jl parse-sensors projects/windfarm-170
```

After this step, you will have a `raw/` directory inside your project with normalized CSV files and corresponding `.sensors.toml` files.

### b. Run All Processing Steps

The `process all` command runs the entire data cleaning and reconstruction pipeline. It will automatically generate the necessary configurations and execute the steps in the correct order.

From outside your project directory, run:

```nushell
> julia bin/CleanMast.jl process all projects/windfarm-170
```

This command will:
1.  Generate a `